# 上游与更新

| 项 | 值 |
| --- | --- |
| 上游 | https://github.com/telegramdesktop/tdesktop |
| 标签 | `v7.3.5` |
| 提交 | `3a2a9a34e833d3243a13787215b8a7cdcf5dc3c3` |
| 许可 | GPL-3.0，另加 OpenSSL 链接例外（上游 `LEGAL`） |
| API layer | 232（`Telegram/SourceFiles/mtproto/scheme/api.tl` 的 `// LAYER 232`） |
| 服务端 | `tellomi/teamgram-server` master 的 README 写 API Layer 232（vendored `proto/`） |
| 未采用 | `v7.4.0`（`6d7e0ab348cb2a5520776de442e215833f4573c0`）是 layer 233，比服务端高一层 |

工作树约 86 MB、6926 个文件，另有 36 个 gitlink。依赖的 URL 和 SHA 在仓库根 `.gitmodules`，路径前缀是 `clients/windows/`。依赖内容不在本仓。

在仓库根初始化某一个依赖：

```bash
git submodule update --init --depth 1 clients/windows/cmake
```

36 个 gitlink 是 v7.3.5 的上游 pin。独立复审已核对它们都能取到。Qt，以及构建文档里的预编译依赖，这次没有下载，也没有在 CI 里验证。没有 Windows 原生编译。

要换上游版本：取新标签，确认 `api.tl` 的 layer 仍等于 teamgram-server 当时的 layer，再把源码差量合进 `clients/windows/`，并按新提交重写这 36 个 gitlink。不要把整棵上游改回 submodule。Tellomi 自己的文件在 `clients/windows/tellomi/`，更新时保留。和 macOS 那一支合并时，两边的 `.gitmodules`、硬编码豁免和文档都要留下。两边的 libprisma pin 不是同一个提交，不能合成一个。

原生 macOS 源码在 #1833，head `82cfb8993e221e082372a8ab3c3a1229189fe266`。2026-11-06 复核时它还没进 `main`（`main` 仍是 `c9b4e1f2`），所以本支没有 `clients/macos`。`overtake/TelegramSwift` 对 GitHub API 仍是 404。官方仓库是 `TelegramMessenger/telegram-macos`。`main` 合入那一支之后，用普通 merge 保留两边的 `.gitmodules`、`AGENTS.md`、`CLAUDE.md`、`MODULE_BOUNDARIES.md`，以及各自的 libprisma pin。不 force，不 rebase 已经推过的历史。tdesktop 这棵树也能编 Qt 版 macOS，那不是 #1833 的原生 macOS 源码。
