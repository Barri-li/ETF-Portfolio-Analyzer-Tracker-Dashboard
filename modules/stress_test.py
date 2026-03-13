# ================================================================
# modules/stress_test.py
# Module 3: 情景压力测试
# ================================================================
# 从 config.yaml 读取自定义情景和冲击参数
# 自动计算各ETF损失金额 + 生成图表
# ================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import json
import os
from datetime import datetime
from .labels import L


def run_stress_test(scenarios: dict, portfolio_values: dict) -> dict:
    """
    对每个情景计算三档（悲观/基准/乐观）损失

    Parameters
    ----------
    scenarios        : dict  config.yaml 的 stress_scenarios 块
    portfolio_values : dict  {ticker: 当前市值(CAD)}

    Returns
    -------
    dict  {scenario_key: {name, description, results: {ticker: {...}}, totals: {...}}}
    """
    output = {}

    for key, sc in scenarios.items():
        name        = sc["name"]
        description = sc["description"]
        shocks      = sc["shocks"]  # {ticker: [pessimistic, base, optimistic]}

        scenario_results = {}
        totals = {"pessimistic": 0, "base": 0, "optimistic": 0}

        for ticker, value in portfolio_values.items():
            if ticker not in shocks:
                continue
            s = shocks[ticker]
            pess  = value * s[0] / 100
            base  = value * s[1] / 100
            opti  = value * s[2] / 100
            scenario_results[ticker] = {
                "current_value": value,
                "shock_pess_pct": s[0],
                "shock_base_pct": s[1],
                "shock_opti_pct": s[2],
                "loss_pess":  round(pess, 0),
                "loss_base":  round(base, 0),
                "loss_opti":  round(opti, 0),
            }
            totals["pessimistic"] += pess
            totals["base"]        += base
            totals["optimistic"]  += opti

        total_value = sum(portfolio_values[t] for t in portfolio_values if t in shocks)
        totals = {k: round(v, 0) for k, v in totals.items()}
        total_pct = {k: round(totals[k] / total_value * 100, 1) for k in totals}

        output[key] = {
            "name":        name,
            "description": description,
            "results":     scenario_results,
            "totals":      totals,
            "total_pct":   total_pct,
            "total_value": total_value,
        }

    return output


def plot_stress_test(stress_results: dict, output_dir: str, style: str = "dark") -> str:
    """三情景 × 三档 损失对比图"""
    _set_style(style)

    n_scenarios = len(stress_results)
    fig, axes = plt.subplots(1, n_scenarios, figsize=(6 * n_scenarios, 6))
    if n_scenarios == 1:
        axes = [axes]

    colors = {"pessimistic": "#e05d5d", "base": "#f2a623", "optimistic": "#5bc4a5"}
    labels_cn = {c: L(c) for c in ["pessimistic", "base", "optimistic"]}

    for ax, (key, sc) in zip(axes, stress_results.items()):
        tickers  = list(sc["results"].keys())
        x        = np.arange(len(tickers))
        width    = 0.25

        _loss_key = {"pessimistic": "loss_pess", "base": "loss_base", "optimistic": "loss_opti"}
        for i, case in enumerate(["pessimistic", "base", "optimistic"]):
            vals = [abs(sc["results"][t][_loss_key[case]]) for t in tickers]
            bars = ax.bar(x + (i - 1) * width, vals, width,
                          label=f"{labels_cn[case]}",
                          color=colors[case], alpha=0.85)
            for bar, v in zip(bars, vals):
                if v > 0:
                    ax.text(bar.get_x() + bar.get_width()/2,
                            bar.get_height() + 20,
                            f"${v:,.0f}", ha="center", va="bottom", fontsize=7)

        ax.set_xticks(x)
        ax.set_xticklabels(tickers, rotation=15, ha="right", fontsize=9)
        ax.set_ylabel(L("estimated_loss_cad"))
        ax.set_title(f"{sc['name']}\n{sc['description']}", fontsize=10, pad=8)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.15, axis="y")

        # 底部注释：总损失
        base_loss = abs(sc["totals"]["base"])
        base_pct  = abs(sc["total_pct"]["base"])
        ax.text(0.5, -0.18, f"基准情景总损失：-${base_loss:,.0f} ({base_pct:.1f}%)",
                transform=ax.transAxes, ha="center", fontsize=9, color="#f2a623")

    fig.suptitle(L("stress_test_title"), fontsize=14, y=1.02)
    fig.tight_layout()

    path = os.path.join(output_dir, "etf_stress_test.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  📊 压力测试图 → {path}")
    return path


def plot_portfolio_concentration(stress_results: dict, output_dir: str,
                                 style: str = "dark") -> str:
    """显示各ETF在不同情景下对总损失的贡献比例"""
    _set_style(style)

    scenario_keys = list(stress_results.keys())
    # 用第一个情景的基准档做贡献度分析
    sc = stress_results[scenario_keys[0]]
    tickers = list(sc["results"].keys())

    losses = {t: abs(sc["results"][t]["loss_base"]) for t in tickers}
    total  = sum(losses.values())
    shares = {t: v / total * 100 for t, v in losses.items()}

    fig, ax = plt.subplots(figsize=(7, 4))
    colors_pie = ["#9b72cf", "#5bc4a5", "#f2a623", "#e05d5d", "#5ba4cf", "#a0d468"]

    wedges, texts, autotexts = ax.pie(
        list(shares.values()),
        labels=list(shares.keys()),
        colors=colors_pie[:len(tickers)],
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(9)

    ax.set_title(f"{L('loss_concentration')}\n（{sc['name']}）", fontsize=11)
    fig.tight_layout()

    path = os.path.join(output_dir, "etf_loss_concentration.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  📊 损失集中度图 → {path}")
    return path


def save_stress_csv(stress_results: dict, output_dir: str) -> str:
    rows = []
    for key, sc in stress_results.items():
        for ticker, r in sc["results"].items():
            rows.append({
                L("scenario"):              sc["name"],
                L("ticker"):                ticker,
                L("current_value_stress"):  r["current_value"],
                L("shock_pess"):            r["shock_pess_pct"],
                L("shock_base"):            r["shock_base_pct"],
                L("shock_opti"):            r["shock_opti_pct"],
                L("loss_pess"):             r["loss_pess"],
                L("loss_base"):             r["loss_base"],
                L("loss_opti"):             r["loss_opti"],
            })
        # 添加合计行
        rows.append({
            L("scenario"):              sc["name"],
            L("ticker"):                L("total"),
            L("current_value_stress"):  sc["total_value"],
            L("shock_pess"):            sc["total_pct"]["pessimistic"],
            L("shock_base"):            sc["total_pct"]["base"],
            L("shock_opti"):            sc["total_pct"]["optimistic"],
            L("loss_pess"):             sc["totals"]["pessimistic"],
            L("loss_base"):             sc["totals"]["base"],
            L("loss_opti"):             sc["totals"]["optimistic"],
        })

    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "etf_stress_test_summary.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  📄 压力测试CSV → {path}")
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

def run(config: dict, dca_results: dict = None) -> dict:
    """
    Parameters
    ----------
    config      : dict  已解析的 config.yaml
    dca_results : dict  Module 2 的 DCA 结果（如有，用实际市值替代配置中的估算值）

    Returns
    -------
    dict  {"stress_results": dict, "files": [...]}
    """
    scenarios  = config["stress_scenarios"]
    output_dir = config["output"]["directory"]
    style      = config["output"].get("chart_style", "dark")

    os.makedirs(output_dir, exist_ok=True)

    # 持仓市值：优先用 DCA 实际模拟结果，否则用配置中的估算值
    if dca_results:
        portfolio_values = {t: round(d["current_value"], 0)
                            for t, d in dca_results.items()}
        print("  💡 使用 Module 2 DCA 实际模拟市值")
    else:
        portfolio_values = config["portfolio"].get("current_values_cad", {})
        print("  💡 使用 config.yaml 中的估算市值")

    print("=" * 50)
    print("  Module 3: 情景压力测试")
    print("=" * 50)
    print(f"\n  持仓市值：{portfolio_values}")
    print(f"  情景数量：{len(scenarios)}\n")

    stress_results = run_stress_test(scenarios, portfolio_values)

    # 打印汇总
    print(f"  {'情景':<16} {'悲观':>12} {'基准':>12} {'乐观':>12}")
    print("  " + "-" * 56)
    for key, sc in stress_results.items():
        print(f"  {sc['name']:<16} "
              f"${abs(sc['totals']['pessimistic']):>10,.0f} "
              f"${abs(sc['totals']['base']):>10,.0f} "
              f"${abs(sc['totals']['optimistic']):>10,.0f}")
        print(f"  {'':16} "
              f"{sc['total_pct']['pessimistic']:>11.1f}% "
              f"{sc['total_pct']['base']:>11.1f}% "
              f"{sc['total_pct']['optimistic']:>11.1f}%")

    files = []
    files.append(plot_stress_test(stress_results, output_dir, style))
    files.append(plot_portfolio_concentration(stress_results, output_dir, style))
    files.append(save_stress_csv(stress_results, output_dir))

    if config["output"].get("generate_json", True):
        json_path = os.path.join(output_dir, "stress_results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at":   datetime.now().isoformat(),
                "portfolio_values": portfolio_values,
                "stress_results": stress_results,
            }, f, ensure_ascii=False, indent=2)
        files.append(json_path)
        print(f"  📄 JSON → {json_path}")

    print(f"\n✅ Module 3 完成，共生成 {len(files)} 个文件\n")
    return {"stress_results": stress_results, "files": files}
