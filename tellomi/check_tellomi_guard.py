# Copyright 2026 重庆半格智能科技有限公司
# SPDX-License-Identifier: AGPL-3.0-only
"""可执行检查：默认 Tellomi 构建不能打出 Telegram 安装包，也不能收下上游 DC。不编译客户端。"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIN = ROOT
TEL = WIN / "tellomi"
UPSTREAM = "3a2a9a34e833d3243a13787215b8a7cdcf5dc3c3"


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def normalize(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    addr = ipaddress.ip_address(text)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def builtin_addresses(dc_cpp: str) -> set[str]:
    arrays = re.findall(
        r"const BuiltInDc kBuiltIn\w+\[\] = \{(.*?)\};",
        dc_cpp,
        flags=re.S,
    )
    found: set[str] = set()
    for block in arrays:
        for raw in re.findall(r'"([^"]+)"', block):
            found.add(str(normalize(raw)))
    if len(found) < 8:
        raise RuntimeError(f"只解析到 {len(found)} 个内置地址")
    return found


FORBIDDEN_IF = r"if\s*\(\s*TellomiEndpointForbidden\b[^{]*\)\s*\{[^{}]*\}"
MOBILE_RSA_FINGERPRINTS = (4381149949997195609, 12240908862933197005)
MOBILE_API_HASH_SHA256 = "3eb1bd439947eb762998e566ccc2e099c791118b2f40579cc4f7da2b5061b7f9"


def tellomi_gate(apply_body: str) -> str:
    return apply_body.split("#ifdef TELLOMI_BUILD", 1)[1].split("#endif", 1)[0]


def depth0_return(text: str) -> bool:
    depth = 0
    for line in text.splitlines():
        code = re.sub(r"//.*", "", line)
        if depth == 0 and re.search(r"\breturn\b", code):
            return True
        depth += code.count("{") - code.count("}")
        if depth < 0:
            depth = 0
    return False


def gate_installs_only_allowed(apply_body: str) -> bool:
    """Allowed addresses reach emplace. Forbidden ones still return first."""
    if "emplace" not in apply_body or "#ifdef TELLOMI_BUILD" not in apply_body:
        return False
    gate = tellomi_gate(apply_body)
    if not re.search(FORBIDDEN_IF, gate, flags=re.S):
        return False
    without_forbidden = re.sub(FORBIDDEN_IF, "", gate, count=1, flags=re.S)
    return not depth0_return(without_forbidden)


def drop_forbidden_check(apply_body: str) -> str:
    head, rest = apply_body.split("#ifdef TELLOMI_BUILD", 1)
    gate, tail = rest.split("#endif", 1)
    gate = re.sub(FORBIDDEN_IF, "", gate, count=1, flags=re.S)
    return head + "#ifdef TELLOMI_BUILD" + gate + "#endif" + tail


def add_unconditional_return(apply_body: str) -> str:
    head, rest = apply_body.split("#ifdef TELLOMI_BUILD", 1)
    gate, tail = rest.split("#endif", 1)
    return head + "#ifdef TELLOMI_BUILD" + gate + "\n\treturn false;\n#endif" + tail


def tl_bytes(data: bytes) -> bytes:
    if len(data) < 254:
        out = bytes([len(data)]) + data
    else:
        length = len(data)
        out = bytes([254, length & 255, (length >> 8) & 255, (length >> 16) & 255]) + data
    pad = (4 - (len(out) % 4)) % 4
    return out + bytes(pad)


def rsa_fingerprint(pem: str) -> int:
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
        raise RuntimeError("openssl 没有给出模数或指数")
    raw = bytes.fromhex(re.sub(r"[^0-9a-f]", "", modulus.group(1)))
    if raw[:1] == b"\x00":
        raw = raw[1:]
    value = int(exponent.group(1))
    exp = value.to_bytes((value.bit_length() + 7) // 8, "big")
    digest = hashlib.sha1(tl_bytes(raw) + tl_bytes(exp)).digest()
    return int.from_bytes(digest[12:20], "little")


def tellomi_pems(dc: str) -> list[str]:
    array = dc.split("kTellomiPublicRSAKeys[]", 1)[1].split("};", 1)[0]
    blocks = re.findall(
        r"-----BEGIN RSA PUBLIC KEY-----.*?-----END RSA PUBLIC KEY-----",
        array,
        flags=re.S,
    )
    pems: list[str] = []
    for block in blocks:
        text = block.replace("\\\n", "").replace("\\n", "\n").strip()
        pems.append(text + "\n")
    return pems


def _packaging_if_block(build_bat: str) -> str | None:
    match = re.search(
        r'if not "%TELLOMI_UPSTREAM_PACKAGE%"=="1" \(\n(?:.*\n)*?\)\n',
        build_bat,
    )
    return match.group(0) if match else None


def packaging_blocked(build_bat: str) -> bool:
    if "iscc " not in build_bat:
        return False
    block = _packaging_if_block(build_bat)
    if block is None or "exit /b 1" not in block:
        return False
    if build_bat.find(block) > build_bat.find("iscc "):
        return False
    iscc_line = build_bat.split("iscc ", 1)[1].splitlines()[0]
    return "/dTellomiBuild=0" in iscc_line


def drop_packaging_block(build_bat: str) -> str:
    block = _packaging_if_block(build_bat)
    if block is None:
        return build_bat
    return build_bat.replace(block, block.replace("exit /b 1", "rem exit removed", 1), 1)


def forbidden(ip: str, builtins: set[str]) -> bool:
    try:
        addr = normalize(ip)
    except ValueError:
        return True
    if addr.is_loopback or str(addr) == "10.0.2.2":
        return True
    return str(addr) in builtins


def require_blocked(name: str, text: str, start: str, end: str, needle: str, problems: list[str]) -> None:
    body = text.split(start, 1)[1].split(end, 1)[0]
    if needle not in body:
        fail(problems, f"{name} 没有被 TELLOMI_BUILD 挡住：{needle}")


def main() -> int:
    problems: list[str] = []
    version = (WIN / "Telegram/SourceFiles/core/version.h").read_text(encoding="utf-8")
    dc = (WIN / "Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp").read_text(encoding="utf-8")
    opts = (WIN / "Telegram/cmake/telegram_options.cmake").read_text(encoding="utf-8")
    cmake_lists = (WIN / "Telegram/CMakeLists.txt").read_text(encoding="utf-8")
    root_cmake = (WIN / "CMakeLists.txt").read_text(encoding="utf-8")
    cmake = (TEL / "tellomi.cmake").read_text(encoding="utf-8")
    iss = (WIN / "Telegram/build/setup.iss").read_text(encoding="utf-8")
    crash = (WIN / "Telegram/SourceFiles/core/crash_report_window.cpp").read_text(encoding="utf-8")
    config_h = (WIN / "Telegram/SourceFiles/config.h").read_text(encoding="utf-8")
    scope = (TEL / "SCOPE.md").read_text(encoding="utf-8")
    upstream = (TEL / "UPSTREAM.md").read_text(encoding="utf-8")

    if UPSTREAM not in upstream:
        fail(problems, "UPSTREAM.md 没有钉死提交")
    if "Qt" not in upstream or "没有下载" not in upstream:
        fail(problems, "UPSTREAM.md 没有写明 Qt / 预编译依赖尚未核齐")
    if not re.search(r'option\(TELLOMI_BUILD\s+"[^"]+"\s+ON\)', cmake):
        fail(problems, "TELLOMI_BUILD 不是默认 ON")
    if cmake.index("option(TELLOMI_BUILD") > cmake.index("CMAKE_SCRIPT_MODE_FILE"):
        fail(problems, "cmake -P 在 option 之前 return，默认值没有被检查")
    if "DESKTOP_APP_DISABLE_AUTOUPDATE ON" not in cmake or "DESKTOP_APP_DISABLE_CRASH_REPORTS ON" not in cmake:
        fail(problems, "没有同时关掉自动更新和崩溃上报")
    if "include(${CMAKE_CURRENT_SOURCE_DIR}/tellomi/tellomi.cmake)" not in root_cmake:
        fail(problems, "根 CMakeLists 没有引入 tellomi.cmake")
    if 'set(output_name "Tellomi")' not in cmake_lists.split("if (TELLOMI_BUILD)", 1)[1][:400]:
        fail(problems, "OUTPUT_NAME 在 TELLOMI_BUILD 下仍不是 Tellomi")
    if "#define TellomiBuild 1" not in iss or '#define MyAppExeName "Tellomi.exe"' not in iss.split("#else", 1)[0]:
        fail(problems, "setup.iss 默认仍会打出 Telegram.exe")
    if "desktop.telegram.org" in iss.split("#else", 1)[0]:
        fail(problems, "Tellomi 安装脚本分支仍指向 Telegram 更新域")
    if 'set(output_name "Telegram")' not in cmake_lists or '#define MyAppExeName "Telegram.exe"' not in iss:
        fail(problems, "上游对照分支被删掉了")
    tellomi_version = version.split("#ifdef TELLOMI_BUILD", 1)[1].split("#else", 1)[0]
    if 'AppName = "Tellomi"' not in tellomi_version:
        fail(problems, "version.h 的 Tellomi 分支没有应用名")
    if 'AppName = "Telegram Desktop"' not in version.split("#else // TELLOMI_BUILD", 1)[1]:
        fail(problems, "version.h 的上游分支被删掉了")
    api_branch = config_h.split("#ifdef TELLOMI_BUILD", 1)[1]
    api_match = re.match(
        r'\nconstexpr auto ApiId = 1;\nconstexpr auto ApiHash = "([0-9a-f]{32})";',
        api_branch,
    )
    if api_match is None:
        fail(problems, "TELLOMI_BUILD 的 api id / api hash 不是移动端那一组")
    elif api_match.group(1) == "344583e45741c457fe1862106095a5eb":
        fail(problems, "TELLOMI_BUILD 仍会落到上游测试 api")
    elif hashlib.sha256(api_match.group(1).encode()).hexdigest() != MOBILE_API_HASH_SHA256:
        fail(problems, "TELLOMI_BUILD 的 api hash 与移动端 gradle 默认值不一致")

    apply = dc.split("bool DcOptions::ApplyOneOption(", 1)[1].split(
        "std::vector<DcId> DcOptions::CountOptionsDifference", 1)[0]
    if not gate_installs_only_allowed(apply):
        fail(problems, "ApplyOneOption 没有在拒绝禁止地址之后写入端点")
    if gate_installs_only_allowed(drop_forbidden_check(apply)):
        fail(problems, "负向变异失效：去掉禁止地址判断后守卫仍通过")
    if gate_installs_only_allowed(add_unconditional_return(apply)):
        fail(problems, "负向变异失效：加回无条件 return false 后守卫仍通过")
    if "emplace" not in drop_forbidden_check(apply):
        fail(problems, "负向变异把写入语句一起删掉了")
    if "toIPv4Address" not in dc:
        fail(problems, "源码没有调用 toIPv4Address")
    for gate in ("constructAddOne", "constructFromSerialized", "loadFromFile"):
        if gate not in dc:
            fail(problems, f"缺少入口 {gate}")
    construct = dc.split("void DcOptions::constructTellomi()", 1)[1].split("#endif // TELLOMI_BUILD", 1)[0]
    if "readBuiltInPublicKeys" in construct or "kPublicRSAKeys" in construct:
        fail(problems, "constructTellomi 仍装入 Telegram RSA")
    if "applyOneGuarded" not in construct:
        fail(problems, "constructTellomi 没有把端点送进协议栈")
    if "qFatal" not in construct or "MTProto wiring is not implemented" in construct:
        fail(problems, "装入失败时没有终止，或仍停在未接线的失败")
    if "8.137.39.82" not in dc or "10443" not in dc:
        fail(problems, "没有内置成都 dev DC")
    for fingerprint in MOBILE_RSA_FINGERPRINTS:
        if str(fingerprint) not in construct:
            fail(problems, "constructTellomi 没有核对移动端 RSA 指纹")
    try:
        pems = tellomi_pems(dc)
    except (IndexError, subprocess.CalledProcessError, RuntimeError) as exc:
        fail(problems, f"无法解析 Tellomi RSA：{exc}")
        pems = []
    if len(pems) != 2:
        fail(problems, "Tellomi RSA 不是移动端的两把公钥")
    else:
        try:
            found = tuple(rsa_fingerprint(pem) for pem in pems)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            fail(problems, f"无法计算 RSA 指纹：{exc}")
            found = ()
        if found and found != MOBILE_RSA_FINGERPRINTS:
            fail(problems, "Tellomi RSA 指纹与移动端不一致")
    telegram_keys = dc.split("const char *kPublicRSAKeys[]", 1)[1].split("#ifdef TELLOMI_BUILD", 1)[0]
    if "8.137.39.82" in telegram_keys:
        fail(problems, "Telegram 内置表被改成了 Tellomi 地址")
    if "void LastCrashedWindow::sendReport() {\n#ifdef TELLOMI_BUILD\n\treturn;" not in crash:
        fail(problems, "sendReport 在 Tellomi 构建里仍会访问 tdesktop.com")
    if "void LastCrashedWindow::checkingFinished() {\n#ifdef TELLOMI_BUILD\n\treturn;" not in crash:
        fail(problems, "checkingFinished 在 Tellomi 构建里仍会继续上报")
    loader = (WIN / "Telegram/SourceFiles/mtproto/config_loader.cpp").read_text(encoding="utf-8")
    special = loader.split("void ConfigLoader::createSpecialLoader() {", 1)[1].split(
        "const auto testMode", 1)[0]
    if "#ifdef TELLOMI_BUILD" not in special or "\treturn;" not in special:
        fail(problems, "Tellomi 构建仍会向 Telegram 拉取备用 DC")
    instance = (WIN / "Telegram/SourceFiles/mtproto/mtp_instance.cpp").read_text(encoding="utf-8")
    unixtime = instance.split("void Instance::Private::syncHttpUnixtime() {", 1)[1].split(
        "if (base::unixtime::http_valid()", 1)[0]
    if "#ifdef TELLOMI_BUILD" not in unixtime or "\treturn;" not in unixtime:
        fail(problems, "Tellomi 构建仍会向 Telegram 请求时间")

    builtins = builtin_addresses(dc)
    cases = {
        "10.0.2.2": True,
        "::ffff:10.0.2.2": True,
        "127.0.0.1": True,
        "::1": True,
        "149.154.175.50": True,
        "::ffff:149.154.175.50": True,
        "2001:b28:f23d:f001::a": True,
        "8.8.8.8": False,
        "8.137.39.82": False,
        "not-an-ip": True,
    }
    for ip, expect in cases.items():
        if forbidden(ip, builtins) != expect:
            fail(problems, f"地址判断不符合预期：{ip}")
    if not forbidden("::ffff:" + next(iter(builtins)), builtins):
        fail(problems, "映射后的内置地址没有被拒绝")

    build_bat = (WIN / "Telegram/build/build.bat").read_text(encoding="utf-8")
    if not packaging_blocked(build_bat):
        fail(problems, "build.bat 仍会按 Telegram.exe / Updater.exe 去打包")
    if packaging_blocked(drop_packaging_block(build_bat)):
        fail(problems, "负向变异失效：去掉打包拦截后守卫仍通过")
    if "#define TellomiBuild 1" not in iss:
        fail(problems, "安装脚本没有默认 TellomiBuild")

    for path in TEL.rglob("*"):
        if not path.is_file() or path.name == "check_tellomi_guard.py" or path.suffix == ".pyc":
            continue
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        banned = ["10.0.2.2", "149.154.", "344583e45741c457fe1862106095a5eb"]
        if path.name != "UPSTREAM_PATCHES.md":
            banned.append("8.137.39.82")
        for item in banned:
            if item in text:
                fail(problems, f"{path.relative_to(ROOT)} 含有 {item}")
    if "发现" not in scope or "邮箱" not in scope or "还没写" not in scope:
        fail(problems, "SCOPE.md 没有写范围或未实现的连接")

    listed = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-s"], text=True)
    links = [line for line in listed.splitlines() if line.startswith("160000 ")]
    if len(links) != 36:
        fail(problems, f"gitlink 数量是 {len(links)}，期望 36")

    cmake_bin = subprocess.run(["cmake", "-P", str(TEL / "tellomi.cmake")], capture_output=True, text=True)
    if cmake_bin.returncode != 0 or "TELLOMI_BUILD default ON" not in cmake_bin.stdout + cmake_bin.stderr:
        fail(problems, "cmake -P 没有确认 TELLOMI_BUILD 默认 ON")

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(
        "tellomi windows guard ok "
        f"({len(links)} submodule pins, {len(cases)} address cases; "
        "Qt toIPv4Address was not compiled or executed)"
    )
    print("negative: ApplyOneOption without the forbidden check is rejected")
    print("negative: ApplyOneOption with an unconditional return is rejected")
    print("negative: build.bat without the packaging exit is rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
