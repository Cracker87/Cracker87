# Financial Model Template Guide

## Overview

This template follows best practices for spreadsheet design tailored for Indian financial reporting.

---

## Design Principles Applied

### 1. Layout: Starts at B2
- **Row 1**: Empty (buffer/header space)
- **Column A**: Empty (section labels/navigation)
- **Content begins at B2**: Provides visual breathing room

### 2. Structure: Centralized Inputs
```
Rows 2-35:   ASSUMPTIONS & INPUTS (all hardcoded values here)
Rows 36-55:  CALCULATIONS (formulas referencing inputs)
Rows 56-65:  KEY METRICS (ratios and analysis)
Rows 66+:    OUTPUT SUMMARY (final results)
```

### 3. Formulas: Simple & Readable
- Each calculation broken into separate rows
- No deeply nested formulas
- Helper rows for intermediate calculations
- Clear cell references to input section

---

## Template Sections

### Section 1: Assumptions & Inputs (Rows 6-32)

| Subsection | Purpose |
|------------|---------|
| General Inputs | Model parameters (dates, currency, period) |
| Revenue Assumptions | Growth rates, base revenue |
| Cost Assumptions | Variable and fixed cost percentages |
| Financing Assumptions | Interest, tax, depreciation rates |

**Key Rule**: ALL hardcoded numbers go here. No magic numbers in formulas below.

### Section 2: Calculations (Rows 34-52)

| Subsection | Purpose |
|------------|---------|
| Revenue Projection | Year-by-year revenue with growth |
| Cost Breakdown | Itemized costs per year |
| Profitability | P&L from Gross Profit to Net Profit |

**Key Rule**: Every cell contains ONLY formulas referencing the Inputs section.

### Section 3: Key Metrics (Rows 54-60)

| Metric | Formula Logic |
|--------|---------------|
| Gross Margin | (Revenue - COGS) / Revenue |
| EBITDA Margin | EBITDA / Revenue |
| Net Profit Margin | Net Profit / Revenue |

### Section 4: Output Summary (Rows 62+)

Executive summary with totals and averages for quick review.

---

## Indian Numbering System Reference

| Standard | Indian | Value |
|----------|--------|-------|
| 100,000 | 1,00,000 | 1 Lakh |
| 10,000,000 | 1,00,00,000 | 1 Crore |

### Excel Format Code for Indian System
```
[>=10000000]₹ ##\,##\,##\,##0;[>=100000]₹ ##\,##\,##0;₹ ##,##0
```

---

## How to Use This Template

### Step 1: Import the CSV
1. Open Excel or Google Sheets
2. File → Import → Upload `financial_model_template.csv`
3. Select "Comma" as delimiter

### Step 2: Replace Placeholder Formulas
The template shows `=Formula`, `=Input`, `=SUM` as placeholders.

**Example replacements:**

| Placeholder | Replace With |
|-------------|--------------|
| `=Input` | Direct reference like `=$D$12` |
| `=Formula` | Calculation like `=D40*$D$15` |
| `=SUM` | Sum function like `=SUM(D40:H40)` |

### Step 3: Apply Formatting
1. **Number format**: Apply Indian numbering (see code above)
2. **Headers**: Bold, background color
3. **Inputs**: Light yellow background (industry standard)
4. **Formulas**: No background (white)
5. **Outputs**: Light blue or green background

### Step 4: Add Data Validation
For input cells, add dropdown lists or number ranges to prevent errors.

---

## Color Coding Convention

| Color | Meaning |
|-------|---------|
| Yellow | Hardcoded input (editable) |
| White | Formula (do not edit) |
| Blue | Output/Result |
| Grey | Label/Header |

---

## Formula Examples

### Revenue with Growth
```excel
Year 1: =Base_Revenue
Year 2: =D40*(1+$D$15)
Year 3: =E40*(1+$D$16)
```

### Cost Calculation
```excel
Raw Material: =D40*$D$21
Labour: =D40*$D$22
```

### Margin Calculation
```excel
Gross Margin: =(D40-D45)/D40
```

---

## Best Practices Checklist

- [ ] All inputs in dedicated section at top
- [ ] No hardcoded numbers in formula cells
- [ ] Consistent formatting throughout
- [ ] Named ranges for key inputs
- [ ] Input cells highlighted in yellow
- [ ] Formula cells protected (optional)
- [ ] Version number in header
- [ ] Print area defined

---

## File Information

- **Template**: `financial_model_template.csv`
- **Format**: Indian Numbering (₹ Lakhs/Crores)
- **Layout**: B2 start position
- **Structure**: Centralized inputs
- **Formulas**: Simple, readable, auditable
