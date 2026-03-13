# ================================================================
# modules/labels.py
# 双语标签系统 — 支持 zh / en / both
# ================================================================
# 使用方式：
#   from modules.labels import L
#   L.set_lang("both")
#   print(L("cumulative_return"))  # → "累计收益率 / Cumulative Return"
# ================================================================

_ZH = {
    # 图表标题
    "cumulative_return":       "累计收益率对比",
    "correlation_matrix":      "ETF 相关性矩阵",
    "correlation_subtitle":    "越接近1.0 = 分散化效果越差",
    "dca_vs_value":            "定投：总投入 vs 当前市值",
    "dca_return_compare":      "定投收益率对比",
    "stress_test_title":       "压力测试：各情景损失估算",
    "loss_concentration":      "基准情景下各ETF损失贡献度",

    # 坐标轴 & 图例
    "amount_cad":              "金额（CAD）",
    "return_pct":              "收益率 (%)",
    "estimated_loss_cad":      "估计损失 (CAD)",
    "total_invested":          "总投入",
    "current_value":           "当前市值",

    # 压力测试档位
    "pessimistic":             "悲观",
    "base":                    "基准",
    "optimistic":              "乐观",

    # 指标名称（CSV列头）
    "ticker":                  "Ticker",
    "total_return":            "总收益率(%)",
    "annual_return":           "年化收益率(%)",
    "volatility":              "年化波动率(%)",
    "max_drawdown":            "最大回撤(%)",
    "sharpe":                  "夏普比率",
    "periods":                 "定投期数",
    "amount_per_period":       "每期金额(CAD)",
    "total_invested_csv":      "总投入(CAD)",
    "current_value_csv":       "当前市值(CAD)",
    "profit":                  "浮盈(CAD)",
    "return_pct_csv":          "收益率(%)",
    "scenario":                "情景",
    "current_value_stress":    "当前市值",
    "shock_pess":              "冲击(悲观%)",
    "shock_base":              "冲击(基准%)",
    "shock_opti":              "冲击(乐观%)",
    "loss_pess":               "损失(悲观)",
    "loss_base":               "损失(基准)",
    "loss_opti":               "损失(乐观)",
    "total":                   "合计",

    # 提示文字
    "corr_warning_high":       "极高",
    "corr_warning_mid":        "高",
    "no_corr_warning":         "无高相关性警告",
}

_EN = {
    "cumulative_return":       "Cumulative Return Comparison",
    "correlation_matrix":      "ETF Correlation Matrix",
    "correlation_subtitle":    "Closer to 1.0 = Less Diversification Benefit",
    "dca_vs_value":            "DCA: Total Invested vs Current Value",
    "dca_return_compare":      "DCA Return by ETF",
    "stress_test_title":       "Stress Test: Estimated Losses by Scenario",
    "loss_concentration":      "Loss Contribution by ETF (Base Case)",

    "amount_cad":              "Amount (CAD)",
    "return_pct":              "Return (%)",
    "estimated_loss_cad":      "Estimated Loss (CAD)",
    "total_invested":          "Total Invested",
    "current_value":           "Current Value",

    "pessimistic":             "Pessimistic",
    "base":                    "Base",
    "optimistic":              "Optimistic",

    "ticker":                  "Ticker",
    "total_return":            "Total Return (%)",
    "annual_return":           "Annual Return (%)",
    "volatility":              "Volatility (%)",
    "max_drawdown":            "Max Drawdown (%)",
    "sharpe":                  "Sharpe Ratio",
    "periods":                 "DCA Periods",
    "amount_per_period":       "Amount/Period (CAD)",
    "total_invested_csv":      "Total Invested (CAD)",
    "current_value_csv":       "Current Value (CAD)",
    "profit":                  "Profit (CAD)",
    "return_pct_csv":          "Return (%)",
    "scenario":                "Scenario",
    "current_value_stress":    "Current Value",
    "shock_pess":              "Shock Pessimistic (%)",
    "shock_base":              "Shock Base (%)",
    "shock_opti":              "Shock Optimistic (%)",
    "loss_pess":               "Loss Pessimistic",
    "loss_base":               "Loss Base",
    "loss_opti":               "Loss Optimistic",
    "total":                   "Total",

    "corr_warning_high":       "Very High",
    "corr_warning_mid":        "High",
    "no_corr_warning":         "No high-correlation warnings",
}


class _LabelSystem:
    """
    全局标签系统。在 run_analysis.py 里调用 L.set_lang() 一次，
    之后所有模块调用 L("key") 即可获得对应语言的标签。
    """
    def __init__(self):
        self._lang = "zh"

    def set_lang(self, lang: str):
        """lang: 'zh' | 'en' | 'both'"""
        assert lang in ("zh", "en", "both"), f"language 必须是 zh / en / both，收到: {lang}"
        self._lang = lang

    def __call__(self, key: str) -> str:
        zh = _ZH.get(key, key)
        en = _EN.get(key, key)
        if self._lang == "zh":
            return zh
        elif self._lang == "en":
            return en
        else:  # both
            if zh == en:
                return zh
            return f"{zh} / {en}"

    @property
    def lang(self):
        return self._lang

    def case_label(self, case: str) -> str:
        """'pessimistic' → 对应语言的悲观/Pessimistic/悲观 / Pessimistic"""
        return self(case)


# 全局单例，所有模块共享
L = _LabelSystem()
