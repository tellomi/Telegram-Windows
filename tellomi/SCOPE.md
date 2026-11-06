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

`TELLOMI_BUILD` 默认 ON。这一步只把 dev DC 和服务器 RSA 装进 `DcOptions`。登录验收还没做，不能据此说已经接通。

默认构建用上游同一条 `RSAPublicKey` 和 `applyOneGuarded` 路径装入成都 dev DC，以及移动端的两把服务器公钥。指纹对不上、或端点被拒绝时，`DcOptions` 构造 `qFatal`。上游 RSA 不装入。备用 DC 拉取和用上游域名对时也在 Tellomi 构建里直接返回。登录、会话和收发还没写进验收。

同时：

- 输出名是 Tellomi，安装脚本默认打 `Tellomi.exe` 和 `tellomi-setup`，不是 `Telegram.exe` / `tsetup`
- 自动更新和崩溃上报关掉。崩溃收集域名只留在上游分支里
- `ApplyOneOption` 先拒绝 Telegram 内置地址、回环和模拟器地址，其它地址才写入。去掉这段拒绝，或在拒绝之后再无条件返回，守卫都会失败。地址样例用 Python 的 `ipaddress` 表达规则，没有编译 Qt，也没有执行 `QHostAddress::toIPv4Address`
- `Telegram/build/build.bat` 默认直接退出。它原本找 `Telegram.exe` 和 `Updater.exe`，调用安装器时也不传 `TellomiBuild`。Tellomi 构建没有 Updater，这条链不能当正式出包。只有 `TELLOMI_UPSTREAM_PACKAGE=1` 才走到上游对照打包，并传 `/dTellomiBuild=0`

只有显式 `-DTELLOMI_BUILD=OFF` 才回到上游 DC 和 Telegram 安装包名字。那不是 Tellomi 包。

服务器公钥按上游方式放在协议源码里，不抄进这份说明。Qt 和预编译依赖还没核。没有 Windows 原生编译。没有登录和收发的实测。
