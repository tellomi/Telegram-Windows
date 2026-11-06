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

要换上游版本：取新标签，确认 `api.tl` 的 layer 仍等于 teamgram-server 当时的 layer，再把源码差量合进 `clients/windows/`，并按新提交重写这 36 个 gitlink。不要把整棵上游改回 submodule。Tellomi 自己的文件在 `clients/windows/tellomi/`，更新时保留。

macOS 原生客户端不在这棵树里。`overtake/TelegramSwift` 在 2026-11-06 的 GitHub API 上是 404。现行官方仓库是 `TelegramMessenger/telegram-macos`（GPL-2.0，`macosswift/telegram` 会跳到这里）。那一棵另开 PR，不在这次导入里。tdesktop 也能编 macOS，但那是 Qt 客户端，不是这支要接的原生 macOS 源码。
