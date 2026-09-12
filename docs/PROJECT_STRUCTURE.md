# FinBoard v0.3 项目结构

```text
FinBoard/
├─ app/          应用代码、页面模板和静态资源
├─ tests/        自动化测试
├─ data/         公开AI数据与本地数据边界说明
├─ docs/         使用、架构、设计、发布文档及非自动注册的Skill附件
├─ scripts/      发布打包与隐私检查脚本
├─ .agents/      项目规则
├─ .github/      社区规范、工作流、Issue模板和PR模板
├─ README.md     项目入口与使用说明
├─ CHANGELOG.md  公开版本变更记录
├─ LICENSE       开源许可证
└─ requirements.txt  Python依赖
```

版本写在README与CHANGELOG中。根目录只保留项目入口、许可证、变更记录、依赖和启动文件；GitHub社区治理文件归入`.github/`，隐私与第三方说明合并在`docs/LEGAL.md`。公开版的`update-ai-monitor`完整附件位于`docs/skills/update-ai-monitor/`，不会自动注册；唯一自动识别入口保留在私人主项目。业务代码、测试、文档、自动化脚本、公开数据和AI工作流分别归档，不混入本机数据库或用户资料。
