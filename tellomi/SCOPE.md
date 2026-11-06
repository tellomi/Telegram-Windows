# 范围：只接现有聊天

这棵源码还不是可用的 Tellomi 桌面端。本机没有做 Windows 或 macOS 原生编译。

现在只准备接 teamgram 聊天。不接发现，不接 @tellomi。不为桌面补 Telegram 里和聊天验收无关的服务。

邮箱登录先不做。总仓 `AGENTS.md` 写明邮箱登录暂缓。本轮没有改移动端，也没有另写一套邮箱协议。

首阶段聊天验收（都还没在桌面端跑过）：

- 登录、退出
- 会话列表
- 历史消息收发
- 图片和文件
- 已读
- 断线重连后的同步

`TELLOMI_BUILD=ON` 时：

- 不使用 Telegram 自动更新
- 不装入上游内置 DC，也不装入 Telegram RSA
- 地址只来自进程环境变量 `TELLOMI_DC_CONFIG`，文件格式见 `dc-config.example`
- 拒绝本机模拟器地址、环回地址，以及上游内置的 Telegram DC
- 不在仓库里写 DC、api_hash 或 RSA

没设 `TELLOMI_BUILD` 时，这棵树仍是上游 Telegram Desktop，会使用上游自己的 DC。不要把那个目标打成 Tellomi 安装包。
