# UPSTREAM_PATCHES — Windows 桌面（Telegram Desktop）

上游是 `telegramdesktop/tdesktop` 标签 `v7.3.5`，提交 `3a2a9a34e833d3243a13787215b8a7cdcf5dc3c3`。
只登记相对这一版的 Tellomi 改动。依赖子模块没有改。

| 文件 | 原因 |
| --- | --- |
| `CMakeLists.txt` | 在加入子目录之前包含 `tellomi/tellomi.cmake`。 |
| `tellomi/tellomi.cmake` | `TELLOMI_BUILD` 默认 ON。编译进现有服务器端口 10443 和服务器 RSA。预发端口 11443 不编译进去。同时关掉自动更新和崩溃上报。 |
| `Telegram/CMakeLists.txt` | `TELLOMI_BUILD` 时输出名是 Tellomi，bundle id 是 `app.tellomi.desktop`。 |
| `Telegram/build/setup.iss` | 默认 `TellomiBuild 1`，安装包是 `Tellomi.exe` / `tellomi-setup`。上游名字留在 `#else`。 |
| `Telegram/build/build.bat` | 默认退出，不签 `Telegram.exe`、不要求 `Updater.exe`、不调用安装器。`TELLOMI_UPSTREAM_PACKAGE=1` 才走上游对照，并传 `/dTellomiBuild=0`。 |
| `Telegram/cmake/telegram_options.cmake` | Tellomi 构建拒绝 Telegram 测试 api。不要求为了配置去填 Telegram api id。 |
| `Telegram/SourceFiles/config.h` | `TELLOMI_BUILD` 使用与 Android `gradle.properties` 相同的 api id / api hash，并继续拒绝上游测试 api。 |
| `Telegram/SourceFiles/core/version.h` | `TELLOMI_BUILD` 时应用名和 AppId 改为 Tellomi。版本号仍是上游 7.3.5。 |
| `Telegram/SourceFiles/mtproto/mtproto_dc_options.h` | 声明 `constructTellomi()`。 |
| `Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp` | 内置 `8.137.39.82:10443`（dc 1 和 dc 2）。10443 是现有服务器上据称的生产端口，不是预发。预发端口 11443 不在表里。用上游 `RSAPublicKey` 装入移动端两把服务器公钥，指纹分别是 `4381149949997195609` 和 `12240908862933197005`。不装入上游 RSA。`ApplyOneOption` 仍拒绝 Telegram 地址、回环和模拟器地址，其余地址写入协议栈。公钥无效、指纹不符，或端点没有写入时 `qFatal`。不读 `TELLOMI_DC_CONFIG`。 |
| `Telegram/SourceFiles/core/crash_report_window.cpp` | `TELLOMI_BUILD` 时上报函数直接返回，不访问崩溃收集域名。 |
| `Telegram/SourceFiles/boxes/about_box.cpp` | `TELLOMI_BUILD` 时版本链接不打开上游下载站。 |
| `Telegram/SourceFiles/mtproto/config_loader.cpp`、`Telegram/SourceFiles/mtproto/mtp_instance.cpp` | Tellomi 构建不向 Telegram 拉取备用 DC，也不用上游域名对时。 |
| `tellomi/check_tellomi_guard.py` | 独立仓库根不再是总仓。守卫核对 10443 端点、移动端 RSA 指纹和 api 配置，并拒绝把禁止地址写入端点。确认 11443 没有编译进去。 |
| `tellomi/UPSTREAM.md`、`tellomi/NOTICE.md` | 路径改成独立仓库根，不再写 `clients/windows/`。 |
| `tellomi/check_import_tree.py`、`tellomi/UPSTREAM.md`、`tellomi/SCOPE.md` | 重算导入提交 `f1a8e9cf` 的根树。总仓读不到时只记录读不到，不把它写成已对照。 |
| `tellomi/check_dev_dc_protocol.py` | 记录已经跑过的 MTProto 探测。默认不连服务器，不读 api hash，不进入客户端构建。 |

| `.github/workflows.upstream-disabled/` | 上游自动构建、上传和 WinGet 工作流移出 `.github/workflows/`。文件保留。GitHub 不会执行这个目录。 |
| `.github/workflows/compile-windows.yml` | 只在 PR 或手动触发时编 Windows Debug。不上传产物，不签名，不传 api hash。开发者命令行从装上的 Visual Studio 18 找 `vcvars64.bat`。准备依赖前清掉 runner 上的预装缓存，否则 Qt 装完后 `tg_owt` 会因磁盘满而失败。 |
| `README.md` | 用带来源说明的仓库 README 替换 GitHub 初始化的两行 README。上游正文留在下面。这是必要的文档替换，不是 force 覆盖 main。 |

没有改发现或 AI。没有改服务端。桌面进程没有登录，也没有收发消息。

是否改连预发端口 11443：待确认。保持 10443 时，客户端指向现有服务器上据称的生产端口，和 Android 发布配置相同；以后若在桌面登录，写入会落在这个端口上。已经做过的探测也是对着 10443。改连 11443 则不再指向该生产端口，但会和 Android 发布配置、以及 10443 上的探测分开，而且 11443 还没有探测，RSA 和 api 配置是否相同也不知道。在确认之前不改端点。
