# ================================================================
# modules/fetch_metrics.py
# Module 1: 数据拉取 + 基础指标计算
# ================================================================
# 接收配置参数，返回：
#   - prices DataFrame（每日收盘价）
#   - metrics dict（各ETF核心指标）
#   - cumulative returns chart（PNG）
#   - metrics CSV
# ================================================================

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import os
import shutil
import json
from datetime import datetime
from .labels import L


def clear_cache():
    """清除 yfinance 本地缓存，避免 database locked 错误"""
    path = os.path.join(os.path.expanduser("~"), ".cache", "py-yfinance")
    if os.path.exists(path):
        shutil.rmtree(path)
        print("🧹 已清除 yfinance 缓存")


def fetch_prices(tickers: dict, start: str, end: str) -> pd.DataFrame:
    """
    下载价格数据（逐个下载，避免批量失败）

    Parameters
    ----------
    tickers : dict  {ticker: display_name}
    start   : str   "YYYY-MM-DD"
    end     : str   "YYYY-MM-DD" 或 "today"

    Returns
    -------
    pd.DataFrame  列=ticker，索引=日期，值=收盘价
    """
    if end.lower() == "today":
        end = datetime.today().strftime("%Y-%m-%d")

    print("📥 正在下载价格数据...\n")
    all_prices = {}

    for ticker, name in tickers.items():
        try:
            data = yf.download(
                tickers=ticker,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False
            )
            if data.empty:
                print(f"  ⚠️  {ticker} 数据为空，跳过")
                continue

            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()

            all_prices[ticker] = close
            print(f"  ✅ {ticker} ({name})：{len(data)} 个交易日")

        except Exception as e:
            print(f"  ❌ {ticker} 下载失败：{e}")
            continue

    if len(all_prices) < 1:
        raise ValueError("没有ETF数据下载成功，请检查网络连接和ticker代码。")

    prices = pd.DataFrame(all_prices).dropna()
    print(f"\n✅ 数据准备完成！{len(prices)} 个交易日")
    print(f"   时间范围：{prices.index[0].date()} → {prices.index[-1].date()}")
    print(f"   已加载：{list(prices.columns)}\n")
    return prices


def calculate_metrics(prices: pd.DataFrame, risk_free_rate: float = 0.04) -> dict:
    """
    计算各ETF核心指标

    Returns dict: {ticker: {total_return, annual_return, volatility, max_drawdown, sharpe}}
    """
    daily_returns = prices.pct_change().dropna()
    n_years = len(daily_returns) / 252
    results = {}

    for col in prices.columns:
        r = daily_returns[col]
        p = prices[col]

        total_ret = (p.iloc[-1] / p.iloc[0]) - 1
        annual_ret = (1 + total_ret) ** (1 / n_years) - 1
        vol = r.std() * np.sqrt(252)

        # 最大回撤
        roll_max = p.cummax()
        drawdown = (p - roll_max) / roll_max
        max_dd = drawdown.min()

        # Sharpe（日化）
        excess = r - (risk_free_rate / 252)
        sharpe = (excess.mean() / r.std()) * np.sqrt(252)

        results[col] = {
            "total_return":  round(total_ret * 100, 1),
            "annual_return": round(annual_ret * 100, 1),
            "volatility":    round(vol * 100, 1),
            "max_drawdown":  round(max_dd * 100, 1),
            "sharpe":        round(sharpe, 2),
        }

    return results


def plot_cumulative_returns(prices: pd.DataFrame, tickers: dict,
                            output_dir: str, style: str = "dark") -> str:
    """累计收益率图"""
    _set_style(style)
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#9b72cf", "#5bc4a5", "#f2a623", "#e05d5d", "#5ba4cf", "#a0d468"]
    for i, col in enumerate(prices.columns):
        name = tickers.get(col, col)
        cum_ret = (prices[col] / prices[col].iloc[0] - 1) * 100
        ax.plot(cum_ret.index, cum_ret, label=f"{col} — {name}",
                color=colors[i % len(colors)], linewidth=2)

    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title(L("cumulative_return"), fontsize=14, pad=12)
    ax.set_xlabel("")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.2)
    fig.tight_layout()

    path = os.path.join(output_dir, "etf_cumulative_returns.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  📊 累计收益率图 → {path}")
    return path


def save_metrics_csv(metrics: dict, output_dir: str) -> str:
    """保存指标到CSV"""
    rows = []
    for ticker, m in metrics.items():
        rows.append({
            L("ticker"):        ticker,
            L("total_return"):   m["total_return"],
            L("annual_return"): m["annual_return"],
            L("volatility"):    m["volatility"],
            L("max_drawdown"):  m["max_drawdown"],
            L("sharpe"):        m["sharpe"],
        })
    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "etf_metrics.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  📄 指标CSV → {path}")
    return path


def _set_style(style: str):
    if style == "dark":
        plt.style.use("dark_background")
        plt.rcParams.update({
            "axes.facecolor":   "#1a1a2e",
            "figure.facecolor": "#0d0d1a",
            "text.color":       "#e0e0e0",
            "axes.labelcolor":  "#e0e0e0",
            "xtick.color":      "#aaaaaa",
            "ytick.color":      "#aaaaaa",
            "grid.color":       "#333355",
        })
    else:
        plt.style.use("seaborn-v0_8-whitegrid")


# ── 模块主入口（由 run_analysis.py 调用）──────────────────────
def run(config: dict) -> dict:
    """
    Parameters
    ----------
    config : dict  已解析的 config.yaml 内容

    Returns
    -------
    dict  {"prices": DataFrame, "metrics": dict, "files": [str, ...]}
    """
    clear_cache()

    tickers     = config["portfolio"]["tickers"]
    start       = config["dates"]["start"]
    end         = config["dates"]["end"]
    rfr         = config["dates"].get("risk_free_rate", 0.04)
    output_dir  = config["output"]["directory"]
    style       = config["output"].get("chart_style", "dark")

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 50)
    print("  Module 1: 数据拉取 + 基础指标")
    print("=" * 50)

    prices  = fetch_prices(tickers, start, end)
    metrics = calculate_metrics(prices, rfr)

    # 打印指标摘要
    print("\n📊 核心指标摘要：")
    print(f"  {'Ticker':<12} {'总收益':>8} {'年化':>8} {'波动率':>8} {'最大回撤':>10} {'Sharpe':>8}")
    print("  " + "-" * 60)
    for t, m in metrics.items():
        print(f"  {t:<12} {m['total_return']:>7.1f}% {m['annual_return']:>7.1f}% "
              f"{m['volatility']:>7.1f}% {m['max_drawdown']:>9.1f}% {m['sharpe']:>8.2f}")

    files = []
    files.append(plot_cumulative_returns(prices, tickers, output_dir, style))
    files.append(save_metrics_csv(metrics, output_dir))

    # 输出 JSON（供 dashboard 使用）
    if config["output"].get("generate_json", True):
        json_path = os.path.join(output_dir, "metrics.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "date_range":   {"start": start, "end": end},
                "tickers":      tickers,
                "metrics":      metrics,
            }, f, ensure_ascii=False, indent=2)
        files.append(json_path)
        print(f"  📄 JSON → {json_path}")

    print(f"\n✅ Module 1 完成，共生成 {len(files)} 个文件\n")
    return {"prices": prices, "metrics": metrics, "files": files}
