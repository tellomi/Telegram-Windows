# 范围：只接现有聊天

这棵源码还不是可用的 Tellomi 桌面端。本机没有做 Windows 或 macOS 原生编译。

导入提交的根树已在本仓库重算，数字写在 `tellomi/UPSTREAM.md`。私有总仓这次读不到，`clients/windows` 没有从总仓再算。这只收口源码迁移，聊天连接还没写。

现在只准备接 teamgram 聊天。不接发现，不接 @tellomi。不为桌面补 Telegram 里和聊天验收无关的服务。

桌面端没有另写一套邮箱协议，也没有改移动端。探测调用了现有的 `account.sendVerifyEmailCode`，服务端返回见文末。

首阶段聊天验收（都还没在桌面端跑过）：

- 登录、退出
- 会话列表
- 历史消息收发
- 图片和文件
- 已读
- 断线重连后的同步

`TELLOMI_BUILD` 默认 ON。dev DC 和服务器 RSA 已装进 `DcOptions`。桌面进程没有跑过登录，不能据此说桌面端已经接通。

默认构建用上游同一条 `RSAPublicKey` 和 `applyOneGuarded` 路径装入成都 dev DC，以及移动端的两把服务器公钥。指纹对不上、或端点被拒绝时，`DcOptions` 构造 `qFatal`。上游 RSA 不装入。备用 DC 拉取和用上游域名对时也在 Tellomi 构建里直接返回。登录、会话和收发还没写进验收。

同时：

- 输出名是 Tellomi，安装脚本默认打 `Tellomi.exe` 和 `tellomi-setup`，不是 `Telegram.exe` / `tsetup`
- 自动更新和崩溃上报关掉。崩溃收集域名只留在上游分支里
- `ApplyOneOption` 先拒绝 Telegram 内置地址、回环和模拟器地址，其它地址才写入。去掉这段拒绝，或在拒绝之后再无条件返回，守卫都会失败。地址样例用 Python 的 `ipaddress` 表达规则，没有编译 Qt，也没有执行 `QHostAddress::toIPv4Address`
- `Telegram/build/build.bat` 默认直接退出。它原本找 `Telegram.exe` 和 `Updater.exe`，调用安装器时也不传 `TellomiBuild`。Tellomi 构建没有 Updater，这条链不能当正式出包。只有 `TELLOMI_UPSTREAM_PACKAGE=1` 才走到上游对照打包，并传 `/dTellomiBuild=0`

只有显式 `-DTELLOMI_BUILD=OFF` 才回到上游 DC 和 Telegram 安装包名字。那不是 Tellomi 包。

服务器公钥按上游方式放在协议源码里，不抄进这份说明。Qt 和预编译依赖还没核。没有 Windows 原生编译。

`tellomi/check_dev_dc_protocol.py` 用中间传输对编译进去的 dev DC 做了一次 MTProto 探测，不是桌面进程。探测完成了密钥交换，`help.getNearestDc` 返回 dc 1。`account.sendVerifyEmailCode` 的 loginChange 和 loginSetup 都返回 `500 AUTH_RESTART`。用号码 `0` 调 `auth.sendCode` 返回 `400 PHONE_NUMBER_INVALID`。没有用户会话，`messages.sendMessage` 和 `messages.getHistory` 没有发送。邮箱登录和聊天收发还没写完。
