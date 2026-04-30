# Stock Report - Quick Start Guide

## 🚀 What Changed?

The stock report now uses **actual transaction prices** from your purchase orders and stock pickings, giving you more accurate cost calculations!

---

## 📋 Quick Testing Steps

### Test 1: Simple Purchase Receipt (5 minutes)

1. **Create a Product:**
   - Go to: `Inventory → Products → Products`
   - Click `Create`
   - Name: `Test Widget`
   - Cost: `100 GEL`
   - Save

2. **Create Purchase Order:**
   - Go to: `Purchase → Orders → Purchase Orders`
   - Create new PO with your test product
   - Quantity: `50`
   - Unit Price: `120 GEL` (different from cost!)
   - Confirm and receive the products

3. **Generate Stock Report:**
   - Go to: `Inventory → Reporting → Stock Report`
   - Select date range that includes your receipt
   - Click `Generate Report`

4. **Check Results:**
   - Find your Test Widget
   - Incoming Qty should show: `50`
   - **Incoming Amount should show: `6,000` (50 × 120)** ✅
   - NOT 5,000 (50 × 100) ❌

**Why this matters:** The report now shows you actually paid 6,000 GEL, not the standard cost of 5,000 GEL!

---

## 🎯 Main Testing Scenarios

### Scenario A: Multiple Purchases at Different Prices
**Purpose:** Verify different prices are tracked

**Quick Steps:**
1. Buy 30 units @ 40 GEL on Jan 5
2. Buy 50 units @ 45 GEL on Jan 10  
3. Buy 20 units @ 50 GEL on Jan 15
4. Run report for Jan 1-31

**Expected:** 
- Incoming Qty: 100
- Incoming Amount: 4,450 (not 100 × standard_price)

---

### Scenario B: Date Range Filtering
**Purpose:** Verify date filtering works

**Quick Steps:**
1. Create receipts on different dates
2. Run report for short period (Jan 1-10)
3. Run report for longer period (Jan 1-31)
4. Compare results

**Expected:** Only movements in date range appear

---

### Scenario C: Warehouse Filtering  
**Purpose:** Verify warehouse isolation

**Quick Steps:**
1. Create receipts in Warehouse A
2. Create receipts in Warehouse B
3. Run report filtered for only Warehouse A

**Expected:** Only Warehouse A data appears

---

## 📊 How to Use in Odoo

### Step 1: Navigate to Report
```
Main Menu → Inventory → Reporting → Stock Report
```

### Step 2: Set Parameters
- **Start Date:** Choose start date (default: 30 days ago)
- **End Date:** Choose end date (default: today)
- **Warehouses:** Select specific warehouses or leave empty for all
- **Categories:** Optional - check box and select categories

### Step 3: Generate
- Click `Generate Report` button
- Report opens in new window

### Step 4: Analyze Data
Look at these columns:
- **Incoming Qty:** Products received
- **Incoming Amount:** Total cost of receipts (uses actual purchase prices!)
- **Outgoing Qty:** Products delivered
- **Outgoing Amount:** Total cost of deliveries
- **Final Balance:** Current stock quantity
- **Final Amount:** Current stock value

---

## 💡 Key Features

### ✅ Actual Prices Used
The report now uses:
- Purchase prices from purchase orders
- Transaction prices from stock moves
- Falls back to product cost if no specific price

### ✅ History Button
Click the history icon (📜) on any row to see:
- All movements for that product
- Detailed quantities and dates
- Source and destination locations

### ✅ Flexible Filtering
Filter by:
- Date range
- Warehouse
- Product category
- Product name
- Quantity ranges
- Amount ranges

---

## 🧪 Example Test Values

### Sample Product Setup:

| Product | Category | Cost | Test Price |
|---------|----------|------|------------|
| Test Product A | Electronics | 50.00 | 55.00 |
| Test Product B | Furniture | 200.00 | 220.00 |
| Test Product C | Supplies | 10.00 | 12.00 |

### Sample Movements:

**Receipts (Incoming):**
| Date | Product | Warehouse | Qty | Price | Total |
|------|---------|-----------|-----|-------|-------|
| Jan 5 | A | Main | 100 | 55.00 | 5,500 |
| Jan 10 | B | Main | 50 | 220.00 | 11,000 |
| Jan 15 | C | Secondary | 200 | 12.00 | 2,400 |

**Deliveries (Outgoing):**
| Date | Product | Warehouse | Qty | Cost | Total |
|------|---------|-----------|-----|------|-------|
| Jan 12 | A | Main | 30 | 50.00 | 1,500 |
| Jan 18 | C | Secondary | 50 | 10.00 | 500 |

**Expected Report (Jan 1-31, All Warehouses):**

| Product | Initial | Incoming | Outgoing | Final | Inc Amt | Out Amt | Final Amt |
|---------|---------|----------|----------|-------|---------|---------|-----------|
| A | 0 | 100 | 30 | 70 | 5,500 | 1,500 | 3,500 |
| B | 0 | 50 | 0 | 50 | 11,000 | 0 | 11,000 |
| C | 0 | 200 | 50 | 150 | 2,400 | 500 | 1,500 |

---

## ⚠️ Common Questions

### Q: Why are my amounts showing as 0?
**A:** Make sure:
- Products have cost prices set
- Purchase orders have unit prices
- Stock pickings are validated (not draft)

### Q: The quantities are right but amounts are wrong?
**A:** Check:
- Product cost in product form
- Purchase order unit prices
- Currency settings if using multiple currencies

### Q: Can I see the calculation breakdown?
**A:** Yes! Click the History button (📜) on any product row to see:
- Each individual movement
- Quantities and dates
- You can manually verify the math

### Q: What if I use different currencies?
**A:** The module uses the system currency. For multi-currency:
- Odoo converts automatically at time of receipt
- Amounts show in your company currency

---

## 📈 Real-World Use Cases

### Use Case 1: Monthly Inventory Value Report
**When:** End of each month  
**Purpose:** Know exact inventory value for financial statements  
**How:** Run report for full month, export to Excel, send to accounting

### Use Case 2: Cost Analysis
**When:** Reviewing supplier prices  
**Purpose:** See if purchase costs are increasing  
**How:** Compare incoming amounts across different periods for same products

### Use Case 3: Warehouse Audit
**When:** Physical inventory count  
**Purpose:** Verify system matches reality  
**How:** Run report per warehouse, compare final balances to physical count

### Use Case 4: Product Category Performance
**When:** Analyzing product lines  
**Purpose:** See movement and value by category  
**How:** Use category filter, group by category, review totals

---

## 🛠️ Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| No data appears | Check date range and warehouse filter |
| Amounts are zero | Verify product costs and PO prices |
| Wrong quantities | Confirm pickings are validated |
| Report is slow | Use shorter date range or specific warehouse |
| Can't find report | Go to Inventory → Reporting → Stock Report |

---

## 📚 Documentation Files

For more detailed information:
- **TESTING_MANUAL.md** - Complete testing procedures with 6 detailed test cases
- **UI_GUIDE.md** - Full user interface guide with screenshots descriptions
- **CHANGES.md** - Technical details of what changed in the code

---

## ✅ Deployment Checklist

Before going live:
- [ ] Test with sample data (use examples above)
- [ ] Verify amounts match your expectations
- [ ] Train key users on new features
- [ ] Run parallel reports (old vs new) to compare
- [ ] Document any issues found
- [ ] Get approval from accounting/management

---

## 🎓 5-Minute Training Script

**For training users quickly:**

1. "The stock report now shows actual purchase prices, not just standard costs"
2. "Go to Inventory → Reporting → Stock Report"
3. "Set your dates and click Generate Report"
4. "Look at Incoming Amount - this is what you really paid"
5. "Click the history button to see details"
6. "Use filters to find specific products or warehouses"
7. "Export to Excel if you need to share with others"

**Done!** User is ready to use the enhanced report.

---

## 📞 Need Help?

**Quick Help Path:**
1. Check this Quick Start guide
2. Review the Testing Manual for your specific scenario
3. Check Odoo system logs if errors occur
4. Contact your system administrator

**Happy Reporting!** 🎉

---

**Version:** 1.1  
**Last Updated:** January 14, 2026  
**Estimated Setup Time:** 15-30 minutes  
**Estimated Testing Time:** 1-2 hours
