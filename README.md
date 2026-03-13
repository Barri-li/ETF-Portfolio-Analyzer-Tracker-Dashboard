# ETF Portfolio Analyzer

A Python pipeline + interactive dashboard for analyzing any ETF portfolio.
Covers metrics, DCA simulation, correlation analysis, and scenario stress testing.
Built for Canadian TFSA investors — works with any global ticker supported by yfinance.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      config.yaml                            │
│   ETF tickers · DCA amounts & frequency · stress scenarios  │
│   date range · output language (zh / en / both)             │
└───────────────────────────┬─────────────────────────────────┘
                            │  python run_analysis.py
                            ▼
          ┌─────────────────────────────────────┐
          │         run_analysis.py             │
          │  Orchestrator — runs all modules    │
          │  in sequence, collects outputs      │
          └──────┬──────────┬──────────┬────────┘
                 │          │          │
        ┌────────▼──┐  ┌────▼──────┐  ┌▼────────────┐
        │ Module 1  │  │ Module 2  │  │  Module 3   │
        │  Metrics  │  │  DCA +    │  │   Stress    │
        │  & Fetch  │  │  Corr.    │  │   Testing   │
        └────────┬──┘  └────┬──────┘  └─┬───────────┘
                 │          │            │
                 └──────────┴────────────┘
                            │
              ┌─────────────▼──────────────┐
              │         outputs/           │
              │  *.png  *.csv  *.json      │
              └──────────┬─────────────────┘
                         │
              ┌──────────▼─────────────────┐
              │      index.html            │
              │  Interactive Dashboard     │
              │  (reads JSON, live prices) │
              └────────────────────────────┘
```

**Data flow in detail:**

```
yfinance API ──► Module 1: fetch_metrics.py
                   Pulls historical prices for all tickers
                   Calculates: total return, annual return,
                   volatility, max drawdown, Sharpe ratio
                   Outputs: etf_metrics.csv, metrics.json,
                            etf_cumulative_returns.png

               ──► Module 2: dca_correlation.py
                   Builds correlation matrix between ETFs
                   Simulates DCA purchases over time
                   Outputs: etf_correlation_matrix.png,
                            etf_dca_simulation.png,
                            etf_dca_summary.csv, dca_results.json

               ──► Module 3: stress_test.py
                   Applies scenario shocks from config.yaml
                   Estimates portfolio loss (pessimistic/base/optimistic)
                   Outputs: etf_stress_test.png,
                            etf_loss_concentration.png,
                            etf_stress_test_summary.csv, stress_results.json
```

**Key design principles:**
- `config.yaml` is the only file you ever need to edit
- Swap tickers, DCA amounts, or stress scenarios → re-run → done
- All three JSON files feed the dashboard automatically
- `modules/labels.py` handles bilingual output (zh / en / both)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/barri-li/etf-portfolio-analyzer.git
cd etf-portfolio-analyzer

# 2. Install dependencies
pip install yfinance pandas numpy matplotlib pyyaml

# 3. Edit your portfolio (tickers, DCA amounts, etc.)
# Open config.yaml and change what you need

# 4. Run the full pipeline
python run_analysis.py

# 5. Open the dashboard
python -m http.server 8080
# Then visit: http://localhost:8080
```

---

## Configuration (`config.yaml`)

Everything is controlled by one file. You never need to touch the Python code.

### Portfolio tickers

```yaml
portfolio:
  tickers:
    VFV.TO:  "Vanguard S&P 500 (CAD)"
    XEQT.TO: "iShares All-Equity"
    TEC.TO:  "TD Tech ETF"
    # Add any yfinance ticker: QQQ, VOO, VTI, 2800.HK, etc.

  current_values_cad:       # Used for stress test loss calculations
    VFV.TO:  9621
    XEQT.TO: 12014
    TEC.TO:  5454
```

### DCA parameters

```yaml
dca:
  start_date: "2022-01-01"
  frequency: "biweekly"    # weekly / biweekly / monthly
  amounts_cad:
    VFV.TO:  70
    XEQT.TO: 65
    TEC.TO:  35
```

### Stress test scenarios

```yaml
stress_scenarios:
  my_scenario:
    name: "Tech Crash"
    description: "Major AI regulation selloff"
    shocks:  # [pessimistic%, base%, optimistic%]
      VFV.TO:  [-20, -14, -8]
      XEQT.TO: [-16, -11, -6]
      TEC.TO:  [-45, -32, -20]
```

Add, remove, or rename scenarios freely — the pipeline adapts automatically.

### Output language

```yaml
output:
  language: "both"     # zh = 中文 | en = English | both = 中英双语
  chart_style: "dark"  # dark / light
```

---

## Dashboard Usage Guide

The dashboard (`index.html`) is a standalone HTML file — no build step needed.
For live prices + pipeline data, run a local HTTP server.

### Setup

```
etf-portfolio-analyzer/
├── index.html          ← The dashboard
├── run_analysis.py
├── config.yaml
├── modules/
└── outputs/            ← Pipeline JSON files go here
    ├── metrics.json
    ├── dca_results.json
    └── stress_results.json
```

```bash
python -m http.server 8080
# Open: http://localhost:8080
```

---

### Dashboard Views

The dashboard has four views, navigated from the left sidebar.

#### ▶ Summary

The main overview screen.

- **Ticker bar** — live prices for every ETF in your portfolio, with source badge (Yahoo / Google / manual) and daily % change
- **Stat cards** — total portfolio value, cost basis, unrealized P&L
- **Holdings Overview table** — price, daily change, shares held, P&L, DCA plan amount per ETF
- **Allocation bar** — portfolio weight by current market value
- **DCA donut charts** — target allocation per ETF
- **Area chart** — cumulative return history

Click **Edit** on any holdings row to update shares held or average cost.

#### ▶ Holdings Detail

Expanded table with full position data: shares, average cost, current price, market value, cost basis, P&L ($ and %), DCA plan amount, and next DCA date.

#### ▶ DCA 交易日志

Full transaction log for recording every DCA purchase.

- **Stats row** — total trades, total invested, total shares, weighted average price
- **Log table** — date, ETF, amount, shares, execution price, plan amount, deviation, memo
- **Per-ETF summary cards** — cumulative invested, shares held, average cost, unrealized P&L

**To record a purchase:** click **+ 记录定投** → fill in date / ETF / amount / shares → Save.
The memo auto-generates. Holdings recalculate automatically from the log.

**Export:** click **⬇ 导出 CSV** to download all records.

#### ▶ Analysis

Displays Python pipeline results. Run `python run_analysis.py` first.

- **核心指标** — per-ETF cards: total return, annual return, volatility, max drawdown, Sharpe ratio
- **相关性分析** — high-correlation warnings (≥ 0.90) between ETF pairs
- **定投模拟结果** — DCA performance: invested vs current value, return %
- **压力测试** — scenario loss tables (pessimistic / base / optimistic) for each scenario

Click **↻ 重新加载** to refresh after re-running the pipeline.

---

### Managing Your Portfolio (Manage ETFs)

Click **Manage ETFs** in the sidebar at any time.

**Current portfolio tab — edit existing ETFs inline:**

| Field | What it does |
|-------|-------------|
| DCA金额/期 | Amount invested per period (CAD) — saves on change |
| 频率 | weekly / biweekly / monthly |
| DCA开始日期 | Start date for this position's DCA plan |
| 持股数 | Current shares held — sync with your brokerage |

Click **✕ 删除** to remove an ETF. A confirmation dialog warns you if the ETF has holdings or log entries.

**新增 ETF tab — add a new position:**

| Field | Description |
|-------|-------------|
| Ticker 代码 | Any yfinance ticker — `CGL.C`, `QQC-F.TO`, `QQQ`, `2800.HK` |
| 显示名称 | Optional name shown in charts and tables |
| DCA金额/期 | Amount per period (CAD) |
| DCA开始日期 | When DCA begins |
| 频率 | weekly / biweekly / monthly |
| 颜色 | Color used across all charts and allocation views |
| 持股数 | Pre-fill if you already hold shares |

After adding, the ticker bar, all filters, and all views update immediately.
A live price fetch runs automatically for the new ticker.

---

### Live Price Fetching

The dashboard uses a three-layer fallback for every ticker:

```
Layer 1: Yahoo Finance  (6 attempts: 2 hosts × 3 CORS proxies)
Layer 2: Google Finance (HTML scrape via allorigins)
Layer 3: Manual entry   (popup to enter prices by hand)
```

Prices refresh automatically every 5 minutes.
Click **↻ Refresh Prices** in the sidebar for an immediate update.
Source badges on each price show which layer succeeded: `yahoo`, `google`, or `manual`.

---

## Output Files Reference

| File | Module | Description |
|------|--------|-------------|
| `etf_cumulative_returns.png` | 1 | Return chart for all ETFs |
| `etf_metrics.csv` | 1 | Core metrics table |
| `metrics.json` | 1 | Dashboard data feed |
| `etf_correlation_matrix.png` | 2 | Correlation heatmap |
| `etf_dca_simulation.png` | 2 | DCA invested vs current value |
| `etf_dca_summary.csv` | 2 | DCA results per ETF + total |
| `dca_results.json` | 2 | Dashboard data feed |
| `etf_stress_test.png` | 3 | Stress test loss chart |
| `etf_loss_concentration.png` | 3 | Loss contribution by ETF |
| `etf_stress_test_summary.csv` | 3 | Full stress test table |
| `stress_results.json` | 3 | Dashboard data feed |

---

## Advanced CLI Usage

```bash
# Run only specific modules
python run_analysis.py --modules 1 2

# Use a different config file
python run_analysis.py --config growth_portfolio.yaml

# Override the output directory
python run_analysis.py --output-dir my_results/

# Skip PDF report
python run_analysis.py --no-pdf

# Debug mode (full traceback on error)
python run_analysis.py --debug
```

---

## Project Structure

```
etf-portfolio-analyzer/
├── config.yaml              ← Only file you need to edit
├── run_analysis.py          ← Pipeline entry point
├── index.html               ← Interactive dashboard
├── modules/
│   ├── __init__.py
│   ├── fetch_metrics.py     ← Module 1: data fetch + metrics
│   ├── dca_correlation.py   ← Module 2: correlation + DCA simulation
│   ├── stress_test.py       ← Module 3: scenario stress testing
│   └── labels.py            ← Bilingual label system (zh / en / both)
├── outputs/                 ← Auto-created on first run
│   ├── *.png                ← Charts
│   ├── *.csv                ← Data tables
│   └── *.json               ← Dashboard data feeds
└── README.md
```

---

## Supported Tickers

Any ticker on [Yahoo Finance](https://finance.yahoo.com):

- **TSX (Canada):** `VFV.TO`, `XEQT.TO`, `TEC.TO`, `XIU.TO`, `ZAG.TO`, `CGL.C`
- **NYSE / NASDAQ:** `QQQ`, `VOO`, `VTI`, `ARKK`, `SPY`, `GLD`
- **Hong Kong:** `2800.HK`, `3032.HK`
- **Other exchanges:** use the exchange suffix as shown on Yahoo Finance

---

## Requirements

- Python 3.9+
- `yfinance >= 0.2`
- `pandas >= 2.0`
- `numpy >= 1.24`
- `matplotlib >= 3.7`
- `pyyaml >= 6.0`

---

## About

Built as a personal finance + Python learning project.
Portfolio context: Canadian TFSA investor, TSX-listed ETFs, bi-weekly DCA strategy.

---

*Data sourced from Yahoo Finance via yfinance. For informational purposes only — not financial advice.*
