# FinBoard 后续更新指南

## 发布原则

日常使用目录保存真实数据，GitHub目录只保存脱敏公开内容。所有准备上传的文件都必须先进入独立的`FinBoard/`公开仓库工作目录，不直接从日常目录提交。每次更新都同步填写公开`CHANGELOG.md`，保证线上每次变化都有记录。

## 每次更新顺序

1. 在日常项目中完成修改并更新私有变更记录。
2. 运行项目测试：

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -q
   ```

3. 生成新的公开副本：

   ```powershell
   .\scripts\export_github.ps1 -Version "下一版本号"
   ```

4. 运行公开包检查：

   ```powershell
   .\scripts\audit_public_package.ps1 -Path "公开副本目录"
   ```

5. 将准备上传的文件保存到`FinBoard/`公开仓库工作目录，并更新公开`CHANGELOG.md`。
6. 在公开仓库目录中检查变更：

   ```powershell
   git status --short
   git diff --stat
   git diff
   ```

7. 确认没有`.env`、数据库、个人JSON、备份、日志、未脱敏截图、卡片、CVC、手机号、姓名、地址或本机路径后再提交和推送。
8. 发布正式版本时创建对应标签，例如`v0.2`。

## 绝对不要上传

- `data/`中除`ai_monitor.json`和目录说明外的文件；
- 日常项目的私有`CHANGELOG.md`、`backups/`、`scratch/`和ZIP；
- `.env`、API Key、Token、证书和任何登录凭据；
- 未脱敏的终端输出、浏览器截图、Issue和Pull Request附件。

## 更新失败时

不要强制覆盖远端。先检查`git remote -v`、`git status`、当前分支和远端最新提交；保留本地配置与私有数据，再决定拉取、变基或重新生成公开副本。
