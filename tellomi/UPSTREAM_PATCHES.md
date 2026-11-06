# UPSTREAM_PATCHES — Windows 桌面（Telegram Desktop）

上游是 `telegramdesktop/tdesktop` 标签 `v7.3.5`，提交 `3a2a9a34e833d3243a13787215b8a7cdcf5dc3c3`。
只登记相对这一版的 Tellomi 改动。依赖子模块没有改。

| 文件 | 原因 |
| --- | --- |
| `CMakeLists.txt` | 在加入子目录之前包含 `tellomi/tellomi.cmake`，让 `TELLOMI_BUILD` 传到后面的目标。 |
| `tellomi/tellomi.cmake` | 新文件。打开 `TELLOMI_BUILD` 时定义同名宏，并关掉 Telegram 自动更新。 |
| `Telegram/cmake/telegram_options.cmake` | `TELLOMI_BUILD` 拒绝 `TDESKTOP_API_TEST` 和上游公开的测试 api_id / api_hash。不写入 Tellomi 的 api_id。 |
| `Telegram/SourceFiles/core/version.h` | `TELLOMI_BUILD` 时应用名和 AppId 改为 Tellomi。版本号仍是上游 7.3.5。 |
| `Telegram/SourceFiles/mtproto/mtproto_dc_options.h` | 声明 `constructTellomi()`。 |
| `Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp` | `TELLOMI_BUILD` 不装入上游内置 DC 和 Telegram RSA。只读环境变量 `TELLOMI_DC_CONFIG`。拒绝本机模拟器地址、环回地址，以及上游内置的 Telegram DC。 |

没有改发现、AI、邮箱登录。没有填 DC、API hash 或 RSA。
