# -*- coding: utf-8 -*-
"""
量化引擎 v2 — 多维信号综合评分系统

指标维度：
  - 趋势: MA20 / MA60 位置关系
  - 动量: RSI(14), MACD(12,26,9)
  - 波动: 布林带宽度 (Bollinger Band Width)
  - 量能: 成交量比率 (Volume Ratio vs 20日均量)

评分规则：
  每项指标 -2 ~ +2 分，加权求和得复合分
  最终操作根据复合分 + 置信度裁定
"""

import os
import logging
import time
from collections import OrderedDict

# ── 关键：在 import akshare 之前清除代理 ──
# requests 在导入时读取 proxy 配置，必须提前清掉
_SAVED_ENV = {}
for _k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    _v = os.environ.pop(_k, None)
    if _v is not None:
        _SAVED_ENV[_k] = _v

import akshare as ak
import pandas as pd
import numpy as np
import json

# 恢复代理（给其他模块用）
for _k, _v in _SAVED_ENV.items():
    os.environ[_k] = _v

# ── 所有此模块内的请求都走无代理 session ──
import requests as _req
_NO_PROXY_SESSION = _req.Session()
_NO_PROXY_SESSION.trust_env = False
_NO_PROXY_SESSION.proxies = {"http": "", "https": ""}

# 修补 akshare 的 cons 模块
try:
    import akshare.bond.cons as _ak_cons
    _ak_cons.session = _NO_PROXY_SESSION
    _ak_cons.get_requests_session = lambda: _NO_PROXY_SESSION
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 定投标的 ──
MY_TARGETS = OrderedDict([
    ("588290", "芯片ETF"),
    ("515030", "新能源ETF"),
    ("512010", "医药ETF"),
    ("512890", "红利低波ETF"),
    ("518880", "黄金ETF"),
    ("159928", "消费ETF"),
])

# ── 指标权重 ──
WEIGHTS = {
    "ma_bias":    0.25,
    "rsi":        0.20,
    "macd":       0.20,
    "volume":     0.15,
    "bollinger":  0.10,
    "trend":      0.10,
}

# ── 缓存 ──
_cache = {"etf_spot": None, "spot_ts": 0, "hist": {}, "hist_ts": 0}
CACHE_TTL = 300


# ── 代理绕过辅助函数 ──
def _bypass_proxy():
    """临时清除系统代理，返回(旧值字典)用于恢复"""
    saved = {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        v = os.environ.pop(k, None)
        if v is not None:
            saved[k] = v
    return saved


def _restore_proxy(saved):
    for k, v in saved.items():
        os.environ[k] = v


# ════════════════════════════════════════════
#  helper: 获取数据
# ════════════════════════════════════════════

def _get_etf_spot():
    now = time.time()
    if _cache["etf_spot"] is not None and (now - _cache["spot_ts"]) < CACHE_TTL:
        return _cache["etf_spot"]
    saved = _bypass_proxy()
    try:
        df = ak.fund_etf_spot_em()
    finally:
        _restore_proxy(saved)
    _cache["etf_spot"] = df
    _cache["spot_ts"] = now
    return df


def _get_hist(code, retries=2):
    """获取历史日线数据（子进程+无代理）"""
    import subprocess
    
    now = time.time()
    if code in _cache["hist"] and (now - _cache["hist_ts"]) < CACHE_TTL:
        return _cache["hist"][code]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "fetch_hist.py")
    
    for i in range(retries):
        try:
            result = subprocess.run(
                ["python", script_path, code],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                df = pd.DataFrame(data)
                _cache["hist"][code] = df
                _cache["hist_ts"] = now
                return df
            else:
                logger.warning(f"[{code}] 子进程无数据: {result.stderr[:100]}")
        except Exception as e:
            logger.warning(f"[{code}] 子进程获取失败(第{i+1}次): {e}")
            time.sleep(2 ** i)
    return None


# ════════════════════════════════════════════
#  单指标评分函数（每个返回 -2 ~ +2）
# ════════════════════════════════════════════

def _score_ma_bias(current, closes, period=20):
    """MA 偏离度评分"""
    ma = np.mean(closes)
    bias_pct = (current - ma) / ma * 100
    if bias_pct < -3.0:
        return 2.0, f"MA{period} 偏离 {bias_pct:+.1f}% (深度超卖)"
    elif bias_pct < -1.0:
        return 1.0, f"MA{period} 偏离 {bias_pct:+.1f}% (超卖区)"
    elif bias_pct < 1.0:
        return 0.0, f"MA{period} 偏离 {bias_pct:+.1f}% (均线附近)"
    elif bias_pct < 3.0:
        return -1.0, f"MA{period} 偏离 {bias_pct:+.1f}% (偏高区)"
    else:
        return -2.0, f"MA{period} 偏离 {bias_pct:+.1f}% (深度超买)"


def _score_rsi(closes, period=14):
    """RSI 动量评分"""
    if len(closes) < period + 1:
        return 0, "RSI 数据不足"
    deltas = np.diff(closes[-period-1:])
    gains = deltas[deltas > 0].sum()
    losses = -deltas[deltas < 0].sum()
    if losses == 0:
        return 2.0, "RSI(14)=100 连续上涨"
    rs = gains / losses
    rsi = 100 - 100 / (1 + rs)
    if rsi < 25:
        return 2.0, f"RSI(14)={rsi:.0f} (深度超卖)"
    elif rsi < 40:
        return 1.0, f"RSI(14)={rsi:.0f} (超卖区)"
    elif rsi < 60:
        return 0.0, f"RSI(14)={rsi:.0f} (中性区)"
    elif rsi < 75:
        return -1.0, f"RSI(14)={rsi:.0f} (超买区)"
    else:
        return -2.0, f"RSI(14)={rsi:.0f} (深度超买)"


def _score_macd(closes):
    """MACD 趋势强度评分"""
    if len(closes) < 26:
        return 0, "MACD 数据不足"
    arr = np.array(closes, dtype=float)
    def ema(data, span):
        alpha = 2 / (span + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        return result
    ema12 = ema(arr, 12)
    ema26 = ema(arr, 26)
    dif = ema12 - ema26
    dea = ema(dif, 9)
    hist_val = dif[-1] - dea[-1]
    trend_dir = "多头" if dif[-1] > dea[-1] else "空头"
    score = 1.5 if (dif[-1] > dea[-1] and hist_val > 0) else -1.5 if (dif[-1] < dea[-1] and hist_val < 0) else 0.0
    return score, f"MACD({trend_dir}) DIF/DEA={dif[-1]:.4f}/{dea[-1]:.4f}"


def _score_volume(closes, volumes, period=20):
    """量能配合评分"""
    if len(volumes) < period:
        return 0, "量能数据不足"
    avg_vol = np.mean(volumes[-period:])
    cur_vol = volumes[-1]
    vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0
    close_trend = closes[-1] > closes[-2]
    if vol_ratio > 1.5 and close_trend:
        return 1.5, f"量比 {vol_ratio:.1f}x (放量上涨 ✅)"
    elif vol_ratio > 1.5 and not close_trend:
        return -1.5, f"量比 {vol_ratio:.1f}x (放量下跌 ❌)"
    elif vol_ratio > 1.0 and close_trend:
        return 0.5, f"量比 {vol_ratio:.1f}x (温和放量)"
    elif vol_ratio > 1.0 and not close_trend:
        return -0.5, f"量比 {vol_ratio:.1f}x (温和缩量)"
    else:
        return 0, f"量比 {vol_ratio:.1f}x (正常量能)"


def _score_bollinger(closes):
    """布林带位置评分"""
    if len(closes) < 20:
        return 0, "布林带数据不足"
    ma = np.mean(closes[-20:])
    std = np.std(closes[-20:])
    upper = ma + 2 * std
    lower = ma - 2 * std
    current = closes[-1]
    bw = (upper - lower) / ma * 100
    if current <= lower:
        return 2.0, f"布林下轨下方 (带宽{bw:.1f}%)"
    elif current <= ma - std:
        return 1.0, f"布林下轨区域"
    elif current <= ma + std:
        return 0.0, f"布林中轨区域"
    elif current <= upper:
        return -1.0, f"布林上轨区域"
    else:
        return -2.0, f"布林上轨上方 (带宽{bw:.1f}%)"


def _score_trend_ma(closes):
    """多空趋势评分"""
    if len(closes) < 60:
        return 0, "趋势数据不足"
    ma5 = np.mean(closes[-5:])
    ma20 = np.mean(closes[-20:])
    ma60 = np.mean(closes[-60:])
    if ma5 > ma20 > ma60:
        return 1.5, "多头排列 (MA5>MA20>MA60)"
    elif ma5 < ma20 < ma60:
        return -1.5, "空头排列 (MA5<MA20<MA60)"
    elif ma5 > ma20:
        return 1.0, "短多长平"
    elif ma5 < ma20:
        return -1.0, "短空长平"
    else:
        return 0.0, "均线缠绕"


# ════════════════════════════════════════════
#  综合评分与信号生成
# ════════════════════════════════════════════

def _composite_signal(closes, volumes):
    """综合所有指标给出最终信号"""
    current = closes[-1]
    scores = OrderedDict()
    details = OrderedDict()
    for fn, k in [
        (_score_ma_bias, "ma_bias"),
        (_score_rsi, "rsi"),
        (_score_macd, "macd"),
        (_score_volume, "volume"),
        (_score_bollinger, "bollinger"),
        (_score_trend_ma, "trend"),
    ]:
        if k in ("ma_bias",):
            s, d = fn(current, closes, 20)
        elif k == "volume":
            s, d = fn(closes, volumes, 20)
        else:
            s, d = fn(closes)
        scores[k] = s
        details[k] = d

    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    max_possible = sum(2.0 * WEIGHTS[k] for k in WEIGHTS)
    confidence_pct = abs(total) / max_possible * 100

    if total >= 1.2:
        label, pos = "🔥 强烈买入", "加仓 2 份"
    elif total >= 0.5:
        label, pos = "📈 偏向买入", "加仓 1 份"
    elif total <= -1.2:
        label, pos = "⚠️ 强烈卖出", "减仓 30%"
    elif total <= -0.5:
        label, pos = "🔻 偏向卖出", "减仓 10%"
    else:
        label, pos = "⚪️ 中性观望", "持有不动"

    confidence = "高" if confidence_pct >= 60 else ("中" if confidence_pct >= 35 else "低")

    return {
        "score": round(total, 2),
        "label": label,
        "position": pos,
        "confidence": confidence,
        "confidence_pct": round(confidence_pct, 1),
        "details": details,
    }


# ════════════════════════════════════════════
#  对外接口
# ════════════════════════════════════════════

async def calculate_trading_signals():
    """计算多维度量化信号"""
    try:
        spot_df = _get_etf_spot()
        if spot_df is None:
            return "❌ 无法获取行情数据"

        lines = ["📊 **多维量化雷达**\n"]
        lines.append("*(评分: +2~-2, 综合分 > +0.5 买入, <-0.5 卖出)*\n")

        for code, name in MY_TARGETS.items():
            try:
                spot = spot_df[spot_df["代码"] == code]
                if spot.empty:
                    lines.append(f"\n**{name}** — 无实时数据\n" + "─" * 24)
                    continue

                row = spot.iloc[0]
                price = float(row["最新价"])
                change_raw = str(row.get("涨跌幅", "0")).replace("%", "")
                change_pct = float(change_raw) if change_raw.replace(".", "").replace("-", "").isdigit() else 0.0

                hist = _get_hist(code)
                if hist is None or len(hist) < 20:
                    lines.append(f"\n**{name}** — 历史数据不足\n" + "─" * 24)
                    continue

                closes = hist["收盘"].tail(80).tolist()
                closes[-1] = price
                vol_col = "成交量" if "成交量" in hist.columns else "volume"
                volumes = hist[vol_col].tail(80).tolist()

                sig = _composite_signal(closes, volumes)

                lines.append(f"\n**{name}** — 实时 ${price:.3f} ({change_pct:+.2f}%)")
                lines.append(f"综评: {sig['label']} (分: {sig['score']:+.2f}) | 操作: **{sig['position']}**")
                lines.append(f"置信度: {sig['confidence']} ({sig['confidence_pct']:.0f}%)")
                for v in sig["details"].values():
                    lines.append(f"  · {v}")
                lines.append("─" * 24)

            except Exception as e:
                logger.error(f"{name} 异常: {e}")
                lines.append(f"\n**{name}** — 计算异常\n" + "─" * 24)
                continue

        lines.append("\n💡 基于 MA20/MA60·RSI·MACD·量能·布林带·趋势排列 六维度评分")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"量化引擎异常: {e}")
        return f"❌ 量化引擎异常: {str(e)[:200]}"


async def scan_market_strategies():
    """预留"""
    return "📊 全市场扫描功能开发中..."
