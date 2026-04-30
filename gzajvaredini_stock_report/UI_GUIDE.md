# Stock Report - User Interface Guide

## Quick Start Guide

### 📍 How to Access the Stock Report

**Navigation Path:**
```
Main Menu → Inventory → Reporting → Stock Report
```

Or search in the top search bar: "Stock Report"

---

## Using the Stock Report Wizard

### Step 1: Open the Report Wizard

When you click on "Stock Report", you'll see a popup window with these fields:

### Step 2: Configure Report Parameters

#### 🗓️ Date Selection
- **Start Date (საწყისი თარიღი):** 
  - Default: 30 days ago from today
  - Click on the field to open calendar picker
  - Example: `2026-01-01`

- **End Date (საბოლოო თარიღი):**
  - Default: Today
  - Example: `2026-01-31`

#### 🏭 Warehouse Selection
- **Warehouses (საწყობები):**
  - Leave empty = Show all warehouses
  - Click to select one or more warehouses
  - Multi-select: Click multiple items
  - Remove: Click X on selected tag

#### 📂 Category Filtering
- **Filter by Category (კატეგორიებით გაფილტვრა):**
  - Checkbox - Enable/Disable category filter
  - When checked, "Categories" field appears below

- **Categories (კატეგორიები):**
  - Only visible when filter is enabled
  - Select product categories to filter
  - Includes sub-categories automatically

### Step 3: Generate Report
- Click **"Generate Report (რეპორტის გენერაცია)"** button
- Report opens in new window

---

## Understanding the Report View

### Column Descriptions

| Column Name (English) | Column Name (Georgian) | Description |
|----------------------|------------------------|-------------|
| Product | პროდუქცია | Product name |
| Product Code | პროდუქციის კოდი | Internal reference code |
| Category | კატეგორია | Product category |
| Warehouse | საწყობი | Warehouse location |
| Unit | ერთეული | Unit of measure |
| Initial Balance | - | Stock at start date (Quantity) |
| Incoming | - | Products received (Quantity) |
| Outgoing | - | Products delivered (Quantity) |
| Final Balance | - | Current stock (Quantity) |
| Initial Balance Amount | - | Value at start (Amount) |
| Incoming Amount | - | Value of receipts (Amount) |
| Outgoing Amount | - | Value of deliveries (Amount) |
| Final Balance Amount | - | Current stock value (Amount) |

### Column Totals
- All numeric columns show **totals at the bottom**
- Totals update automatically when filtering

### 🔍 Search and Filter

At the top of the report, you can use:

#### Quick Filters:
- **With Stock:** Show only products with current stock > 0
- **Out of Stock:** Show only products with 0 stock
- **With Movement:** Show only products that had incoming or outgoing movement

#### Advanced Search:
Click on any column name to add custom filters:
- `=` Equal to
- `>` Greater than
- `<` Less than
- `>=` Greater or equal
- `<=` Less or equal
- `contains` Text search

**Example Searches:**
```
Final Balance > 100          (Show products with more than 100 units)
Incoming Amount >= 5000      (Show products with incoming value ≥ 5000)
Product contains "Cable"     (Search for cables)
Warehouse = "Main Warehouse" (Filter by warehouse)
```

---

## Special Features

### 📜 History Button

Each product row has a **History** button (clock icon):
- Click to see detailed stock movement history
- Shows all transfers for that product
- Filtered by your selected date range and warehouse
- Displays:
  - Date and time of movement
  - Source location
  - Destination location
  - Quantity moved
  - Reference document

### 📊 Grouping Data

You can group data by clicking the **Group By** button:
- Group by Warehouse
- Group by Category
- Group by Product
- Multiple levels of grouping supported

**How to group:**
1. Click search icon (magnifying glass)
2. Click "Group By"
3. Select field to group by
4. Data reorganizes automatically

### 📥 Export Options

Export report data:
1. Select rows (checkbox on left) or leave unselected for all
2. Click **Action** (⚙️ gear icon)
3. Choose:
   - **Export** → Excel/CSV format
   - **Print** → PDF format

---

## Example Use Cases

### Use Case 1: Monthly Stock Review
**Goal:** See all stock movements for January

**Steps:**
1. Open Stock Report
2. Set dates: `2026-01-01` to `2026-01-31`
3. Leave warehouse empty (all warehouses)
4. Click "Generate Report"
5. Review incoming and outgoing totals

### Use Case 2: Warehouse-Specific Audit
**Goal:** Audit only Main Warehouse

**Steps:**
1. Open Stock Report
2. Set desired date range
3. Select only "Main Warehouse"
4. Click "Generate Report"
5. Check final balances match physical count

### Use Case 3: Category-Based Inventory
**Goal:** See stock for "Electronics" category

**Steps:**
1. Open Stock Report
2. Set date range
3. Check "Filter by Category"
4. Select "Electronics"
5. Click "Generate Report"
6. Review all electronics products

### Use Case 4: Find Products with High Incoming
**Goal:** Find products with large purchases

**Steps:**
1. Generate report for desired period
2. Click on "Incoming Amount" column
3. Add filter: `Incoming Amount > 10000`
4. Sort descending (click column header)
5. Export results if needed

### Use Case 5: Zero Stock Items
**Goal:** Find products that are out of stock

**Steps:**
1. Generate report
2. Click "Out of Stock" filter
3. Review products with 0 final balance
4. Plan restocking accordingly

---

## Tips & Tricks

### ⚡ Speed Tips
- **Narrow date range** for faster reports (1-3 months)
- **Select specific warehouse** instead of all
- **Use category filter** for large product databases

### 🎯 Accuracy Tips
- Always **validate stock pickings** before running report
- Ensure **purchase orders are confirmed** and received
- Check **product costs are set** for accurate amounts
- Verify **warehouse configurations** are correct

### 🔄 Refresh Data
If you made changes and report doesn't reflect them:
1. Close the report window
2. Open Stock Report wizard again
3. Re-generate with same parameters
4. New data should appear

### 📱 Shortcut Keys
- `Alt + C` → Close window
- `Alt + S` → Search
- `Ctrl + Click` → Multi-select in dropdown

---

## Understanding Amount Calculations

### How Incoming Amount is Calculated:
```
Incoming Amount = Sum of (Quantity × Purchase Price)
```
- Uses actual purchase prices from purchase orders
- If no purchase price, uses product cost

### How Outgoing Amount is Calculated:
```
Outgoing Amount = Sum of (Quantity × Product Cost)
```
- Uses product cost price at time of delivery

### Balance Formula:
```
Final Balance = Initial Balance + Incoming - Outgoing
Final Amount = Initial Amount + Incoming Amount - Outgoing Amount
```

### Example Calculation:
```
Initial Balance: 50 units @ 40 GEL = 2,000 GEL
Incoming: 100 units @ 45 GEL = 4,500 GEL
Outgoing: 30 units @ 40 GEL = 1,200 GEL
Final Balance: 120 units
Final Amount: 2,000 + 4,500 - 1,200 = 5,300 GEL
```

---

## Troubleshooting Common Issues

### ❌ Problem: No data appears
**Solutions:**
- Check date range includes stock movements
- Verify warehouse filter is not too restrictive
- Ensure products have stock in selected warehouse
- Confirm stock pickings are validated (not draft)

### ❌ Problem: Amounts show as 0.00
**Solutions:**
- Go to product form → Inventory tab
- Set "Cost" field
- For purchases, ensure unit price is set in PO
- Re-validate stock pickings if needed

### ❌ Problem: Wrong quantities shown
**Solutions:**
- Check product unit of measure
- Verify stock moves are in "Done" state
- Ensure locations belong to selected warehouse
- Check for canceled or draft transfers

### ❌ Problem: History button shows no data
**Solutions:**
- Ensure stock moves exist for the product
- Check date range in report parameters
- Verify warehouse selection
- Confirm transfers are validated

### ❌ Problem: Report takes too long
**Solutions:**
- Reduce date range (shorter period)
- Select specific warehouses only
- Use category filter to limit products
- Run report during off-peak hours

---

## Report Maintenance

### Regular Actions:
- **Weekly:** Generate and save reports for record
- **Monthly:** Review and reconcile with accounting
- **Quarterly:** Archive historical reports
- **Yearly:** Clean up old data if needed

### Best Practices:
1. ✅ Always set specific date ranges
2. ✅ Document any discrepancies found
3. ✅ Cross-check with physical inventory
4. ✅ Export important reports for backup
5. ✅ Train all users on proper usage

---

## Visual Guide

### Report Layout:
```
┌─────────────────────────────────────────────────────┐
│  🔍 Search  📊 Filters  ⚙️ Actions  📥 Export       │
├─────────────────────────────────────────────────────┤
│ Product | Code | Warehouse | Initial | Incoming... │
├─────────────────────────────────────────────────────┤
│ Product A | P001 | Main WH | 50 | 100 | ... | 📜  │
│ Product B | P002 | Main WH | 30 | 80  | ... | 📜  │
│ Product C | P003 | Sec WH  | 20 | 50  | ... | 📜  │
├─────────────────────────────────────────────────────┤
│ TOTALS:                  100  230  ...              │
└─────────────────────────────────────────────────────┘
```

### Wizard Layout:
```
┌───────────────────────────────────────┐
│  რეპორტი საწყობების მიხედვით        │
├───────────────────────────────────────┤
│  📅 Start Date:  [2026-01-01    ▼]   │
│  📅 End Date:    [2026-01-31    ▼]   │
│                                       │
│  🏭 Warehouses:  [Main Warehouse  x]  │
│                 [+ Add More]          │
│                                       │
│  ☐ Filter by Category                │
│  📂 Categories:  [              ▼]   │
│                                       │
├───────────────────────────────────────┤
│  [რეპორტის გენერაცია]  [გაუქმება]   │
└───────────────────────────────────────┘
```

---

## Need Help?

If you're stuck:
1. ⚙️ Check Odoo documentation
2. 📧 Contact system administrator
3. 📞 Reach out to support team
4. 📚 Review this guide again

**Remember:** This report is a powerful tool for inventory management. Take time to understand each feature for best results!

---

**Document Version:** 1.0  
**Last Updated:** January 2026  
**Compatible with:** Odoo 18
