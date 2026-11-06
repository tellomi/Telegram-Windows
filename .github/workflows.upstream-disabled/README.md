这些文件从上游 `.github/workflows/` 移来。GitHub 只执行 `.github/workflows/`，不会执行这个目录。

不要移回去。里面有 WinGet 发布、构建产物上传、Docker、snap 和 canary。这些发布 workflow 继续不执行。`.github/workflows/compile-windows.yml` 只在 PR 或手动触发时编译 Debug，不上传、不签名、不用仓库秘密。要恢复本目录里的任何一条，另开 PR，并且确认没有发布、上传或部署。
