# Copyright 2026 重庆半格智能科技有限公司
# SPDX-License-Identifier: AGPL-3.0-only
"""可执行检查：默认 Tellomi 构建不能打出 Telegram 安装包，也不能收下上游 DC。不编译客户端。"""
from __future__ import annotations

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


def write_gate_lost(apply_body: str) -> bool:
    """True when a non-forbidden address can still be stored.

    The TellomiEndpointForbidden branch alone is not enough: after that
    if-statement returns, ApplyOneOption must still return before emplace.
    """
    if "emplace" not in apply_body or "#ifdef TELLOMI_BUILD" not in apply_body:
        return True
    gate = apply_body.split("#ifdef TELLOMI_BUILD", 1)[1].split("#endif", 1)[0]
    without_forbidden = re.sub(
        r"if\s*\(\s*TellomiEndpointForbidden\b[^{]*\)\s*\{[^{}]*\}",
        "",
        gate,
        flags=re.S,
    )
    depth = 0
    for line in without_forbidden.splitlines():
        code = re.sub(r"//.*", "", line)
        if depth == 0 and re.search(r"\breturn\b", code):
            return False
        depth += code.count("{") - code.count("}")
        if depth < 0:
            depth = 0
    return True


def drop_unconditional_returns(apply_body: str) -> str:
    head, rest = apply_body.split("#ifdef TELLOMI_BUILD", 1)
    gate, tail = rest.split("#endif", 1)
    kept: list[str] = []
    depth = 0
    for line in gate.splitlines(keepends=True):
        code = re.sub(r"//.*", "", line)
        if depth == 0 and re.search(r"\breturn\b", code):
            continue
        kept.append(line)
        depth += code.count("{") - code.count("}")
    return head + "#ifdef TELLOMI_BUILD" + "".join(kept) + "#endif" + tail


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
    if not config_h.split("#ifdef TELLOMI_BUILD", 1)[1].startswith("\nconstexpr auto ApiId = 0;"):
        fail(problems, "TELLOMI_BUILD 仍会落到上游测试 api id")

    apply = dc.split("bool DcOptions::ApplyOneOption(", 1)[1].split(
        "std::vector<DcId> DcOptions::CountOptionsDifference", 1)[0]
    if write_gate_lost(apply):
        fail(problems, "ApplyOneOption 在 forbidden 判断之后仍会写入端点")
    mutated_apply = drop_unconditional_returns(apply)
    if not write_gate_lost(mutated_apply):
        fail(problems, "负向变异失效：删掉无条件 return false 后守卫仍认为不能写入")
    if "emplace" not in mutated_apply:
        fail(problems, "负向变异把写入语句一起删掉了")
    if "toIPv4Address" not in dc:
        fail(problems, "源码没有调用 toIPv4Address")
    for gate in ("constructAddOne", "constructFromSerialized", "loadFromFile"):
        if gate not in dc:
            fail(problems, f"缺少入口 {gate}")
    construct = dc.split("void DcOptions::constructTellomi()", 1)[1].split("#endif // TELLOMI_BUILD", 1)[0]
    if "readBuiltInPublicKeys" in construct or "applyOneGuarded" in construct:
        fail(problems, "constructTellomi 仍装入 Telegram RSA 或 DC")
    if "qFatal" not in construct or "MTProto wiring is not implemented" not in construct:
        fail(problems, "未实现的 MTProto 没有明确失败")
    if "void LastCrashedWindow::sendReport() {\n#ifdef TELLOMI_BUILD\n\treturn;" not in crash:
        fail(problems, "sendReport 在 Tellomi 构建里仍会访问 tdesktop.com")
    if "void LastCrashedWindow::checkingFinished() {\n#ifdef TELLOMI_BUILD\n\treturn;" not in crash:
        fail(problems, "checkingFinished 在 Tellomi 构建里仍会继续上报")

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
        for banned in ("10.0.2.2", "149.154.", "8.137.39.82", "344583e45741c457fe1862106095a5eb"):
            if banned in text:
                fail(problems, f"{path.relative_to(ROOT)} 含有 {banned}")
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
    print("negative: ApplyOneOption without unconditional return false is rejected")
    print("negative: build.bat without the packaging exit is rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
