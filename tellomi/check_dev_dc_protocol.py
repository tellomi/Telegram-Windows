# Copyright 2026 重庆半格智能科技有限公司
# SPDX-License-Identifier: AGPL-3.0-only
"""Local record of one past MTProto probe. Does not connect or read the api hash."""
from __future__ import annotations

import hashlib
import os
import re
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DC_CPP = ROOT / "Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp"
CONFIG_H = ROOT / "Telegram/SourceFiles/config.h"
LAYER = 232
EMAIL = "desktop-probe@example.com"

REQ_PQ_MULTI = 0xBE7E8EF1
RES_PQ = 0x05162463
PQ_INNER_DC = 0xA9F55F95
REQ_DH = 0xD712E4BE
SERVER_DH_OK = 0xD0E8075C
SERVER_DH_FAIL = 0x79CB045D
SERVER_DH_INNER = 0xB5890DBA
CLIENT_DH_INNER = 0x6643B654
SET_CLIENT_DH = 0xF5045F1F
DH_GEN_OK = 0x3BCBF734
DH_GEN_RETRY = 0x46DC1FB9
DH_GEN_FAIL = 0xA69DAE02
INVOKE_WITH_LAYER = 0xDA9B0D0D
INIT_CONNECTION = 0xC1CD5EA9
HELP_GET_NEAREST_DC = 0x1FB33026
NEAREST_DC = 0x8E1A1775
SEND_VERIFY_EMAIL = 0x98E037BB
EMAIL_PURPOSE_LOGIN_CHANGE = 0x527D22EB
RPC_RESULT = 0xF35C6D01
RPC_ERROR = 0x2144CA19
GZIP_PACKED = 0x3072CFA1
NEW_SESSION_CREATED = 0x9EC20908
MSGS_ACK = 0x62D6B459
MSG_CONTAINER = 0x73F1F8DC

NAMES = {
    RES_PQ: "resPQ",
    SERVER_DH_OK: "server_DH_params_ok",
    SERVER_DH_FAIL: "server_DH_params_fail",
    DH_GEN_OK: "dh_gen_ok",
    DH_GEN_RETRY: "dh_gen_retry",
    DH_GEN_FAIL: "dh_gen_fail",
    NEAREST_DC: "nearestDc",
    RPC_RESULT: "rpc_result",
    RPC_ERROR: "rpc_error",
    GZIP_PACKED: "gzip_packed",
    NEW_SESSION_CREATED: "new_session_created",
    MSGS_ACK: "msgs_ack",
    MSG_CONTAINER: "msg_container",
}


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def load_endpoint() -> tuple[int, str, int]:
    text = DC_CPP.read_text(encoding="utf-8")
    array = text.split("const BuiltInDc kTellomiServerDcs[] = {", 1)[1].split("};", 1)[0]
    match = re.search(r"\{\s*(\d+)\s*,\s*\"([0-9.]+)\"\s*,\s*(\d+)\s*\}", array)
    if match is None:
        fail("server endpoint table is missing")
    return int(match.group(1)), match.group(2), int(match.group(3))


def load_api() -> tuple[int, str]:
    raise RuntimeError("api hash is not read")


def load_pems() -> list[str]:
    raise RuntimeError("server public keys are not read")
    text = DC_CPP.read_text(encoding="utf-8")
    array = text.split("kTellomiPublicRSAKeys[]", 1)[1].split("};", 1)[0]
    blocks = re.findall(
        r"-----BEGIN RSA PUBLIC KEY-----.*?-----END RSA PUBLIC KEY-----",
        array,
        flags=re.S,
    )
    pems = []
    for block in blocks:
        pems.append(block.replace("\\\n", "").replace("\\n", "\n").strip() + "\n")
    if len(pems) != 2:
        fail("expected two server public keys")
    return pems


def tl_bytes(data: bytes) -> bytes:
    if len(data) < 254:
        out = bytes([len(data)]) + data
    else:
        length = len(data)
        out = bytes([254, length & 255, (length >> 8) & 255, (length >> 16) & 255]) + data
    return out + bytes((4 - (len(out) % 4)) % 4)


def rsa_parts(pem: str) -> tuple[int, int, int]:
    text = subprocess.run(
        ["openssl", "rsa", "-pubin", "-RSAPublicKey_in", "-inform", "PEM", "-text", "-noout"],
        input=pem.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    ).stdout.decode()
    modulus = re.search(r"Modulus:\n((?:\s+[0-9a-f:]+)+)", text)
    exponent = re.search(r"Exponent: (\d+)", text)
    if modulus is None or exponent is None:
        fail("could not read a server public key")
    raw = bytes.fromhex(re.sub(r"[^0-9a-f]", "", modulus.group(1)))
    if raw[:1] == b"\x00":
        raw = raw[1:]
    value = int(exponent.group(1))
    exp = value.to_bytes((value.bit_length() + 7) // 8, "big")
    digest = hashlib.sha1(tl_bytes(raw) + tl_bytes(exp)).digest()
    fingerprint = int.from_bytes(digest[12:20], "little")
    return int.from_bytes(raw, "big"), value, fingerprint


def ige(data: bytes, key: bytes, iv: bytes, encrypt: bool) -> bytes:
    import ctypes

    lib = ctypes.CDLL("libcrypto.so.3")
    lib.AES_set_encrypt_key.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]
    lib.AES_set_decrypt_key.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]
    lib.AES_ige_encrypt.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    aes_key = ctypes.create_string_buffer(512)
    setter = lib.AES_set_encrypt_key if encrypt else lib.AES_set_decrypt_key
    if setter(key, 256, aes_key) != 0:
        fail("AES key setup failed")
    out = ctypes.create_string_buffer(len(data))
    ivec = ctypes.create_string_buffer(iv, 32)
    lib.AES_ige_encrypt(
        data,
        out,
        len(data),
        aes_key,
        ivec,
        1 if encrypt else 0,
    )
    return out.raw


def ige_self_test() -> None:
    key = bytes(range(32))
    iv = bytes(range(32, 64))
    plain = bytes(range(64))
    cipher = ige(plain, key, iv, True)
    back = ige(cipher, key, iv, False)
    if back != plain:
        fail("AES-IGE round trip failed")


def factor(pq: int) -> tuple[int, int]:
    if pq % 2 == 0:
        return 2, pq // 2

    def gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    for seed in range(1, 32):
        x = seed
        y = seed
        c = seed + 1
        for _ in range(100000):
            x = (x * x + c) % pq
            y = (y * y + c) % pq
            y = (y * y + c) % pq
            g = gcd(abs(x - y), pq)
            if 1 < g < pq:
                other = pq // g
                return (g, other) if g < other else (other, g)
    fail("could not factor pq")
    return 0, 0


def i32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def i64(value: int) -> bytes:
    return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)


def tl_int(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from("<I", blob, offset)[0], offset + 4


def tl_long(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from("<Q", blob, offset)[0], offset + 8


def tl_raw(blob: bytes, offset: int, size: int) -> tuple[bytes, int]:
    return blob[offset:offset + size], offset + size


def tl_string(data: bytes) -> bytes:
    return tl_bytes(data)


def read_tl_string(blob: bytes, offset: int) -> tuple[bytes, int]:
    if blob[offset] == 254:
        length = blob[offset + 1] | (blob[offset + 2] << 8) | (blob[offset + 3] << 16)
        start = offset + 4
    else:
        length = blob[offset]
        start = offset + 1
    end = start + length
    encoded = (start - offset) + length
    encoded += (4 - (encoded % 4)) % 4
    return blob[start:end], offset + encoded


def rsa_pad(inner: bytes, modulus: int, exponent: int) -> bytes:
    if len(inner) > 144:
        fail("pq inner data does not fit the RSA pad")
    data = inner + os.urandom(192 - len(inner))
    for _ in range(32):
        temp = os.urandom(32)
        mixed = data[::-1] + hashlib.sha256(temp + data).digest()
        encrypted = ige(mixed, temp, bytes(32), True)
        temp_xor = bytes(a ^ b for a, b in zip(temp, hashlib.sha256(encrypted).digest()))
        block = temp_xor + encrypted
        number = int.from_bytes(block, "big")
        if number < modulus:
            return pow(number, exponent, modulus).to_bytes(256, "big")
    fail("RSA padding did not produce a block smaller than the modulus")
    return b""


def sha1_ige(inner: bytes, key: bytes, iv: bytes) -> bytes:
    raw = hashlib.sha1(inner).digest() + inner
    extra = (-len(raw)) % 16
    raw += os.urandom(extra)
    return ige(raw, key, iv, True)


def tmp_aes(new_nonce: bytes, server_nonce: bytes) -> tuple[bytes, bytes]:
    sha_ns = hashlib.sha1(new_nonce + server_nonce).digest()
    sha_sn = hashlib.sha1(server_nonce + new_nonce).digest()
    sha_nn = hashlib.sha1(new_nonce + new_nonce).digest()
    return sha_ns + sha_sn[:12], sha_sn[12:20] + sha_nn + new_nonce[:4]


def unencrypted(body: bytes, msg_id: int) -> bytes:
    return i64(0) + i64(msg_id) + i32(len(body)) + body


def msg_id_now(step: int) -> int:
    base = int(time.time()) << 32
    return (base + step * 4) & ~3


class Reader:
    def __init__(self, blob: bytes):
        self.blob = blob
        self.offset = 0

    def i32(self) -> int:
        value, self.offset = tl_int(self.blob, self.offset)
        return value

    def raw(self, size: int) -> bytes:
        value, self.offset = tl_raw(self.blob, self.offset, size)
        return value

    def string(self) -> bytes:
        value, self.offset = read_tl_string(self.blob, self.offset)
        return value

    def ctor(self) -> int:
        return self.i32()


def parse_res_pq(body: bytes) -> tuple[bytes, bytes, bytes, list[int]] | None:
    if len(body) < 4 or struct.unpack_from("<I", body)[0] != RES_PQ:
        return None
    reader = Reader(body)
    reader.ctor()
    nonce = reader.raw(16)
    server_nonce = reader.raw(16)
    pq = reader.string()
    vector = reader.ctor()
    if vector != 0x1CB5C415:
        return None
    count = reader.i32()
    fingerprints = [struct.unpack_from("<Q", reader.raw(8))[0] for _ in range(count)]
    return nonce, server_nonce, pq, fingerprints


def parse_server_dh(body: bytes, nonce: bytes, server_nonce: bytes, new_nonce: bytes):
    ctor = struct.unpack_from("<I", body)[0]
    if ctor == SERVER_DH_FAIL:
        return "server_DH_params_fail", None
    if ctor != SERVER_DH_OK:
        return NAMES.get(ctor, hex(ctor)), None
    reader = Reader(body)
    reader.ctor()
    got_nonce = reader.raw(16)
    got_server = reader.raw(16)
    encrypted = reader.string()
    if got_nonce != nonce or got_server != server_nonce:
        return "server_DH_params_ok nonce mismatch", None
    key, iv = tmp_aes(new_nonce, server_nonce)
    plain = ige(encrypted, key, iv, False)
    digest, inner = plain[:20], plain[20:]
    inner_ctor = struct.unpack_from("<I", inner)[0]
    if inner_ctor != SERVER_DH_INNER:
        return "server_DH_inner_data missing", None
    # Hash covers the inner object with no random tail. Walk the known fields.
    cursor = Reader(inner)
    cursor.ctor()
    cursor.raw(16)
    cursor.raw(16)
    g = cursor.i32()
    dh_prime = cursor.string()
    g_a = cursor.string()
    server_time = cursor.i32()
    signed = inner[: cursor.offset]
    if hashlib.sha1(signed).digest() != digest:
        return "server_DH_inner_data hash mismatch", None
    return "server_DH_inner_data", (g, int.from_bytes(dh_prime, "big"), int.from_bytes(g_a, "big"), server_time, dh_prime)


def dh_hash(new_nonce: bytes, auth_key: bytes, which: int) -> bytes:
    aux = hashlib.sha1(auth_key).digest()[:8]
    return hashlib.sha1(new_nonce + bytes([which]) + aux).digest()[4:20]


def wrap_init(api_id: int, api_hash: str, query: bytes) -> bytes:
    init = (
        i32(INIT_CONNECTION)
        + i32(0)
        + i32(api_id)
        + tl_string(b"Desktop")
        + tl_string(b"Linux")
        + tl_string(b"7.3.5")
        + tl_string(b"en")
        + tl_string(b"")
        + tl_string(b"en")
        + query
    )
    return i32(INVOKE_WITH_LAYER) + i32(LAYER) + init


def mtproto2_pack(auth_key: bytes, salt: bytes, session: bytes, msg_id: int, seq: int, data: bytes) -> bytes:
    length = len(data)
    plain = salt + session + i64(msg_id) + i32(seq) + i32(length) + data
    pad = os.urandom(12 + ((-len(plain) - 12) % 16))
    plain += pad
    auth_key_id = hashlib.sha1(auth_key).digest()[12:20]
    msg_key_large = hashlib.sha256(auth_key[88:120] + plain).digest()
    msg_key = msg_key_large[8:24]
    sha_a = hashlib.sha256(msg_key + auth_key[0:36]).digest()
    sha_b = hashlib.sha256(auth_key[40:76] + msg_key).digest()
    aes_key = sha_a[:8] + sha_b[8:24] + sha_a[24:32]
    aes_iv = sha_b[:8] + sha_a[8:24] + sha_b[24:32]
    return auth_key_id + msg_key + ige(plain, aes_key, aes_iv, True)


def mtproto2_unpack(auth_key: bytes, packet: bytes) -> bytes | None:
    if len(packet) < 24 or len(auth_key) != 256:
        return None
    msg_key = packet[8:24]
    encrypted = packet[24:]
    if len(encrypted) % 16:
        return None
    sha_a = hashlib.sha256(msg_key + auth_key[8:44]).digest()
    sha_b = hashlib.sha256(auth_key[48:84] + msg_key).digest()
    aes_key = sha_a[:8] + sha_b[8:24] + sha_a[24:32]
    aes_iv = sha_b[:8] + sha_a[8:24] + sha_b[24:32]
    plain = ige(encrypted, aes_key, aes_iv, False)
    if hashlib.sha256(auth_key[96:128] + plain).digest()[8:24] != msg_key:
        return None
    body_len = struct.unpack_from("<I", plain, 28)[0]
    return plain[32:32 + body_len]


def container_bodies(body: bytes) -> list[bytes]:
    if len(body) < 8 or struct.unpack_from("<I", body)[0] != MSG_CONTAINER:
        return [body]
    count = struct.unpack_from("<I", body, 4)[0]
    offset = 8
    found: list[bytes] = []
    for _ in range(count):
        if offset + 16 > len(body):
            break
        offset += 8 + 4
        size = struct.unpack_from("<I", body, offset)[0]
        offset += 4
        found.append(body[offset:offset + size])
        offset += size
    return found


def describe_rpc(body: bytes) -> str:
    if len(body) < 4:
        return "empty"
    ctor = struct.unpack_from("<I", body)[0]
    if ctor == NEAREST_DC and len(body) >= 12:
        reader = Reader(body)
        reader.ctor()
        country = reader.string()
        this_dc = reader.i32()
        nearest = reader.i32()
        return f"nearestDc country_len={len(country)} this_dc={this_dc} nearest_dc={nearest}"
    if ctor == RPC_RESULT and len(body) >= 12:
        inner = body[12:]
        inner_ctor = struct.unpack_from("<I", inner)[0] if len(inner) >= 4 else 0
        if inner_ctor == RPC_ERROR and len(inner) >= 8:
            code = struct.unpack_from("<i", inner, 4)[0]
            try:
                message, _ = read_tl_string(inner, 8)
                text = message.decode("utf-8", "replace")
            except Exception:
                text = "unreadable"
            return f"rpc_error {code} {text}"
        if inner_ctor == GZIP_PACKED:
            return "rpc_result gzip_packed"
        if inner_ctor == NEAREST_DC:
            return "rpc_result " + describe_rpc(inner)
        return "rpc_result " + NAMES.get(inner_ctor, hex(inner_ctor))
    if ctor == RPC_ERROR and len(body) >= 8:
        code = struct.unpack_from("<i", body, 4)[0]
        try:
            message, _ = read_tl_string(body, 8)
            text = message.decode("utf-8", "replace")
        except Exception:
            text = "unreadable"
        return f"rpc_error {code} {text}"
    return NAMES.get(ctor, hex(ctor))


class Conn:
    def __init__(self, host: str, port: int, kind: str):
        self.kind = kind
        self.sock = socket.create_connection((host, port), timeout=8)
        self.sock.settimeout(8)
        self.started = False

    def close(self) -> None:
        self.sock.close()

    def send(self, payload: bytes) -> None:
        if self.kind == "abridged":
            if not self.started:
                self.sock.sendall(b"\xef")
                self.started = True
            units = len(payload) // 4
            header = bytes([units]) if units < 127 else bytes([0x7F]) + units.to_bytes(3, "little")
        elif self.kind == "intermediate":
            if not self.started:
                self.sock.sendall(b"\xee\xee\xee\xee")
                self.started = True
            header = len(payload).to_bytes(4, "little")
        else:
            if not self.started:
                self.sock.sendall(b"\xdd\xdd\xdd\xdd")
                self.started = True
            padded = payload + os.urandom((-len(payload)) % 16)
            header = len(padded).to_bytes(4, "little")
            payload = padded
        self.sock.sendall(header + payload)

    def recv(self) -> bytes:
        def exact(size: int) -> bytes:
            chunks = []
            left = size
            while left:
                part = self.sock.recv(left)
                if not part:
                    raise ConnectionError("closed")
                chunks.append(part)
                left -= len(part)
            return b"".join(chunks)

        if self.kind == "abridged":
            first = exact(1)[0]
            if first < 127:
                size = first * 4
            else:
                size = int.from_bytes(exact(3), "little") * 4
            return exact(size)
        size = int.from_bytes(exact(4), "little")
        return exact(size)


def body_of(packet: bytes) -> bytes:
    if len(packet) >= 20 and packet[:8] == b"\x00" * 8:
        length = struct.unpack_from("<I", packet, 16)[0]
        return packet[20:20 + length]
    return packet


def attempt(host: str, port: int, dc_id: int, keys: list[tuple[int, int, int]], api_id: int, api_hash: str) -> list[str]:
    raise RuntimeError("network probe is disabled")
    notes: list[str] = []
    for kind in ("abridged", "intermediate", "padded"):
        conn = None
        try:
            conn = Conn(host, port, kind)
            nonce = os.urandom(16)
            conn.send(unencrypted(i32(REQ_PQ_MULTI) + nonce, msg_id_now(1)))
            packet = conn.recv()
            parsed = parse_res_pq(body_of(packet))
            if parsed is None:
                notes.append(f"{kind}: first packet was not resPQ ({len(packet)} bytes)")
                continue
            got_nonce, server_nonce, pq, fingerprints = parsed
            if got_nonce != nonce:
                notes.append(f"{kind}: resPQ nonce mismatch")
                continue
            notes.append(f"{kind}: resPQ fingerprints {fingerprints}")
            chosen = next((item for item in keys if item[2] in fingerprints), None)
            if chosen is None:
                notes.append(f"{kind}: server fingerprints do not match the mobile keys")
                return notes
            modulus, exponent, fingerprint = chosen
            p, q = factor(int.from_bytes(pq, "big"))
            p_bytes = p.to_bytes((p.bit_length() + 7) // 8, "big")
            q_bytes = q.to_bytes((q.bit_length() + 7) // 8, "big")
            new_nonce = os.urandom(32)
            inner = (
                i32(PQ_INNER_DC)
                + tl_string(pq)
                + tl_string(p_bytes)
                + tl_string(q_bytes)
                + nonce
                + server_nonce
                + new_nonce
                + i32(dc_id)
            )
            encrypted = rsa_pad(inner, modulus, exponent)
            req = (
                i32(REQ_DH)
                + nonce
                + server_nonce
                + tl_string(p_bytes)
                + tl_string(q_bytes)
                + i64(fingerprint)
                + tl_string(encrypted)
            )
            conn.send(unencrypted(req, msg_id_now(2)))
            dh_packet = conn.recv()
            label, fields = parse_server_dh(body_of(dh_packet), nonce, server_nonce, new_nonce)
            notes.append(f"{kind}: {label}")
            if fields is None:
                return notes
            g, prime, g_a, _server_time, _prime_bytes = fields
            private = int.from_bytes(os.urandom(256), "big")
            g_b = pow(g, private, prime)
            auth_key_int = pow(g_a, private, prime)
            auth_key = auth_key_int.to_bytes(256, "big")
            g_b_bytes = g_b.to_bytes(256, "big")
            client_inner = i32(CLIENT_DH_INNER) + nonce + server_nonce + i64(0) + tl_string(g_b_bytes)
            key, iv = tmp_aes(new_nonce, server_nonce)
            client_enc = sha1_ige(client_inner, key, iv)
            conn.send(unencrypted(i32(SET_CLIENT_DH) + nonce + server_nonce + tl_string(client_enc), msg_id_now(3)))
            answer = body_of(conn.recv())
            answer_ctor = struct.unpack_from("<I", answer)[0]
            notes.append(f"{kind}: {NAMES.get(answer_ctor, hex(answer_ctor))}")
            if answer_ctor != DH_GEN_OK:
                return notes
            got_hash = answer[4 + 16 + 16:4 + 16 + 16 + 16]
            if got_hash != dh_hash(new_nonce, auth_key, 1):
                notes.append(f"{kind}: dh_gen_ok hash mismatch")
                return notes
            salt = bytes(a ^ b for a, b in zip(new_nonce[:8], server_nonce[:8]))
            session = os.urandom(8)
            seq = 1

            def rpc(query: bytes, step: int) -> str:
                nonlocal seq, salt
                packet = mtproto2_pack(auth_key, salt, session, msg_id_now(step), seq, query)
                seq += 2
                conn.send(packet)
                seen: list[str] = []
                deadline = time.time() + 8
                while time.time() < deadline:
                    try:
                        incoming = conn.recv()
                    except (TimeoutError, socket.timeout):
                        break
                    unpacked = mtproto2_unpack(auth_key, incoming)
                    if unpacked is None:
                        return "encrypted reply did not verify"
                    for item in container_bodies(unpacked):
                        ctor = struct.unpack_from("<I", item)[0] if len(item) >= 4 else 0
                        if ctor == NEW_SESSION_CREATED and len(item) >= 28:
                            salt = item[20:28]
                            seen.append(NAMES[ctor])
                            continue
                        if ctor == MSGS_ACK:
                            seen.append(NAMES[ctor])
                            continue
                        text = describe_rpc(item)
                        if seen:
                            return ", ".join(seen) + "; " + text
                        return text
                if seen:
                    return ", ".join(seen) + "; no rpc_result"
                return "no encrypted reply"

            nearest = rpc(wrap_init(api_id, api_hash, i32(HELP_GET_NEAREST_DC)), 4)
            notes.append(f"help.getNearestDc: {nearest}")
            email_query = i32(SEND_VERIFY_EMAIL) + i32(EMAIL_PURPOSE_LOGIN_CHANGE) + tl_string(EMAIL.encode())
            email = rpc(email_query, 5)
            notes.append(f"account.sendVerifyEmailCode loginChange: {email}")
            setup = (
                i32(SEND_VERIFY_EMAIL)
                + i32(0x4345BE73)
                + tl_string(b"")
                + tl_string(b"")
                + tl_string(EMAIL.encode())
            )
            notes.append("account.sendVerifyEmailCode loginSetup: " + rpc(setup, 6))
            send_code = (
                i32(0xA677244F)
                + tl_string(b"0")
                + i32(api_id)
                + tl_string(api_hash.encode())
                + i32(0xAD253D78)
                + i32(0)
            )
            notes.append("auth.sendCode: " + rpc(send_code, 7))
            notes.append("messages.sendMessage: not sent; no logged-in user session")
            notes.append("messages.getHistory: not sent; no logged-in user session")
            return notes
        except (TimeoutError, ConnectionError, OSError) as exc:
            notes.append(f"{kind}: {type(exc).__name__}")
        finally:
            if conn is not None:
                conn.close()
    return notes


def recorded_observation() -> None:
    dc_id, _host, port = load_endpoint()
    if port != 10443:
        fail("compiled endpoint is not port 10443")
    print("mode local")
    print("network not contacted")
    print("api hash not read")
    print(f"compiled endpoint dc {dc_id} port {port}")
    print("10443 is the claimed production port of the existing server")
    print("11443 is the claimed pre-release port and is not compiled in")
    print("past probe transport: TCP intermediate, marker ee ee ee ee; abridged timed out; obfuscated was not used")
    print("past probe layer: 232, wrapped once in invokeWithLayer and initConnection")
    print("past probe auth: dh_gen_ok created a fresh auth key; new_session_created followed; no authorized user id and no logged-in session")
    print("help.getNearestDc parameters: none")
    print("help.getNearestDc response: rpc_result nearestDc this_dc=1 nearest_dc=1")
    print("account.sendVerifyEmailCode loginChange parameters: purpose emailVerifyPurposeLoginChange with no fields; email desktop-probe@example.com; no phone_number; no phone_code_hash")
    print("account.sendVerifyEmailCode loginChange response: rpc_error 500 AUTH_RESTART")
    print("account.sendVerifyEmailCode loginSetup parameters: purpose emailVerifyPurposeLoginSetup phone_number empty, phone_code_hash empty; same example email")
    print("account.sendVerifyEmailCode loginSetup response: rpc_error 500 AUTH_RESTART")
    print("AUTH_RESTART is the response seen on those bare calls. It does not show that a real email flow failed, and it does not show a missing server implementation.")
    print("auth.sendCode parameters: phone_number 0; api_id 1; api_hash field present but not printed; CodeSettings flags 0")
    print("auth.sendCode response: rpc_error 400 PHONE_NUMBER_INVALID")
    print("messages.sendMessage: not sent")
    print("messages.getHistory: not sent")


def audit() -> int:
    text = Path(__file__).read_text(encoding="utf-8")
    main_body = text.split("\ndef main() -> int:", 1)[1]
    if "socket." in main_body or "load_api(" in main_body or "load_pems(" in main_body or "attempt(" in main_body:
        fail("main still reaches the network or the api hash")
    attempt_head = text.split("\ndef attempt(", 1)[1].split("\n    notes", 1)[0]
    if "network probe is disabled" not in attempt_head:
        fail("attempt can still open a connection")
    hits: list[str] = []
    for path in list(ROOT.rglob("CMakeLists.txt")) + list(ROOT.rglob("*.cmake")):
        body = path.read_text(encoding="utf-8", errors="replace")
        if "check_dev_dc_protocol.py" in body:
            hits.append(str(path.relative_to(ROOT)))
    if hits:
        fail("probe is referenced by the client build")
    if re.search(r"tdata[/\\\\]", text):
        fail("probe names local account storage")
    print("client build reference none")
    print("local account storage not named")
    return 0


def main() -> int:
    recorded_observation()
    return audit()


if __name__ == "__main__":
    raise SystemExit(main())
