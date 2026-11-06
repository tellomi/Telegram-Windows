# Copyright 2026 重庆半格智能科技有限公司
# SPDX-License-Identifier: AGPL-3.0-only
"""重算导入提交的根树，并在读得到总仓时对照 clients/windows。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT_COMMIT = "f1a8e9cf380988fdfc881fdb20cabf65ebd96519"
EXPECTED_TREE = "8f4a6328b4886f53a0a029d1c8c4d845f242f1c4"
MONOREPO = "tellomi/tellomi"


def git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )


def local_tree() -> str:
    commit = git(["rev-parse", f"{IMPORT_COMMIT}^{{commit}}"])
    if commit.returncode != 0 or commit.stdout.strip() != IMPORT_COMMIT:
        raise RuntimeError("导入提交不在本仓库")
    kind = git(["cat-file", "-t", f"{IMPORT_COMMIT}^{{tree}}"])
    if kind.returncode != 0 or kind.stdout.strip() != "tree":
        raise RuntimeError("导入提交的根不是 tree")
    tree = git(["rev-parse", f"{IMPORT_COMMIT}^{{tree}}"])
    if tree.returncode != 0:
        raise RuntimeError(tree.stderr.strip() or "无法重算导入根树")
    return tree.stdout.strip()


def ancestor() -> bool:
    return git(["merge-base", "--is-ancestor", IMPORT_COMMIT, "HEAD"]).returncode == 0


def monorepo_tree() -> tuple[str, str]:
    local = os.environ.get("TELLOMI_MONOREPO", "").strip()
    if local:
        path = Path(local)
        if not path.is_dir():
            return "unreadable", f"TELLOMI_MONOREPO 不存在"
        shown = git(["rev-parse", "HEAD:clients/windows"], cwd=path)
        if shown.returncode != 0:
            return "unreadable", "本地总仓没有 clients/windows"
        return "read", shown.stdout.strip()

    api = subprocess.run(
        ["gh", "api", f"repos/{MONOREPO}", "--jq", ".full_name"],
        capture_output=True,
        text=True,
    )
    if api.returncode != 0:
        detail = (api.stderr or api.stdout).strip().splitlines()
        reason = detail[-1] if detail else "gh api failed"
        if "404" in reason or "Not Found" in reason:
            reason = "GitHub 404"
        return "unreadable", reason

    remote = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{MONOREPO}.git", "HEAD"],
        capture_output=True,
        text=True,
    )
    if remote.returncode != 0 or not remote.stdout.strip():
        return "unreadable", "总仓 HEAD 取不到"
    return "unreadable", "总仓元数据可读，但没有把 clients/windows 树取下来对照"


def main() -> int:
    problems: list[str] = []
    try:
        tree = local_tree()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    if tree != EXPECTED_TREE:
        problems.append("导入根树与已记录的标识不一致")
    if not ancestor():
        problems.append("导入提交不是 HEAD 的祖先")
    status, detail = monorepo_tree()
    if status == "read" and detail != tree:
        problems.append("总仓 clients/windows 树与导入根树不一致")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"import {IMPORT_COMMIT}")
    print(f"tree {tree}")
    print("ancestor yes")
    if status == "read":
        print("monorepo clients/windows matches the import tree")
    else:
        print(f"monorepo unreadable: {detail}")
        print("clients/windows was not recomputed from the private monorepo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
