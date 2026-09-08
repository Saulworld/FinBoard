# FinBoard AI 项目地图

本文档以当前代码为准，供维护者和AI助手快速定位。执行修改前还必须读取项目根目录下的`.agents/AGENTS.md`。

## 1. 项目定位

FinBoard是一个仅监听本机的个人投资与境外工具管理Web应用，包含：

- 美股、ETF、港股、A股自选与行情详情；
- 多市场持仓、交易流水和统一币种汇总；
- 每日简报导入和浏览；
- 境外工具、银行卡与手机号管理；
- 达人名录、真实动态采集和AI中文日报。

## 2. 技术栈

- 后端：FastAPI、Uvicorn、SQLAlchemy；
- 前端：Jinja2、原生JavaScript、CSS、Chart.js；
- 行情：Yahoo Finance、腾讯财经，可选Finnhub和Twelve Data；
- AI总结：OpenAI Responses API；
- 数据库：SQLite与JSON混合存储。

## 3. 当前目录和职责

```text
FinBoard/
├── app/
│   ├── main.py                    # 应用装配、生命周期、首页
│   ├── config.py                  # 环境变量和路径
│   ├── db.py                      # SQLAlchemy Engine/Session
│   ├── models.py                  # SQLite模型
│   ├── portfolio.py               # 组合币种折算与汇总
│   ├── json_store.py              # JSON锁、原子写入、读改写事务
│   ├── providers.py               # 行情提供商适配
│   ├── services.py                # 行情聚合、缓存、并发和汇率
│   ├── influencer_sources.py      # X/Telegram/YouTube真实采集
│   ├── fetch_influencer_news.py   # 达人日报和OpenAI总结
│   ├── importer.py                # 每日简报导入
│   ├── utils.py                   # 格式化、规范化、JSON业务函数
│   ├── routers/
│   │   ├── portfolio.py           # 自选、持仓、交易、汇总API
│   │   ├── stock.py               # 个股和行情API
│   │   ├── briefing.py            # 每日简报
│   │   ├── cards.py               # 境外工具
│   │   ├── phones.py              # 境外号码
│   │   └── influencers.py         # 达人名录和日报API
│   ├── templates/                 # 仅保留Jinja结构和必要页面标记
│   └── static/
│       ├── css/                    # 全局及页面CSS
│       └── js/                     # 全局及页面JavaScript
├── data/
│   ├── portfolio.db               # SQLite主库
│   ├── cards.json                  # 境外工具
│   ├── phones.json                 # 境外号码
│   ├── influencers.json            # 达人名录
│   └── influencer_news.json        # 达人历史日报
└── start_local.ps1                # 127.0.0.1:8010启动脚本
```

## 4. 数据存储边界

SQLite文件是`data/portfolio.db`，存储以下表：

- `watchlist_items`
- `holdings`
- `holding_transactions`
- `daily_briefings`
- `daily_reports`

境外工具、手机号、达人和下拉选项仍使用`data/*.json`。所有JSON写入必须经过`app/json_store.py`，禁止直接用`open(..., "w")`覆盖。

## 5. 关键业务规则

### 持仓汇总

单只持仓保持原币种展示；组合总成本、总市值和总盈亏必须先按实时汇率折算到`PORTFOLIO_BASE_CURRENCY`，默认CNY。缺失任何行情或汇率时不允许输出部分汇总。

### 达人日报

- 只处理`status == "跟进中"`的达人；
- X通过官方近期搜索接口读取，需要`X_BEARER_TOKEN`；
- Telegram读取公开频道页面；YouTube读取官方Atom Feed；
- AI总结使用OpenAI Responses API，需要`OPENAI_API_KEY`；
- 未配置凭证或抓取失败时必须显示明确警告，绝不能生成预写行情或虚构帖子数量。

### JSON更新

记录CRUD必须在`json_file_transaction()`中完成完整的“读取—修改—原子替换”，防止并发覆盖。数据库内容修改仍需遵守`.agents/AGENTS.md`和`CHANGELOG.md`规范。

## 6. 验证命令

```powershell
python -m compileall -q app
python -m unittest discover -s tests -v
python -c "import app.main; print('IMPORT_OK')"
```
