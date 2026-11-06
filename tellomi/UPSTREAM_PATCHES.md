# UPSTREAM_PATCHES — Windows 桌面（Telegram Desktop）

上游是 `telegramdesktop/tdesktop` 标签 `v7.3.5`，提交 `3a2a9a34e833d3243a13787215b8a7cdcf5dc3c3`。
只登记相对这一版的 Tellomi 改动。依赖子模块没有改。

| 文件 | 原因 |
| --- | --- |
| `CMakeLists.txt` | 在加入子目录之前包含 `tellomi/tellomi.cmake`。 |
| `tellomi/tellomi.cmake` | `TELLOMI_BUILD` 默认 ON。同时关掉自动更新和崩溃上报。 |
| `Telegram/CMakeLists.txt` | `TELLOMI_BUILD` 时输出名是 Tellomi，bundle id 是 `app.tellomi.desktop`。 |
| `Telegram/build/setup.iss` | 默认 `TellomiBuild 1`，安装包是 `Tellomi.exe` / `tellomi-setup`。上游名字留在 `#else`。 |
| `Telegram/build/build.bat` | 默认退出，不签 `Telegram.exe`、不要求 `Updater.exe`、不调用安装器。`TELLOMI_UPSTREAM_PACKAGE=1` 才走上游对照，并传 `/dTellomiBuild=0`。 |
| `Telegram/cmake/telegram_options.cmake` | Tellomi 构建拒绝 Telegram 测试 api。不要求为了配置去填 Telegram api id。 |
| `Telegram/SourceFiles/config.h` | `TELLOMI_BUILD` 不使用上游测试 api id / api hash。 |
| `Telegram/SourceFiles/core/version.h` | `TELLOMI_BUILD` 时应用名和 AppId 改为 Tellomi。版本号仍是上游 7.3.5。 |
| `Telegram/SourceFiles/mtproto/mtproto_dc_options.h` | 声明 `constructTellomi()`。 |
| `Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp` | 构造时 `qFatal`，不装入 RSA，不把配置送进协议栈。`ApplyOneOption` 在 forbidden 判断之后仍无条件 `return false`，所以非 Telegram 地址也写不进去。 |
| `Telegram/SourceFiles/core/crash_report_window.cpp` | `TELLOMI_BUILD` 时上报函数直接返回，不访问崩溃收集域名。 |
| `Telegram/SourceFiles/boxes/about_box.cpp` | `TELLOMI_BUILD` 时版本链接不打开上游下载站。 |

没有改发现、AI、邮箱登录。没有填 DC、API hash 或 RSA。
