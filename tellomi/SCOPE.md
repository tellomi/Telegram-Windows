# 范围：只接现有聊天

这棵源码还不是可用的 Tellomi 桌面端。本机没有做 Windows 或 macOS 原生编译。

导入提交的根树已在本仓库重算，数字写在 `tellomi/UPSTREAM.md`。私有总仓这次读不到，`clients/windows` 没有从总仓再算。这只收口源码迁移，聊天连接还没写。

现在只准备接 teamgram 聊天。不接发现，不接 @tellomi。不为桌面补 Telegram 里和聊天验收无关的服务。

邮箱登录先不做。总仓 `AGENTS.md` 写明邮箱登录暂缓。本轮没有改移动端，也没有另写一套邮箱协议。

首阶段聊天验收（都还没在桌面端跑过）：

- 登录、退出
- 会话列表
- 历史消息收发
- 图片和文件
- 已读
- 断线重连后的同步

`TELLOMI_BUILD` 默认 ON。这不是已经接上的聊天连接，登录验收还没做。

默认构建会停在配置阶段之后的进程入口：`DcOptions` 构造时 `qFatal`。缺 `TELLOMI_DC_CONFIG` 或 `TELLOMI_SERVER_PUBLIC_KEY`，或文件不存在，或文件在但 MTProto 还没写，都在这里失败。配置文件不会被送进协议栈，上游 RSA 也不会装入。

同时：

- 输出名是 Tellomi，安装脚本默认打 `Tellomi.exe` 和 `tellomi-setup`，不是 `Telegram.exe` / `tsetup`
- 自动更新和崩溃上报关掉。崩溃收集域名只留在上游分支里
- `ApplyOneOption` 在 forbidden 判断之后仍无条件返回，所以任何地址都写不进去。只留 forbidden 判断的话，非 Telegram 地址会落到 `emplace`。守卫对这种删改会失败。地址样例用 Python 的 `ipaddress` 表达规则，没有编译 Qt，也没有执行 `QHostAddress::toIPv4Address`
- `Telegram/build/build.bat` 默认直接退出。它原本找 `Telegram.exe` 和 `Updater.exe`，调用安装器时也不传 `TellomiBuild`。Tellomi 构建没有 Updater，这条链不能当正式出包。只有 `TELLOMI_UPSTREAM_PACKAGE=1` 才走到上游对照打包，并传 `/dTellomiBuild=0`

只有显式 `-DTELLOMI_BUILD=OFF` 才回到上游 DC 和 Telegram 安装包名字。那不是 Tellomi 包。

地址和公钥不写在仓库里。Qt 和预编译依赖还没核。没有 Windows 原生编译。
