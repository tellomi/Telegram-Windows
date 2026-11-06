# Copyright 2026 重庆半格智能科技有限公司
# SPDX-License-Identifier: AGPL-3.0-only
"""可执行检查：默认 Tellomi 构建不能打出 Telegram 安装包，也不能收下上游 DC。不编译客户端。"""
from __future__ import annotations

import ipaddress
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WIN = ROOT / "clients" / "windows"
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
    if "Qt" not in upstream or "未" not in upstream:
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

    apply = dc.split("bool DcOptions::ApplyOneOption(", 1)[1].split("auto i = data.find(dcId);", 1)[0]
    if "TellomiEndpointForbidden" not in apply or "return false;" not in apply:
        fail(problems, "ApplyOneOption 没有拦住后续写入")
    if "toIPv4Address" not in dc.split("bool TellomiEndpointForbidden", 1)[0].split("TellomiNormalizedAddress", 1)[-1] and "toIPv4Address" not in dc:
        fail(problems, "地址归一没有处理 IPv4-mapped IPv6")
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

    # 负向：守卫自己必须能发现被改回上游的默认值。
    if re.search(r'option\(TELLOMI_BUILD\s+"[^"]+"\s+ON\)', 'option(TELLOMI_BUILD "x" OFF)'):
        fail(problems, "负向检查失效：OFF 也被当成默认 ON")
    if "#define TellomiBuild 1" not in iss:
        fail(problems, "安装脚本没有默认 TellomiBuild")

    for path in TEL.rglob("*"):
        if not path.is_file() or path.name == "check_tellomi_guard.py":
            continue
        text = path.read_text(encoding="utf-8")
        for banned in ("10.0.2.2", "149.154.", "8.137.39.82", "344583e45741c457fe1862106095a5eb"):
            if banned in text:
                fail(problems, f"{path.relative_to(ROOT)} 含有 {banned}")
    if "发现" not in scope or "邮箱" not in scope or "还没写" not in scope:
        fail(problems, "SCOPE.md 没有写范围或未实现的连接")

    listed = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-s", "clients/windows"], text=True)
    links = [line for line in listed.splitlines() if line.startswith("160000 ")]
    if len(links) != 36:
        fail(problems, f"gitlink 数量是 {len(links)}，期望 36")

    cmake_bin = subprocess.run(["cmake", "-P", str(TEL / "tellomi.cmake")], capture_output=True, text=True)
    if cmake_bin.returncode != 0 or "TELLOMI_BUILD default ON" not in cmake_bin.stdout + cmake_bin.stderr:
        fail(problems, "cmake -P 没有确认 TELLOMI_BUILD 默认 ON")

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"tellomi windows guard ok ({len(links)} submodule pins, {len(cases)} address cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
