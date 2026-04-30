# Stock Report - User Manual
## Module: gzajvaredini_stock_report

---

## Overview

This module generates detailed stock reports showing inventory movements with actual transaction prices.

### What Does It Show?
- **Initial Balance** - Stock at the beginning of the period
- **Incoming** - Products received (purchases, returns)
- **Outgoing** - Products delivered (sales, returns to vendors)
- **Final Balance** - Current stock position
- **Amounts** - Values calculated using actual transaction prices

---

## How to Access the Report

### Step 1: Open Stock Report
```
Main Menu → Inventory → Reporting → Stock Report
```

### Step 2: Set Report Parameters
A wizard window will open with the following fields:

| Field | Georgian Name | Description | Default |
|-------|---------------|-------------|---------|
| Start Date | საწყისი თარიღი | Beginning of report period | 30 days ago |
| End Date | საბოლოო თარიღი | End of report period | Today |
| Warehouses | საწყობები | Select specific warehouses | All |
| Filter by Category | კატეგორიებით გაფილტვრა | Enable category filtering | Unchecked |
| Categories | კატეგორიები | Select product categories | - |
| **შიდა გადაცემების გათვალისწინება** | - | Include internal transfers | **Unchecked** |

### Step 3: Generate Report
Click **"რეპორტის გენერაცია"** (Generate Report) button

---

## Understanding the Checkbox: "შიდა გადაცემების გათვალისწინება"

This is the **KEY feature** that controls how the report handles internal warehouse transfers.

### When UNCHECKED ☐ (Default):
**Shows only business transactions**

✅ **What's Included:**
- Purchases from vendors
- Sales to customers
- Returns from customers
- Returns to vendors

❌ **What's Excluded:**
- Warehouse-to-warehouse transfers
- Internal location movements
- Stock relocations between warehouses

**Use Case:** Monthly reports, accounting, financial statements

---

### When CHECKED ☑:
**Shows all logistics movements**

✅ **What's Included:**
- Everything from unchecked mode PLUS
- Warehouse-to-warehouse transfers
- Internal stock movements
- All internal logistics operations

**Use Case:** Detailed logistics tracking, warehouse management, complete movement audit

---

## Practical Examples

### Example 1: Simple Business Report

**Scenario:**
- Need monthly report for accounting
- Only want to see purchases and sales
- Don't care about internal movements

**Steps:**
1. Open Stock Report
2. Set dates: Jan 1 to Jan 31
3. **Leave checkbox UNCHECKED** ☐
4. Generate Report

**Result:**
- Shows only external transactions
- Clean, simple report for accounting

---

### Example 2: Detailed Logistics Report

**Scenario:**
- Need to track all movements
- Want to see warehouse transfers
- Auditing complete logistics flow

**Steps:**
1. Open Stock Report
2. Set dates: Jan 1 to Jan 31
3. **CHECK the checkbox** ☑
4. Generate Report

**Result:**
- Shows all movements including internal transfers
- Complete logistics picture

---

## Real Example with Numbers

### Setup:
```
Product: Widget A (Cost: 100 GEL)

Movements in January:
1. Jan 5:  Purchase 100 units from Vendor → Warehouse 1
2. Jan 10: Transfer 30 units from Warehouse 1 → Warehouse 2
3. Jan 15: Sell 20 units from Warehouse 1 → Customer
```

### Report with Checkbox UNCHECKED ☐:

**Warehouse 1:**
| Field | Value | Explanation |
|-------|-------|-------------|
| Initial Balance | 0 | No stock at start |
| Incoming | 100 | Purchase from vendor |
| Outgoing | 20 | Sale to customer |
| Final Balance | 50 | Actual stock (100-30-20) |

**Warehouse 2:**
| Field | Value | Explanation |
|-------|-------|-------------|
| Initial Balance | 0 | No stock at start |
| Incoming | 0 | Internal transfer not counted |
| Outgoing | 0 | No sales |
| Final Balance | 30 | Actual stock |

**Summary:** Only sees business transactions (purchase + sale)

---

### Report with Checkbox CHECKED ☑:

**Warehouse 1:**
| Field | Value | Explanation |
|-------|-------|-------------|
| Initial Balance | 0 | No stock at start |
| Incoming | 100 | Purchase from vendor |
| Outgoing | 50 | Transfer (30) + Sale (20) |
| Final Balance | 50 | Actual stock |

**Warehouse 2:**
| Field | Value | Explanation |
|-------|-------|-------------|
| Initial Balance | 0 | No stock at start |
| Incoming | 30 | Internal transfer counted |
| Outgoing | 0 | No sales |
| Final Balance | 30 | Actual stock |

**Summary:** Sees all movements including internal transfer

---

## Report Columns Explained

### Quantity Columns:
- **Initial Balance** - Stock quantity at start date
- **Incoming** - Total received quantity
- **Outgoing** - Total delivered quantity  
- **Final Balance** - Current stock quantity

### Amount Columns:
- **Initial Balance Amount** - Value of initial stock
- **Incoming Amount** - Total value received (uses actual purchase prices!)
- **Outgoing Amount** - Total value delivered
- **Final Balance Amount** - Current stock value

### Other Columns:
- **პროდუქცია** (Product) - Product name
- **პროდუქციის კოდი** (Product Code) - Internal reference
- **კატეგორია** (Category) - Product category
- **საწყობი** (Warehouse) - Warehouse name
- **ერთეული** (Unit) - Unit of measure

---

## Using Filters

### Date Range Filter:
**Purpose:** Control which period to analyze

**Example:**
- Last month: Set start = Dec 1, end = Dec 31
- Quarter: Set start = Jan 1, end = Mar 31
- Year: Set start = Jan 1, end = Dec 31

### Warehouse Filter:
**Purpose:** Focus on specific warehouses

**Example:**
- Single warehouse: Select "Main Warehouse"
- Multiple warehouses: Select multiple from list
- All warehouses: Leave empty

### Category Filter:
**Purpose:** Analyze specific product types

**Steps:**
1. Check "კატეგორიებით გაფილტვრა"
2. Select categories from "კატეგორიები" field
3. Generate report

**Example:**
- Only electronics: Select "Electronics" category
- Only furniture: Select "Furniture" category

---

## Advanced Features

### View History Button
Each product row has a **History** button (📜 icon)

**What it does:**
- Shows detailed movement list
- Displays dates, locations, quantities
- Links to original documents

**How to use:**
1. Find product in report
2. Click History button
3. View all movements for that product

### Export Options
**Export to Excel:**
1. Select rows (or leave all selected)
2. Click Action menu (⚙️)
3. Choose Export

**Export to PDF:**
1. Click Print button
2. Choose PDF format

### Quick Filters
At the top of the report:
- **With Stock** - Products with current stock > 0
- **Out of Stock** - Products with 0 stock
- **With Movement** - Products that had activity

---

## Testing Guide

### Quick Test (5 minutes):

**1. Create Test Data:**
```
Product: Test Item A
- Cost: 50 GEL
- Warehouse: Main Warehouse
```

**2. Create Purchase:**
```
- Purchase 100 units @ 55 GEL from Vendor
- Date: Today
- Validate receipt
```

**3. Create Internal Transfer:**
```
- Transfer 30 units to Secondary Warehouse
- Date: Today
- Validate transfer
```

**4. Test Unchecked:**
```
- Generate report with checkbox UNCHECKED ☐
- Expected: Main WH shows Incoming=100, Outgoing=0
- Expected: Secondary WH shows Incoming=0
```

**5. Test Checked:**
```
- Generate report with checkbox CHECKED ☑
- Expected: Main WH shows Incoming=100, Outgoing=30
- Expected: Secondary WH shows Incoming=30
```

**Success:** Numbers are DIFFERENT between the two reports!

---

## Common Scenarios

### Scenario 1: Monthly Accounting Report
**Need:** Clean report showing only purchases and sales

**Solution:**
1. Set dates to full month
2. **Leave checkbox UNCHECKED** ☐
3. Leave warehouse filter empty
4. Generate and export to Excel
5. Send to accounting

---

### Scenario 2: Warehouse Audit
**Need:** Verify physical count matches system

**Solution:**
1. Set date range to include all history
2. **Checkbox UNCHECKED** ☐ (for business transactions)
3. Select specific warehouse
4. Check Final Balance column
5. Compare with physical count

---

### Scenario 3: Logistics Review
**Need:** Track all warehouse movements including transfers

**Solution:**
1. Set dates to review period
2. **CHECK the checkbox** ☑
3. Leave warehouses empty (see all)
4. Review incoming/outgoing for transfers
5. Analyze logistics efficiency

---

### Scenario 4: Product Movement Analysis
**Need:** See where specific product moved

**Solution:**
1. Generate report with **checkbox CHECKED** ☑
2. Find product in list
3. Click History button
4. View detailed movement list
5. Trace product flow

---

### Scenario 5: Category Performance
**Need:** Analyze specific product category

**Solution:**
1. Check "კატეგორიებით გაფილტვრა"
2. Select category
3. Choose checkbox state based on needs
4. Generate report
5. Review category totals

---

## Troubleshooting

### Problem: No data appears
**Causes:**
- No stock movements in date range
- Warehouse filter too restrictive
- Products have no stock

**Solutions:**
- Expand date range
- Remove warehouse filter
- Check that transfers are validated

---

### Problem: Checkbox doesn't change anything
**Causes:**
- No internal transfers exist in date range
- Transfers not validated
- Wrong date range

**Solutions:**
- Create test internal transfer
- Validate all transfers
- Check transfer dates match report dates

---

### Problem: Numbers don't add up
**Causes:**
- Looking at wrong warehouse
- Mixed up unchecked vs checked states
- Transfers between warehouses

**Solutions:**
- Check which warehouse you're viewing
- Try both checkbox states
- Remember: Final Balance is always correct!

---

### Problem: Amounts showing as 0.00
**Causes:**
- Product cost not set
- Purchase order has no unit price

**Solutions:**
- Set product cost in product form
- Add unit prices to purchase orders
- Re-validate receipts if needed

---

## Important Notes

### ✅ Key Points to Remember:

1. **Final Balance is always accurate**
   - Shows actual current stock
   - Same regardless of checkbox state
   - Only incoming/outgoing columns change

2. **Checkbox controls visibility**
   - UNCHECKED = Business view (purchases/sales)
   - CHECKED = Logistics view (all movements)

3. **Amounts use real prices**
   - Incoming = Actual purchase prices
   - Not just current product cost
   - More accurate for accounting

4. **Transfers are bidirectional**
   - Source warehouse: shows as outgoing
   - Destination warehouse: shows as incoming
   - Only visible when checkbox CHECKED

5. **Reports are point-in-time**
   - Based on validated movements
   - Draft transfers don't appear
   - Re-generate for latest data

---

## Best Practices

### For Accounting:
- ✅ Use UNCHECKED ☐ mode
- ✅ Monthly date ranges
- ✅ Export to Excel
- ✅ Compare with financial reports

### For Warehouse Management:
- ✅ Use CHECKED ☑ mode
- ✅ Weekly or daily reports
- ✅ Filter by warehouse
- ✅ Track transfer efficiency

### For Inventory Audits:
- ✅ Use UNCHECKED ☐ mode
- ✅ Include all history
- ✅ Compare Final Balance to physical count
- ✅ Investigate discrepancies using History button

### For Cost Analysis:
- ✅ Focus on Incoming Amount column
- ✅ Compare different purchase prices
- ✅ Track cost trends over time
- ✅ Use for vendor evaluation

---

## Quick Reference

### Wizard Fields:
| Field | Required | Default |
|-------|----------|---------|
| Start Date | ✅ Yes | 30 days ago |
| End Date | ✅ Yes | Today |
| Warehouses | ❌ No | All |
| Categories | ❌ No | All |
| შიდა გადაცემების გათვალისწინება | ❌ No | Unchecked |

### Report Views:
- **List View** - Default, shows all data
- **Export** - Excel/CSV format
- **Print** - PDF format

### Checkbox States:
- **☐ UNCHECKED** - Business transactions only (DEFAULT)
- **☑ CHECKED** - All movements including internal transfers

---

## Summary Table

| Aspect | UNCHECKED ☐ | CHECKED ☑ |
|--------|------------|----------|
| **Purpose** | Business reporting | Logistics tracking |
| **Purchases** | ✅ Shown | ✅ Shown |
| **Sales** | ✅ Shown | ✅ Shown |
| **Internal Transfers** | ❌ Hidden | ✅ Shown |
| **Use For** | Accounting, Finance | Warehouse, Operations |
| **Complexity** | Simple | Detailed |
| **Final Balance** | ✅ Accurate | ✅ Accurate |

---

## Frequently Asked Questions

**Q: Which checkbox state should I use?**  
A: For accounting and financial reports, use UNCHECKED ☐. For warehouse operations and complete logistics tracking, use CHECKED ☑.

**Q: Why is Final Balance the same in both modes?**  
A: Final Balance shows actual physical stock, which doesn't change. Only the incoming/outgoing columns show different movements.

**Q: Can I see both views at once?**  
A: No, but you can generate two reports - one with checkbox unchecked and one checked - and compare them.

**Q: What if I have multiple warehouses?**  
A: Leave warehouse filter empty to see all warehouses, or select specific ones. Use CHECKED ☑ mode to see transfers between them.

**Q: How do amounts get calculated?**  
A: Incoming amounts use actual purchase prices from POs. Outgoing amounts use product cost. This gives accurate financial data.

**Q: Can I schedule automatic reports?**  
A: Not built into this module, but you can export to Excel and automate from there.

---

## Support

If you need help:
1. Review this manual
2. Try the Quick Test
3. Check Troubleshooting section
4. Contact your system administrator

---

**Module Version:** 1.1  
**Odoo Version:** 18.0  
**Last Updated:** January 2026  
**Feature:** Internal Transfer Control with Checkbox

---

## Quick Start Checklist

- [ ] Module installed and upgraded
- [ ] Can access Stock Report from menu
- [ ] Understand checkbox purpose (internal transfers)
- [ ] Tested with UNCHECKED ☐ mode
- [ ] Tested with CHECKED ☑ mode
- [ ] Verified numbers are different
- [ ] Know when to use each mode
- [ ] Can export reports
- [ ] Can use History button

**Happy Reporting!** 📊
