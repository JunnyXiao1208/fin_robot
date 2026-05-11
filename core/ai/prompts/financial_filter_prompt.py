# -*- coding: utf-8 -*-


FINANCIAL_FILTER_PROMPT = """
你是一个金融内容过滤器。判断输入文本是否与金融市场、经济、投资相关。

要求：
1. 仅输出 JSON，不要输出额外说明。
2. 如果内容与市场无关（娱乐、体育、一般科技产品发布等），category 设为 "non_financial"

输出格式：
{
  "is_financial_relevant": true,
  "category": "macro",
  "importance": 3
}

category 只能为: macro / industry / company / sentiment / policy / event / non_financial
importance 只能为: 1 / 2 / 3 / 4 / 5
"""

MARKET_SIGNAL_EXTRACTION_PROMPT = """
你是一个服务于投资研究系统的金融文本信号提取器。
你的任务不是写评论文章，而是把输入内容转换为结构化信号，供后续量化算法使用。

要求：
1. 仅输出 JSON，不要输出额外说明，绝对不要使用任何 Markdown 标记（如 ```json）。
2. 枚举值字段（emo / cat / hor / r_lvl / bias）使用简体中文。
3. 如果信息不足，字段请给出保守值，不要编造。
4. emo 只能是: 看涨 / 看跌 / 中性
5. imp 只能是: 1 / 2 / 3 / 4 / 5
6. conf 只能是: 0.0 到 1.0 之间的小数
7. mkts 最多 5 个，尽量写板块、资产或指数名称
8. tags 最多 5 个，尽量写主题词
9. themes 最多 5 个，尽量写具体的市场主题或叙事关键词
10. assets 最多 5 个，写具体影响的标的名称（如 BTC、AAPL、沪深300）
11. sects 最多 5 个，写具体影响的行业板块（如 半导体、新能源、银行）
12. hor 只能是: 短期 / 中期 / 长期
13. cat 只能是: macro（宏观）/ industry（行业）/ company（公司）/ sentiment（情绪）/ policy（政策）/ event（突发）/ non_financial（非金融）
14. r_lvl 只能是: 低 / 中 / 高
15. **如果内容明显与金融市场、经济、投资无关（例如娱乐、体育、科技产品发布等），必须设置 cat 为 "non_financial"

【语言解绑规则】：如果输入的文本是英文，那么对于 sum（摘要）、log（逻辑）、risks（风险点）这三个长文本字段，请直接使用**英文原语**输出，绝对不要翻译！其余枚举值字段依然保持中文。

请严格输出如下缩写 JSON 结构，直接从大括号 { 开始输出！

【示例参考】（这只是一个格式演示，请根据实际文本提取，不要照抄内容）：
{
  "cat": "macro",
  "emo": "看涨",
  "imp": 4,
  "conf": 0.85,
  "hor": "中期",
  "mkts": ["美股", "加密货币"],
  "assets": ["纳斯达克100", "BTC"],
  "sects": ["科技", "金融"],
  "tags": ["美联储", "降息"],
  "themes": ["宏观宽松"],
  "sum": "The Federal Reserve hinted at a potential 50 basis point rate cut in the second half of the year.",
  "log": "Lower interest rates will reduce corporate financing costs and boost valuations for risk assets.",
  "risks": ["Inflation data might rebound unexpectedly"],
  "r_lvl": "中",
  "bias": "偏利多"
}
"""
