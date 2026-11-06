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

工作树约 86 MB。索引 6969 条（普通文件 6905、可执行位 28、gitlink 36）。依赖的 URL 和 SHA 在本仓库根 `.gitmodules`，路径相对仓库根。依赖内容不在本仓。

在仓库根初始化某一个依赖：

```bash
git submodule update --init --depth 1 cmake
```

36 个 gitlink 是 v7.3.5 的上游 pin。独立复审已核对它们都能取到。Qt，以及构建文档里的预编译依赖，这次没有下载，也没有在 CI 里验证。没有 Windows 原生编译。

要换上游版本：取新标签，确认 `api.tl` 的 layer 仍等于 teamgram-server 当时的 layer，再把源码差量合进本仓库根，并按新提交重写这 36 个 gitlink。不要把整棵上游改回 submodule。Tellomi 自己的文件在 `tellomi/`，更新时保留。macOS 在独立仓库 `tellomi/Telegram-macOS`。两边的 libprisma pin 不是同一个提交，不能合成一个。

原生 macOS 的已审树在总仓 squash `59f5c5801885a90ad5ef7f180fd99ca786a80bc1`（#1833，原 head `82cfb8993e221e082372a8ab3c3a1229189fe266`）。它没有原生编译，没有接上聊天，没有发布。macOS 的 libprisma pin 仍是 `31a5d6fbbef8136e4a2b3adaf7b95e2ccaa7436d`；Windows 的 libprisma 在 `Telegram/ThirdParty/libprisma`，是 v7.3.5 自己的 gitlink。两个 pin 不要合成一个。`overtake/TelegramSwift` 不是这套源码。tdesktop 这棵树也能编 Qt 版 macOS，那不是 `tellomi/Telegram-macOS`。
