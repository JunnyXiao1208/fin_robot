# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from core.ai.pipeline import extract_market_signal


async def main():
    test_text = """
    Federal Reserve officials indicated they are in no rush to cut interest rates, stressing that inflation remains stubbornly above their 2% target.
    Speaking at a conference in Washington, Fed Chair Jerome Powell noted that the recent string of strong economic data and robust labor market reports
    give the central bank breathing room to assess the impact of previous rate hikes. The S&P 500 tumbled 1.5% following his remarks, while the yield
    on the 10-year Treasury note spiked to 4.65%. Investors are rapidly recalibrating their expectations, scaling back bets on a summer rate cut.
    Technology stocks bore the brunt of the selloff, with major tech giants losing over $200 billion in market capitalization combined.
    """

    print("开始向大模型发送【英文长文本】测试请求 (启用 JSON 瘦身与语言解绑)...")
    start_time = time.time()

    try:
        result = await extract_market_signal(
            text=test_text,
            source_type="news",
            author="Wall Street Journal"
        )
        elapsed = time.time() - start_time

        print(f"\n测试完成！耗时: {elapsed:.2f} 秒")
        print("以下是经过【还原映射】后的最终 JSON 结果：\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"\n测试失败，抛出异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
