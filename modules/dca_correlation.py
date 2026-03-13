# ================================================================
# modules/dca_correlation.py
# Module 2: 相关性矩阵 + DCA 定投模拟
# ================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import json
import os
from datetime import datetime
from .labels import L


# ── 相关性矩阵 ────────────────────────────────────────────────

def plot_correlation_matrix(prices: pd.DataFrame, tickers: dict,
                             output_dir: str, style: str = "dark") -> str:
    _set_style(style)
    corr = prices.pct_change().dropna().corr()
    labels = [tickers.get(t, t) for t in corr.columns]

    fig, ax = plt.subplots(figsize=(8, 6))
    n = len(corr)
    cmap = plt.cm.RdYlGn

    im = ax.imshow(corr.values, cmap=cmap, vmin=0.5, vmax=1.0, aspect="auto")
    fig.colorbar(im, ax=ax, label="相关系数")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)

    for i in range(n):
        for j in range(n):
            val = corr.values[i, j]
            color = "black" if val > 0.75 else "white"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=color)

    ax.set_title(f"{L('correlation_matrix')}\n（{L('correlation_subtitle')}）", fontsize=13, pad=12)
    fig.tight_layout()

    path = os.path.join(output_dir, "etf_correlation_matrix.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  📊 相关性矩阵 → {path}")
    return path


def get_correlation_insights(prices: pd.DataFrame) -> list:
    """返回高相关性警告列表"""
    corr = prices.pct_change().dropna().corr()
    warnings = []
    tickers = list(corr.columns)
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            val = corr.iloc[i, j]
            if val >= 0.95:
                warnings.append({"pair": (tickers[i], tickers[j]), "corr": round(val, 3),
                                  "level": L("corr_warning_high"), "note": "几乎无分散化效果，考虑替换其中一只"})
            elif val >= 0.90:
                warnings.append({"pair": (tickers[i], tickers[j]), "corr": round(val, 3),
                                  "level": L("corr_warning_mid"), "note": "分散化效果有限"})
    return warnings


# ── DCA 定投模拟 ──────────────────────────────────────────────

def run_dca_simulation(prices: pd.DataFrame, dca_config: dict) -> dict:
    """
    模拟定投结果

    Parameters
    ----------
    prices     : DataFrame  历史收盘价
    dca_config : dict       来自 config.yaml 的 dca 块

    Returns
    -------
    dict: {ticker: {invested, current_value, return_pct, n_periods, units}}
    """
    start   = dca_config["start_date"]
    freq    = dca_config.get("frequency", "monthly")
    amounts = dca_config["amounts_cad"]

    # 映射频率到 pandas resample 规则
    freq_map = {"weekly": "W", "biweekly": "2W", "monthly": "ME"}
    resample_rule = freq_map.get(freq, "ME")

    # 过滤到定投开始日期之后的价格
    dca_prices = prices[prices.index >= start].copy()
    if dca_prices.empty:
        raise ValueError(f"定投开始日期 {start} 超出价格数据范围。")

    # 取每期第一个交易日作为买入日
    period_first = dca_prices.resample(resample_rule).first().dropna(how="all")

    results = {}
    for ticker in prices.columns:
        if ticker not in amounts:
            continue  # 该ETF未设置定投金额，跳过
        if ticker not in period_first.columns:
            continue

        amount = amounts[ticker]
        p = period_first[ticker].dropna()
        units_list = []
        for date, price in p.items():
            if price > 0:
                units_list.append(amount / price)

        total_invested = amount * len(units_list)
        total_units    = sum(units_list)
        current_price  = prices[ticker].iloc[-1]
        current_value  = total_units * current_price
        ret_pct        = (current_value - total_invested) / total_invested * 100

        results[ticker] = {
            "invested":      round(total_invested, 2),
            "current_value": round(current_value, 2),
            "return_pct":    round(ret_pct, 1),
            "n_periods":     len(units_list),
            "total_units":   round(total_units, 4),
            "amount_per_period": amount,
        }

    return results


def plot_dca_results(dca_results: dict, tickers: dict,
                     output_dir: str, style: str = "dark") -> str:
    _set_style(style)

    labels     = [tickers.get(t, t) for t in dca_results]
    invested   = [v["invested"]      for v in dca_results.values()]
    curr_vals  = [v["current_value"] for v in dca_results.values()]
    returns    = [v["return_pct"]    for v in dca_results.values()]

    x = np.arange(len(labels))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 左：投入 vs 当前市值
    colors_inv = ["#5b3f8a"] * len(labels)
    colors_cur = ["#9b72cf" if r >= 0 else "#e05d5d" for r in returns]
    bars1 = ax1.bar(x - width/2, invested,  width, label=L("total_invested"), color=colors_inv, alpha=0.85)
    bars2 = ax1.bar(x + width/2, curr_vals, width, label=L("current_value"), color=colors_cur, alpha=0.85)

    for bar in bars2:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h + 80, f"${h:,.0f}",
                 ha="center", va="bottom", fontsize=8)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    ax1.set_ylabel(L("amount_cad"))
    ax1.set_title(L("dca_vs_value"), fontsize=12)
    ax1.legend()
    ax1.grid(alpha=0.2, axis="y")

    # 右：收益率
    bar_colors = ["#5bc4a5" if r >= 0 else "#e05d5d" for r in returns]
    ax2.bar(x, returns, color=bar_colors, alpha=0.85)
    for i, r in enumerate(returns):
        ax2.text(i, r + (0.5 if r >= 0 else -1.5), f"{r:.1f}%",
                 ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax2.axhline(0, color="gray", linewidth=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=15, ha="right", fontsize=9)
    ax2.set_ylabel(L("return_pct"))
    ax2.set_title(L("dca_return_compare"), fontsize=12)
    ax2.grid(alpha=0.2, axis="y")

    fig.tight_layout()
    path = os.path.join(output_dir, "etf_dca_simulation.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  📊 DCA模拟图 → {path}")
    return path


def save_dca_csv(dca_results: dict, output_dir: str) -> str:
    rows = []
    for ticker, d in dca_results.items():
        rows.append({
            L("ticker"):      ticker,
            L("periods"):     d["n_periods"],
            L("amount_per_period"): d["amount_per_period"],
            L("total_invested_csv"): d["invested"],
            L("current_value_csv"): d["current_value"],
            L("profit"):      round(d["current_value"] - d["invested"], 2),
            L("return_pct_csv"): d["return_pct"],
        })
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {
        L("ticker"): L("total"),
        L("periods"): "",
        L("amount_per_period"): "",
        L("total_invested_csv"): df[L("total_invested_csv")].sum(),
        L("current_value_csv"): df[L("current_value_csv")].sum(),
        L("profit"):      df[L("profit")].sum(),
        L("return_pct_csv"): round((df[L("current_value_csv")].sum() / df[L("total_invested_csv")].sum() - 1) * 100, 1),
    }
    path = os.path.join(output_dir, "etf_dca_summary.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  📄 DCA汇总CSV → {path}")
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
        })
    else:
        plt.style.use("seaborn-v0_8-whitegrid")


# ── 模块主入口 ────────────────────────────────────────────────

def run(config: dict, prices: pd.DataFrame) -> dict:
    """
    Parameters
    ----------
    config : dict        已解析的 config.yaml
    prices : DataFrame   Module 1 返回的价格数据

    Returns
    -------
    dict  {"correlation_warnings": [...], "dca_results": dict, "files": [...]}
    """
    tickers    = config["portfolio"]["tickers"]
    dca_config = config["dca"]
    output_dir = config["output"]["directory"]
    style      = config["output"].get("chart_style", "dark")

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 50)
    print("  Module 2: 相关性分析 + DCA 定投模拟")
    print("=" * 50)

    # 相关性
    corr_warnings = get_correlation_insights(prices)
    if corr_warnings:
        print("\n⚠️  相关性警告：")
        for w in corr_warnings:
            t1, t2 = w["pair"]
            print(f"  {t1} vs {t2}: {w['corr']} ({w['level']}) — {w['note']}")
    else:
        print("  ✅ 无高相关性警告")

    # DCA 模拟
    dca_results = run_dca_simulation(prices, dca_config)
    total_inv  = sum(v["invested"]      for v in dca_results.values())
    total_val  = sum(v["current_value"] for v in dca_results.values())
    total_ret  = (total_val - total_inv) / total_inv * 100

    print(f"\n💰 DCA 汇总（{dca_config.get('frequency','monthly')}定投）：")
    print(f"  {'Ticker':<12} {'期数':>6} {'总投入':>10} {'当前市值':>12} {'收益率':>8}")
    print("  " + "-" * 55)
    for t, d in dca_results.items():
        print(f"  {t:<12} {d['n_periods']:>6} ${d['invested']:>9,.0f} ${d['current_value']:>11,.0f} "
              f"{d['return_pct']:>7.1f}%")
    print("  " + "-" * 55)
    print(f"  {'合计':<12} {'':>6} ${total_inv:>9,.0f} ${total_val:>11,.0f} {total_ret:>7.1f}%")

    files = []
    files.append(plot_correlation_matrix(prices, tickers, output_dir, style))
    files.append(plot_dca_results(dca_results, tickers, output_dir, style))
    files.append(save_dca_csv(dca_results, output_dir))

    # JSON
    if config["output"].get("generate_json", True):
        json_path = os.path.join(output_dir, "dca_results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at":       datetime.now().isoformat(),
                "dca_config":         dca_config,
                "dca_results":        dca_results,
                "correlation_warnings": [
                    {"pair": list(w["pair"]), "corr": w["corr"],
                     "level": w["level"], "note": w["note"]}
                    for w in corr_warnings
                ],
                "summary": {
                    "total_invested":    round(total_inv, 2),
                    "total_value":       round(total_val, 2),
                    "total_return_pct":  round(total_ret, 1),
                }
            }, f, ensure_ascii=False, indent=2)
        files.append(json_path)
        print(f"  📄 JSON → {json_path}")

    print(f"\n✅ Module 2 完成，共生成 {len(files)} 个文件\n")
    return {"correlation_warnings": corr_warnings, "dca_results": dca_results, "files": files}
