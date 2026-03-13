#!/usr/bin/env python3
# ================================================================
# run_analysis.py — ETF Portfolio Analyzer Pipeline 主入口
# ================================================================
#
# 用法：
#   python run_analysis.py                    # 使用默认 config.yaml
#   python run_analysis.py --config my.yaml   # 指定配置文件
#   python run_analysis.py --modules 1 2      # 只跑指定模块
#   python run_analysis.py --help             # 显示帮助
#
# ================================================================

import argparse
import sys
import os
import time
from datetime import datetime

# ── 路径修复（模块级，最早执行）──────────────────────────────
# 必须在所有 from modules import ... 之前执行
# 确保无论从哪个目录调用，都能找到 modules/ 文件夹
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
os.chdir(_SCRIPT_DIR)

try:
    import yaml
except ImportError:
    print("❌ 缺少依赖：pyyaml")
    print("   请运行：pip install pyyaml")
    sys.exit(1)


# ── 参数解析 ──────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="ETF Portfolio Analyzer — 一键运行全流程分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run_analysis.py
  python run_analysis.py --config my_portfolio.yaml
  python run_analysis.py --modules 1 2
  python run_analysis.py --no-pdf
        """
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="配置文件路径（默认：config.yaml）"
    )
    parser.add_argument(
        "--modules", nargs="+", type=int, choices=[1, 2, 3],
        default=[1, 2, 3],
        help="要运行的模块（1=指标, 2=DCA相关性, 3=压力测试）"
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="跳过PDF报告生成"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="覆盖配置文件中的输出目录"
    )
    return parser.parse_args()


# ── 配置加载 ──────────────────────────────────────────────────

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        print(f"❌ 找不到配置文件：{path}")
        print("   请确认 config.yaml 和 run_analysis.py 在同一个文件夹。")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 基础校验
    required = ["portfolio", "dates", "dca", "stress_scenarios", "output"]
    for key in required:
        if key not in config:
            print(f"❌ 配置文件缺少必填项：{key}")
            sys.exit(1)

    if not config["portfolio"].get("tickers"):
        print("❌ portfolio.tickers 不能为空，至少填一只ETF")
        sys.exit(1)

    # 检查 DCA amounts 中的 ticker 是否在 portfolio 中
    portfolio_tickers = set(config["portfolio"]["tickers"].keys())
    dca_tickers       = set(config["dca"].get("amounts_cad", {}).keys())
    unknown = dca_tickers - portfolio_tickers
    if unknown:
        print(f"⚠️  DCA amounts 中有 ticker 不在 portfolio 里，将被忽略：{unknown}")

    return config


# ── 依赖检查 ──────────────────────────────────────────────────

def check_dependencies():
    missing = []
    packages = {
        "yfinance":    "yfinance",
        "pandas":      "pandas",
        "numpy":       "numpy",
        "matplotlib":  "matplotlib",
        "yaml":        "pyyaml",
    }
    for module, pkg in packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("❌ 缺少以下依赖，请先安装：")
        print(f"   pip install {' '.join(missing)}")
        sys.exit(1)


# ── 工具函数 ──────────────────────────────────────────────────

def print_banner():
    print()
    print("=" * 60)
    print("  ETF Portfolio Analyzer — 全流程分析 Pipeline")
    print(f"  运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()


def print_config_summary(config: dict):
    tickers    = config["portfolio"]["tickers"]
    dates      = config["dates"]
    dca        = config["dca"]
    scenarios  = config["stress_scenarios"]

    print("📋 当前配置：")
    print(f"  ETF组合：{', '.join(tickers.keys())}")
    print(f"  数据范围：{dates['start']} → {dates['end']}")
    print(f"  定投方式：{dca.get('frequency','monthly')}，"
          f"每期总投入 ${sum(dca.get('amounts_cad',{}).values())} CAD")
    print(f"  压力测试情景：{', '.join(sc['name'] for sc in scenarios.values())}")
    print(f"  输出目录：{config['output']['directory']}")
    print()


def print_final_summary(results: dict, elapsed: float):
    print()
    print("=" * 60)
    print("  ✅ 全部分析完成")
    print(f"  耗时：{elapsed:.1f} 秒")
    print()

    all_files = []
    for module_key, res in results.items():
        if res and "files" in res:
            all_files.extend(res["files"])

    print(f"  📁 共生成 {len(all_files)} 个文件：")
    for f in all_files:
        size = os.path.getsize(f) / 1024 if os.path.exists(f) else 0
        print(f"     {os.path.basename(f):<45} {size:>6.1f} KB")
    print()
    print("  提示：打开 outputs/ 文件夹查看所有图表和报告")
    print("=" * 60)
    print()


# ── 主流程 ────────────────────────────────────────────────────

def main():
    args = parse_args()

    print_banner()
    check_dependencies()

    config = load_config(args.config)

    # 命令行覆盖输出目录
    if args.output_dir:
        config["output"]["directory"] = args.output_dir

    # 命令行关闭PDF
    if args.no_pdf:
        config["output"]["generate_pdf"] = False

    print_config_summary(config)

    # 模块导入（路径已在文件顶部设置好）
    from modules import fetch_metrics, dca_correlation, stress_test
    from modules.labels import L

    # 设置全局标签语言：zh / en / both
    lang = config["output"].get("language", "zh")
    L.set_lang(lang)
    lang_display = {"zh": "中文", "en": "English", "both": "中英双语"}
    print(f"  🌐 图表语言：{lang_display.get(lang, lang)}\n")

    start_time = time.time()
    results = {}

    # ── Module 1 ──────────────────────────────────────────────
    if 1 in args.modules:
        try:
            results["module1"] = fetch_metrics.run(config)
        except Exception as e:
            print(f"❌ Module 1 失败：{e}")
            if "--debug" in sys.argv:
                raise
            sys.exit(1)
    else:
        print("⏭  跳过 Module 1（数据拉取）\n")
        results["module1"] = None

    # ── Module 2 ──────────────────────────────────────────────
    if 2 in args.modules:
        prices = results["module1"]["prices"] if results.get("module1") else None
        if prices is None:
            print("❌ Module 2 需要先运行 Module 1（价格数据）")
            sys.exit(1)
        try:
            results["module2"] = dca_correlation.run(config, prices)
        except Exception as e:
            print(f"❌ Module 2 失败：{e}")
            if "--debug" in sys.argv:
                raise
            sys.exit(1)
    else:
        print("⏭  跳过 Module 2（相关性 + DCA）\n")
        results["module2"] = None

    # ── Module 3 ──────────────────────────────────────────────
    if 3 in args.modules:
        # 优先用 Module 2 DCA 的实际市值
        dca_res = results["module2"]["dca_results"] if results.get("module2") else None
        try:
            results["module3"] = stress_test.run(config, dca_results=dca_res)
        except Exception as e:
            print(f"❌ Module 3 失败：{e}")
            if "--debug" in sys.argv:
                raise
            sys.exit(1)
    else:
        print("⏭  跳过 Module 3（压力测试）\n")
        results["module3"] = None

    # ── 最终汇总 ──────────────────────────────────────────────
    elapsed = time.time() - start_time
    print_final_summary(results, elapsed)


if __name__ == "__main__":
    main()
