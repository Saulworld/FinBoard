# FinBoard 使用与 GitHub 发布指南

## 1. 使用公开版本

需要 Windows 10/11 和 Python 3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\start_local.ps1
```

浏览器打开 `http://127.0.0.1:18010`。首次启动会创建空数据库和空的个人 JSON，不会生成示例账户、手机号或卡片。

可选数据源在 `.env` 中配置。每日简报项目不在 FinBoard 相邻目录时，设置 `BRIEFING_DIR`。不要把 `.env` 发给别人或提交到仓库。

## 2. 本地数据边界

以下内容永远只留在本机：

- `.env` 和任何 API Key、Token、密码、证书；
- `data/portfolio.db` 及其他 SQLite 文件；
- `cards.json`、`wallet_cards.json`、`phones.json`、选项文件和旧版数据；
- `backups/`、`scratch/`、日志、截图、导出报告和私有变更历史；
- 卡号、CVC、手机号、姓名、地址、登录方式、持仓与交易记录。

`.gitignore` 是最后一道防误传保护，不是脱敏工具。已经被 Git 跟踪的内容不会因为后来加入 `.gitignore` 而自动消失。

## 3. 生成可上传副本

不要直接上传日常使用目录。在项目根目录运行：

```powershell
.\scripts\export_github.ps1
```

脚本会在桌面创建`FinBoard-v0.1`独立目录和 ZIP，只复制代码、公开文档、测试、AI 公共数据和 `update-ai-monitor` skill，并执行隐私检查。ZIP 方便网页上传；目录方便先检查和初始化 Git。

再次手工检查：

```powershell
.\scripts\audit_public_package.ps1 -Path "桌面上的新版本目录"
```

至少随机打开 README、CHANGELOG、`.env.example`、测试、`app/utils.py`、`app/importer.py` 和 `data/`，确认看不到你的资料。

## 4. 上传 GitHub

推荐创建一个全新的空仓库，不要导入旧目录或旧 Git 历史。

1. 在 GitHub 创建仓库，先设为 **Private** 完成复查；不要勾选自动生成 README、`.gitignore` 或 License。
2. 只使用桌面新版本目录，不使用日常数据目录。
3. 初始化并逐项检查：

   ```powershell
   git init -b main
   git add --dry-run .
   git status --short
   git add .
   git diff --cached --stat
   git diff --cached
   git commit -m "Initial public release"
   git remote add origin 你的仓库地址
   git push -u origin main
   ```

4. 在 GitHub 网页再次检查文件树、提交内容和 Actions 测试，通过后再决定是否改为 Public。

不要使用 `git add -f` 绕过忽略规则。不要上传桌面 ZIP 本身到仓库；ZIP 是传输副本，不是项目源文件。

## 5. GitHub 公开仓库规范

- **许可证**：本包代码使用 MIT License；隐私边界和第三方名称、商标、素材说明见 `docs/LEGAL.md`。
- **隐私**：提交、Issue、Pull Request、Discussion、Actions 日志和截图都可能公开。发布前必须脱敏。
- **安全报告**：启用 GitHub Private vulnerability reporting，让漏洞通过私密渠道报告；公开 Issue 不接收真实敏感数据。
- **安全功能**：建议启用 Dependabot alerts、secret scanning、push protection 和 CodeQL 默认扫描。公开仓库的部分安全功能可免费使用。
- **分支保护**：为 `main` 启用拉取请求、测试通过后合并和禁止直接强推。
- **贡献内容**：提交者必须有权提供代码、图片和数据；不得提交侵权、违法、恶意、绕过身份验证或规避金融合规的内容。
- **社区管理**：按 `CONTRIBUTING.md`、`CODE_OF_CONDUCT.md` 和 `SECURITY.md` 处理贡献、行为和安全问题。

## 6. 如果误传了敏感信息

立即执行以下顺序：

1. 撤销或轮换泄露的 Token、密码、证书或其他凭据。
2. 将仓库临时改为 Private，停止继续提交和转发链接。
3. 不要只删除最新文件；Git 历史、Pull Request、缓存、Fork 和他人 Clone 仍可能保留内容。
4. 按 GitHub 官方“Removing sensitive data from a repository”流程重写历史，并在需要时联系 GitHub Support 清理缓存引用。
5. 要求协作者重新克隆干净仓库，避免旧历史再次被推回。

官方参考：

- [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Best practices for repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories)
- [Managing security and analysis settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)
- [Adding a code of conduct](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-code-of-conduct-to-your-project)
