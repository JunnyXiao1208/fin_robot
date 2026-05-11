import re
from typing import Dict


def pearson_correlation(vec1: list[float], vec2: list[float]) -> float:
    if len(vec1) != len(vec2) or len(vec1) == 0:
        return 0.0

    n = len(vec1)
    sum1 = sum(vec1)
    sum2 = sum(vec2)
    sum1_sq = sum(v * v for v in vec1)
    sum2_sq = sum(v * v for v in vec2)
    p_sum = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))

    numerator = n * p_sum - sum1 * sum2
    denom1 = n * sum1_sq - sum1 * sum1
    denom2 = n * sum2_sq - sum2 * sum2

    if denom1 <= 0 or denom2 <= 0:
        return 0.0

    denominator = (denom1 ** 0.5) * (denom2 ** 0.5)
    if denominator == 0:
        return 0.0

    r = numerator / denominator
    return max(-1.0, min(1.0, r))


def _get_char_bigrams(text: str) -> Dict[str, int]:
    cleaned = re.sub(r"\s+", "", text)
    bigrams = {}
    for i in range(len(cleaned) - 1):
        bg = cleaned[i:i + 2]
        bigrams[bg] = bigrams.get(bg, 0) + 1
    return bigrams


def calculate_text_pearson_similarity(text1: str, text2: str) -> float:
    bg1 = _get_char_bigrams(text1)
    bg2 = _get_char_bigrams(text2)

    if bg1 == bg2:
        return 1.0

    all_bigrams = set(bg1.keys()) | set(bg2.keys())
    if not all_bigrams:
        return 0.0

    vec1 = [float(bg1.get(bg, 0)) for bg in all_bigrams]
    vec2 = [float(bg2.get(bg, 0)) for bg in all_bigrams]

    return pearson_correlation(vec1, vec2)
