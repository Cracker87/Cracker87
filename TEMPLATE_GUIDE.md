# Comprehensive Financial Model Template Guide

## Overview

This is a complete financial model template designed for Indian businesses. It includes all core financial statements, supporting schedules, valuation analysis, and an executive dashboard.

---

## Template Files

| File | Sheet Name | Purpose |
|------|------------|---------|
| `01_INPUTS_ASSUMPTIONS.csv` | Inputs | All hardcoded assumptions |
| `02_PROFIT_LOSS.csv` | P&L | Income Statement |
| `03_CASH_FLOW.csv` | Cash Flow | Cash Flow Statement |
| `04_BALANCE_SHEET.csv` | Balance Sheet | Financial Position |
| `05_SCHEDULES.csv` | Schedules | Working Capital, Debt, Depreciation |
| `06_VALUATION.csv` | Valuation | DCF & Comparable Analysis |
| `07_SENSITIVITY.csv` | Sensitivity | Scenario & Sensitivity Analysis |
| `08_DASHBOARD.csv` | Dashboard | Executive Summary |

---

## Design Principles Applied

### 1. Layout: Starts at B2
- **Row 1**: Empty (buffer/header space)
- **Column A**: Empty (section labels/navigation)
- **Content begins at B2**: Provides visual breathing room

### 2. Structure: Centralized Inputs
All assumptions in one sheet (01_INPUTS_ASSUMPTIONS.csv)
- No hardcoded numbers in calculation sheets
- Single source of truth for all variables

### 3. Formulas: Simple & Readable
- Each calculation broken into separate rows
- No deeply nested formulas
- Helper rows for intermediate calculations
- Clear cell references to input section

---

## Sheet-by-Sheet Guide

### Sheet 1: Inputs & Assumptions

**Purpose**: Central repository for all model inputs

| Section | Contents |
|---------|----------|
| General Inputs | Company info, dates, projection period |
| Revenue Assumptions | Product mix, pricing, volumes, growth rates |
| Cost Assumptions | Variable costs (%), Fixed costs (₹) |
| Financing Assumptions | Loan details, interest rates, equity |
| Tax & Depreciation | Tax rates, depreciation rates by asset |
| Working Capital | Receivable/Inventory/Payable days |
| Capex Assumptions | Initial capex, maintenance capex |

**Key Rule**: ALL numbers that can change go here.

---

### Sheet 2: Profit & Loss Statement

**Purpose**: Income statement with 5-year projections

| Section | Contents |
|---------|----------|
| Revenue | Product-wise breakdown, discounts |
| Other Income | Interest, miscellaneous |
| COGS | Raw material, labour, overheads |
| Operating Expenses | Detailed expense breakdown |
| EBITDA | Operating profit before depreciation |
| Depreciation | Asset-wise depreciation |
| Finance Costs | Interest on term loan, WC loan |
| Tax | Current tax, deferred tax |
| Net Profit | Bottom line with EPS |

**Margins Calculated**: Gross, EBITDA, EBIT, PBT, Net Profit

---

### Sheet 3: Cash Flow Statement

**Purpose**: Track cash movements across three activities

| Activity | Includes |
|----------|----------|
| Operating | Net profit adjustments, working capital changes |
| Investing | Capex, asset sales, interest received |
| Financing | Equity, borrowings, repayments, dividends |

**Key Metrics**:
- Free Cash Flow (FCF)
- Debt Service Coverage Ratio (DSCR)
- Interest Coverage Ratio

---

### Sheet 4: Balance Sheet

**Purpose**: Financial position snapshot

| Section | Includes |
|---------|----------|
| Equity | Share capital, reserves |
| Non-Current Liabilities | Term loans (long-term portion) |
| Current Liabilities | Short-term debt, payables, provisions |
| Non-Current Assets | Fixed assets (gross & net), intangibles |
| Current Assets | Inventory, receivables, cash |

**Ratios Calculated**:
- Liquidity: Current ratio, Quick ratio
- Solvency: Debt/Equity, Debt/Assets
- Efficiency: Asset turnover, Fixed asset turnover
- Profitability: ROA, ROE, ROCE

**Built-in Balance Check**: Assets - Liabilities = 0

---

### Sheet 5: Supporting Schedules

**Purpose**: Detailed calculations supporting main statements

| Schedule | Purpose |
|----------|---------|
| Working Capital | DSO, DIO, DPO calculations |
| Debt Amortization | EMI schedule with principal/interest split |
| Working Capital Loan | Utilization and interest |
| Depreciation | Asset-wise WDV depreciation schedule |

---

### Sheet 6: Valuation

**Purpose**: Estimate enterprise and equity value

| Method | Approach |
|--------|----------|
| WACC Calculation | Cost of equity (CAPM), cost of debt |
| DCF Valuation | 5-year FCF + Terminal value |
| Comparable Multiples | EV/Revenue, EV/EBITDA, P/E |
| Weighted Average | Combined valuation estimate |

**Outputs**: Enterprise Value, Equity Value, Per Share Value

---

### Sheet 7: Sensitivity Analysis

**Purpose**: Understand impact of variable changes

| Analysis | Variables |
|----------|-----------|
| Revenue Sensitivity | -20% to +20% impact on profit |
| Cost Sensitivity | Raw material %, Fixed cost changes |
| Interest Rate | 10% to 15% rate scenarios |
| Two-Way Tables | Revenue Growth vs WACC, EBITDA vs Terminal Growth |
| Scenario Analysis | Worst/Conservative/Base/Optimistic/Best |
| Break-Even | Operating, Cash, Debt Service break-even |

**Probability-Weighted Valuation**: Expected value calculation

---

### Sheet 8: Executive Dashboard

**Purpose**: One-page summary for decision makers

| Section | Contents |
|---------|----------|
| KPI Summary | Revenue, EBITDA, Net Profit, Valuation |
| 5-Year Trends | Financial metrics with visual indicators |
| Revenue Breakdown | Product-wise contribution |
| Capital Structure | Sources of funds, debt metrics |
| Cash Flow Summary | Activity-wise cash flows |
| Valuation Summary | Method-wise values, range |
| Risk Indicators | Traffic light alerts for key metrics |
| Assumptions Summary | Quick reference for key inputs |

---

## Indian Numbering System Reference

| Standard | Indian | Value |
|----------|--------|-------|
| 100,000 | 1,00,000 | 1 Lakh |
| 10,000,000 | 1,00,00,000 | 1 Crore |
| 1,000,000,000 | 1,00,00,00,000 | 1 Arab |

### Excel Format Code for Indian System
```
[>=10000000]₹ ##\,##\,##\,##0;[>=100000]₹ ##\,##\,##0;₹ ##,##0
```

---

## How to Use This Template

### Step 1: Import All CSV Files
1. Open Excel
2. Create a new workbook with 8 sheets
3. Rename sheets: Inputs, P&L, Cash Flow, Balance Sheet, Schedules, Valuation, Sensitivity, Dashboard
4. Import each CSV into respective sheet

### Step 2: Link the Sheets
Create references between sheets:
```excel
# In P&L sheet, reference Inputs:
=Inputs!$D$12  (for Revenue assumptions)

# In Balance Sheet, reference P&L:
='P&L'!D85     (for Net Profit)
```

### Step 3: Replace Values
The template contains sample data for a manufacturing company:
- Base Revenue: ₹50 Lakhs
- 5-Year projection period
- Term Loan: ₹20 Lakhs @ 12%
- Equity: ₹15 Lakhs

Customize these in the Inputs sheet.

### Step 4: Apply Formatting
| Element | Format |
|---------|--------|
| Headers | Bold, dark background |
| Inputs | Yellow background |
| Formulas | White background |
| Outputs | Blue/Green background |
| Negatives | Red font or (brackets) |

### Step 5: Validate
- Check Balance Sheet balances
- Verify Cash Flow ties to Balance Sheet cash
- Confirm DSCR and coverage ratios

---

## Color Coding Convention

| Color | Meaning |
|-------|---------|
| Yellow | Hardcoded input (editable) |
| White | Formula (do not edit) |
| Blue | Output/Result |
| Green | Positive indicator |
| Red | Warning/Negative |
| Grey | Label/Header |

---

## Key Formulas Reference

### Revenue Projection
```excel
Year 2 Revenue = Year 1 Revenue × (1 + Growth Rate)
```

### Working Capital
```excel
Receivables = (Revenue / 365) × Receivable Days
Inventory = (COGS / 365) × Inventory Days
Payables = (Purchases / 365) × Payable Days
```

### EMI Calculation
```excel
=PMT(Rate/12, Tenure×12, -Principal)
```

### WACC
```excel
=(%Equity × Cost of Equity) + (%Debt × Cost of Debt × (1-Tax Rate))
```

### DCF Terminal Value
```excel
=FCF × (1 + Terminal Growth) / (WACC - Terminal Growth)
```

### DSCR
```excel
=EBITDA / (Interest + Principal Repayment)
```

---

## Best Practices Checklist

- [ ] All inputs in dedicated section at top
- [ ] No hardcoded numbers in formula cells
- [ ] Consistent formatting throughout
- [ ] Named ranges for key inputs
- [ ] Input cells highlighted in yellow
- [ ] Formula cells protected
- [ ] Version number in header
- [ ] Print areas defined
- [ ] Balance sheet balances
- [ ] Cash flow ties to balance sheet
- [ ] Sensitivity ranges are realistic
- [ ] Scenarios cover reasonable outcomes

---

## Customization Options

### For Different Industries
Modify the Inputs sheet:
- **Services**: Remove inventory, adjust margins
- **Retail**: Add inventory turnover, seasonal adjustments
- **SaaS**: Add MRR/ARR, churn, CAC/LTV metrics
- **Real Estate**: Add construction timeline, area-based revenues

### For Different Stages
- **Startup**: Focus on burn rate, runway, funding rounds
- **Growth**: Emphasize revenue growth, unit economics
- **Mature**: Focus on margins, ROCE, dividend capacity

---

## File Information

- **Version**: 2.0 (Enhanced)
- **Format**: Indian Numbering (₹ Lakhs/Crores)
- **Layout**: B2 start position
- **Structure**: Multi-sheet with centralized inputs
- **Sample Data**: Manufacturing company, 5-year projection
- **Valuation Methods**: DCF, Comparables, Weighted Average

---

## Support & Updates

For questions or customization requests, refer to:
1. Sample calculations in each sheet
2. This documentation guide
3. Industry-standard financial modeling resources

---

## Disclaimer

This template is for educational and planning purposes. Actual financial decisions should be made with professional advice. Projections are estimates and actual results may vary.
