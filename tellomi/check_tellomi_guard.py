# Copyright 2026 重庆半格智能科技有限公司
# SPDX-License-Identifier: AGPL-3.0-only
"""结构检查：Tellomi 桌面守卫还在，且 tellomi/ 目录没有写入地址或测试 api_hash。不编译客户端。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WIN = ROOT / "clients" / "windows"
TEL = WIN / "tellomi"
UPSTREAM = "3a2a9a34e833d3243a13787215b8a7cdcf5dc3c3"


def main() -> int:
    version = (WIN / "Telegram/SourceFiles/core/version.h").read_text(encoding="utf-8")
    dc = (WIN / "Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp").read_text(encoding="utf-8")
    opts = (WIN / "Telegram/cmake/telegram_options.cmake").read_text(encoding="utf-8")
    cmake = (TEL / "tellomi.cmake").read_text(encoding="utf-8")
    scope = (TEL / "SCOPE.md").read_text(encoding="utf-8")
    upstream = (TEL / "UPSTREAM.md").read_text(encoding="utf-8")
    problems: list[str] = []
    if UPSTREAM not in upstream:
        problems.append("UPSTREAM.md 没有钉死提交")
    if "LAYER 232" not in upstream and "layer 232" not in upstream:
        problems.append("UPSTREAM.md 没有写 layer 232")
    if "TELLOMI_BUILD" not in version or 'AppName = "Tellomi"' not in version:
        problems.append("version.h 没有 Tellomi 应用名分支")
    if "constructTellomi();" not in dc or "TellomiEndpointForbidden" not in dc:
        problems.append("DC 构造没有走到 Tellomi 分支")
    if "10.0.2.2" not in dc:
        problems.append("DC 守卫没有拒绝 10.0.2.2")
    if "readBuiltInPublicKeys();" not in dc.split("constructTellomi()", 1)[-1].split("#endif // TELLOMI_BUILD", 1)[0]:
        pass
    tellomi_body = dc.split("void DcOptions::constructTellomi()", 1)[1].split("#endif // TELLOMI_BUILD", 1)[0]
    if "readBuiltInPublicKeys" in tellomi_body:
        problems.append("Tellomi DC 构造仍装入 Telegram RSA")
    if "TELLOMI_DC_CONFIG" not in dc:
        problems.append("没有读取 TELLOMI_DC_CONFIG")
    if "TDESKTOP_API_TEST" not in opts or "TELLOMI_BUILD" not in opts:
        problems.append("cmake 没有拒绝 Telegram 测试 api")
    if "DESKTOP_APP_DISABLE_AUTOUPDATE" not in cmake:
        problems.append("没有关掉自动更新")
    for path in TEL.rglob("*"):
        if not path.is_file() or path.name == "check_tellomi_guard.py":
            continue
        text = path.read_text(encoding="utf-8")
        for banned in ("10.0.2.2", "149.154.", "8.137.39.82", "344583e45741c457fe1862106095a5eb"):
            if banned in text:
                problems.append(f"{path.relative_to(ROOT)} 含有 {banned}")
    if "发现" not in scope or "邮箱" not in scope:
        problems.append("SCOPE.md 没有写发现和邮箱的范围")
    listed = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-s", "clients/windows"], text=True)
    links = [line for line in listed.splitlines() if line.startswith("160000 ")]
    if len(links) != 36:
        problems.append(f"gitlink 数量是 {len(links)}，期望 36")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"tellomi desktop guard ok ({len(links)} submodule pins)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
