# FinBoard Python代码维护指南

## 应用入口

`app/main.py`只负责创建FastAPI应用、挂载静态目录、注册Jinja环境、装配路由和渲染首页。业务接口应放入`app/routers/`，不要重新堆回`main.py`。

## 路由模块

| 模块 | 职责 |
| --- | --- |
| `routers/portfolio.py` | 自选股、持仓CRUD、交易流水、组合行情与汇率折算 |
| `routers/stock.py` | 个股详情、图表、财务数据和批量报价 |
| `routers/briefing.py` | 每日简报、报告正文和刷新导入 |
| `routers/cards.py` | 境外工具页面、CRUD及选项配置 |
| `routers/phones.py` | 境外号码页面、CRUD及选项配置 |
| `routers/influencers.py` | 达人名录、操作日志、日报页面和刷新API |

新增页面时在独立路由文件中实现，并在`app/routers/__init__.py`与`app/main.py`注册。

## 数据模型

`app/models.py`当前只有以下SQLAlchemy模型：

- `WatchlistItem`：自选股；
- `Holding`：当前持仓；
- `HoldingTransaction`：加仓、减仓和平仓流水；
- `DailyBriefing`：结构化每日股票判断；
- `DailyReport`：HTML/TXT日报正文。

不存在`Preference`模型，也不存在`data/app.db`。实际数据库路径由`app/config.py`配置，默认是`data/portfolio.db`。

## 行情链路

```text
页面/API → MarketDataService → 数据源Provider → 标准QuoteData/QuoteView
```

`app/providers.py`负责第三方协议差异，`app/services.py`负责选择顺序、缓存、批量并发、详情合并和外汇报价。不要在路由层直接调用yfinance或第三方HTTP接口。

组合汇总使用`app/portfolio.py`。成本币种取决于持仓市场，市值币种取决于行情返回值，两者分别折算后再汇总。

## JSON数据链路

以下数据仍存放在JSON：

- `cards.json`、`card_options.json`
- `phones.json`、`phone_options.json`
- `influencers.json`、`influencer_options.json`
- `influencer_news.json`、`influencer_logs.json`

底层统一使用`app/json_store.py`：

- `load_json()`：带锁读取和容错；
- `save_json_atomic()`：写入同目录临时文件、`fsync`、`os.replace`；
- `update_json()`：锁住完整读改写事务；
- `json_file_transaction()`：供多步CRUD持有同一把可重入锁。

严禁新增直接覆盖JSON文件的代码。

## 达人日报链路

```text
influencers.json
  → influencer_sources.py真实采集
  → fetch_influencer_news.py按真实帖子计数
  → OpenAI Responses API翻译/归类/总结
  → influencer_news.json
  → influencers_daily.html
```

没有X或OpenAI凭证时，系统保留真实原文或显示配置警告，不使用静态模板冒充当日动态。

## 前端组织

- `templates/*.html`：Jinja结构和页面DOM；
- `static/css/style.css`：公共样式；
- `static/css/cards.css`、`phones.css`：页面样式；
- `static/js/app.js`：公共PJAX、表格和行情刷新；
- `static/js/cards.js`、`phones.js`：页面交互。

后续新增大量页面脚本或样式时继续放入独立静态文件，不要塞回模板。

## 修改后的验证

1. 运行`python -m compileall -q app`；
2. 运行`python -m unittest discover -s tests -v`；
3. 导入`app.main`确认所有路由依赖存在；
4. 对涉及页面做HTTP烟雾测试；
5. 更新`CHANGELOG.md`。
