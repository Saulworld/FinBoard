---
name: update-ai-monitor
description: 核对并更新 FinBoard AI监控页中的主流模型、API Token价格、全部公开套餐类型和模型动态。用户要求更新AI信息、API价格、套餐价格、套餐档位、增加厂商或维护data/ai_monitor.json时使用；仅采用厂商官方来源，并保持人民币与美元原币种展示。
---

# 更新AI监控

维护 `data/ai_monitor.json`，让 `/ai-monitor` 展示可复核的模型、API价格与订阅套餐。

## 工作流程

1. 优先以本skill文件所在目录向上四级定位项目根目录，核对`app/`与`data/ai_monitor.json`。以当前项目目录为唯一维护入口，不写同级`FinBoard新版`或迁移归档。若调用者明确指定其他项目，先核对对应skill和项目规则。
2. 完整阅读 `references/data-schema.md`，再读取现有 JSON；保留未被本次更新影响的条目。
3. 浏览每家厂商的官方定价、模型文档、帮助中心或正式公告。不要用聚合站、媒体转述或搜索摘要代替最终来源。
4. 分开更新两类价格：
   - **API价格**：逐项核对 `models` 的每100万Token输入、缓存输入、输出价格、上下文与分层区间；收录每家厂商当前仍在售的主流产品线（旗舰、均衡/通用、轻量/高速、代码或推理专用），不要重复收录同一模型的日期快照和等价别名；将同厂商条目连续排列并把常用默认模型放在第一项，供页面下拉切换；调价公告尚未生效时保留当前价并标记生效日期。
   - **套餐价格**：逐家收集官网公开的全部档位，包括免费、个人、团队、企业、地区定价、按量计费和自托管。不要只保留代表性套餐；同一厂商的常用套餐放在第一项，供页面默认显示。
5. 套餐月费使用标准月付价。年付折算、促销原价、人数限制和额度写入 `note`；官网未公开固定价格时令 `price` 为 `null`，并用 `billing` 写明 `地区定价`、`联系销售`、`按量计费` 或 `自托管`。
6. 保留官方原币种。不要把CNY换算为USD；同币种内才能直接比较价格。
7. Meta Llama等开放权重模型没有统一官方API单价时，将价格设为 `null`，状态写为 `自托管`，不要杜撰云厂商价格。
8. 写入前在已定位的项目根目录运行`.venv/Scripts/python.exe scripts/local_actions.py backup`并确认成功。将 `last_checked` 更新为实际核对日期，更新简短的 `updates`。页面文字应简洁，标题优先，说明控制在一句内。
9. 运行校验：

   ```powershell
   python .agents/skills/update-ai-monitor/scripts/validate_ai_monitor.py
   ```

10. 在项目根目录运行`.venv/Scripts/python.exe scripts/run_checks.py`，只在临时数据副本上测试；按 `.agents/AGENTS.md` 更新 `CHANGELOG.md`。

## 完成标准

- 每条模型和套餐都有可直接打开的官方HTTPS来源，每家厂商的全部公开套餐档位均已覆盖。
- 数值、币种、计费单位、上下文与促销状态相互一致。
- JSON校验、应用导入和 `/ai-monitor` 冒烟测试通过。
- 汇报核对日期、变更厂商、验证结果和仍需后续复核的调价事项。
