# 银行、钱包与支付卡品牌图标

本地图标可跨页面复用；按品牌英文短名命名。机器索引见`sources.json`，包含品牌名称、分类、文件名、访问路径及来源。PayFun和MetaMask为根据用户卡面标志绘制的SVG，其余为官网提供的图标；`card.svg`为未知品牌的通用卡图标。新增品牌应追加索引，避免重复下载。

|品牌|分类|文件|
|---|---|---|
|DeCard|支付卡|decard.ico|
|Ether.fi|加密金融|etherfi.png|
|Plasma One|加密金融|plasma.ico|
|PokePay|支付钱包|pokepay.png|
|UU Wallet|支付钱包|uu.ico|
|Krak|支付钱包|krak.png|
|Blackcatcard|支付卡|blackcat.png|
|Skrill|支付钱包|skrill.ico|
|PayFun|支付卡|payfun.svg|
|dtcpay|支付平台|dtcpay.ico|
|Starryblu|跨境金融|starryblu.png|
|MEXC|交易所|mexc.png|
|bunq|银行|bunq.png|
|Yonder|支付卡|yonder.png|
|Altery|跨境金融|altery.png|
|Zopa|银行|zopa.ico|
|Trading 212|投资平台|trading212.svg|
|SumUp|支付平台|sumup.svg|
|MetaMask|加密钱包|metamask.svg|

PokePay官网PNG为192×192画布，标志位于左上角24×24区域。复用时需裁定该区域；卡片CSS已设置8倍放大并通过外框裁切，避免全画布缩小造成空白。
