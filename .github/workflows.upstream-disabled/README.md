这些文件从上游 `.github/workflows/` 移来。GitHub 只执行 `.github/workflows/`，不会执行这个目录。

不要移回去。里面有 WinGet 发布、构建产物上传、Docker、snap 和 canary。Actions 保持关闭。要恢复任何一条，另开 PR，并且确认没有发布、上传或部署。
