# AI监控数据格式

目标文件：`data/ai_monitor.json`

## 根字段

- `last_checked`：实际完成官方核对的日期，格式 `YYYY-MM-DD`。
- `unit`：API价格的统一数量口径，当前为 `每100万Token`。
- `models`：API模型价格数组。
- `plans`：按厂商连续排列的全部公开套餐档位数组。
- `updates`：页面显示的精简动态数组。

## models

必填字段：`provider`、`provider_code`、`model`、`positioning`、`currency`、`currency_symbol`、`input_price`、`cached_input_price`、`output_price`、`context`、`status`、`status_tone`、`pricing_note`、`source_label`、`source_url`。

- 价格均为每100万Token，值为非负数字或 `null`。
- 美元使用 `USD` / `$`，人民币使用 `CNY` / `¥`。
- 无官方统一API价时，三个价格字段可为 `null`，`currency` 也为 `null`。
- `status_tone` 使用 `stable`、`promo`、`warning`、`new`、`opensource`。
- 分层定价选择页面所述的常用标准档，并在 `pricing_note` 写明适用区间。
- 同一厂商的条目必须连续排列，第一项是页面默认展示的常用模型；存在多个条目时，页面在该厂商行提供模型下拉切换。

## plans

必填字段：`provider`、`provider_code`、`plan`、`price`、`currency_symbol`、`billing`、`note`、`source_url`。

- 收录官网公开的全部套餐类型，包括免费、个人、团队、企业、地区定价、按量计费和自托管。
- 记录标准月付价；免费套餐的 `price` 为 `0`、`billing` 为 `免费`。
- 官网没有固定公开价格时，`price` 为 `null`，`billing` 写明 `地区定价`、`联系销售`、`按量计费` 或 `自托管`。
- 限时优惠必须在 `note` 标明原价；年付折算价只写入 `note`，不要覆盖标准月付价。
- 同一厂商的条目必须连续排列，第一项是页面默认展示的常用套餐。
- 订阅套餐不等于API额度，二者分开记录。

## updates

必填字段：`date`、`provider`、`tag`、`title`。只保留对价格或模型选择有用的信息，标题尽量不超过30个汉字。
