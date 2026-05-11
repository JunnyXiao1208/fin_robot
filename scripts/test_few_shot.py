# -*- coding: utf-8 -*-
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from core.ai.pipeline import extract_market_signal


async def main():
    test_text = "最新重磅！A股今日迎来大反弹，核心资产全线爆发，外资疯狂扫货，大金融与白酒板块掀起涨停潮，市场情绪瞬间点燃！"

    print("开始发送【国内A股反弹】测试请求，验证资产标准化...")

    try:
        result = await extract_market_signal(
            text=test_text,
            source_type="news",
            author="Gemini Test"
        )

        print("\n测试完成！以下是最终解析的 JSON 结果：\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        assets = result.get("affected_assets", result.get("assets", []))
        if "沪深300" in assets:
            print("\n完美命中！模型成功将模糊的核心资产映射为标准标的：沪深300")
        else:
            print(f"\n未命中标准标的，模型实际提取的资产为: {assets}")

    except Exception as e:
        print(f"\n测试失败，抛出异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
