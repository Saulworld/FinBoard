# FinBoard 后续更新指南

## 发布原则

日常使用目录保存真实数据，GitHub目录只保存脱敏公开内容。每次更新先在私人主项目完成修改，再生成新的公开副本，与现有公开目录比较后更新；不直接从日常目录提交。

## 每次更新顺序

1. 在日常项目中完成修改并更新私有变更记录。
2. 每次准备上传都递增公开版本号，并同步更新`docs/VERSION`、README当前版本及公开CHANGELOG的新版本章节。
3. 运行项目测试：

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -q
   ```

4. 重新打包并更新固定的`FinBoard/`脱敏副本：

   ```powershell
   .\scripts\export_github.ps1
   ```

5. 运行公开包检查：

   ```powershell
   .\scripts\audit_public_package.ps1 -Path "公开副本目录"
   ```

6. 准备真正推送时，在`docs/UPLOAD_HISTORY.md`按版本顺序新增北京时间、分支、版本和更新内容。
7. 在公开仓库目录中检查变更：

   ```powershell
   git status --short
   git diff --stat
   git diff
   ```

8. 确认没有`.env`、数据库、个人JSON、备份、日志、未脱敏截图、卡片、CVC、手机号、姓名、地址或本机路径后再提交和推送。
9. 从`FinBoard/`生成版本ZIP，再提交、推送并创建同名Git标签；只有推送成功才算一次上传：

   ```powershell
   cd ..\FinBoard
   .\scripts\package_finboard.ps1
   ```

## 绝对不要上传

- `data/`中除`ai_monitor.json`和目录说明外的文件；
- 日常项目的私有`CHANGELOG.md`、`backups/`、`scratch/`和ZIP；
- `.env`、API Key、Token、证书和任何登录凭据；
- 未脱敏的终端输出、浏览器截图、Issue和Pull Request附件。

## 更新失败时

不要强制覆盖远端。先检查`git remote -v`、`git status`、当前分支和远端最新提交；保留本地配置与私有数据，再决定拉取、变基或重新生成公开副本。
