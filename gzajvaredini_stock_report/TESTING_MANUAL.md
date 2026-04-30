# Stock Report Testing Manual
## Module: gzajvaredini_stock_report (Updated Version)

---

## Overview
This module generates stock reports showing:
- **Initial Balance** (quantity & amount)
- **Incoming** (quantity & amount from purchases, receipts)
- **Outgoing** (quantity & amount from deliveries, sales)
- **Final Balance** (quantity & amount)

The amounts use **actual transaction prices** from stock pickings when available.

**NEW:** You can now control whether internal transfers are included using the checkbox "შიდა გადაცემების გათვალისწინება".

---

## Testing Prerequisites

### 1. Module Installation
1. Go to **Apps** menu
2. Search for "Gza Stock Report"
3. Click **Install** or **Upgrade**
4. Wait for installation to complete

### 2. Required Setup
- At least **one warehouse** configured
- At least **one product** with inventory
- Products should have **cost price** set

---

## Test Scenarios

### Test Case 1: Basic Product Receipt (Incoming)

#### Setup Data:
| Field | Value |
|-------|-------|
| Product | Test Product A |
| Product Cost | 50.00 GEL |
| Warehouse | Main Warehouse |
| Quantity | 100 units |
| Date | 2026-01-10 |

#### Steps:
1. **Create a Product**
   - Go to: **Inventory → Products → Products**
   - Click **Create**
   - Fill in:
     - Name: `Test Product A`
     - Product Type: `Storable Product`
     - Cost: `50.00`
     - Unit of Measure: `Units`
   - Click **Save**

2. **Create Purchase Order**
   - Go to: **Purchase → Orders → Purchase Orders**
   - Click **Create**
   - Fill in:
     - Vendor: Select any vendor (create one if needed)
     - Order Date: `2026-01-10`
   - In **Order Lines**, click **Add a line**:
     - Product: `Test Product A`
     - Quantity: `100`
     - Unit Price: `50.00`
   - Click **Save**
   - Click **Confirm Order**

3. **Receive Products**
   - Click on **Receipt** smart button
   - Click **Validate**
   - Confirm the transfer

4. **Generate Stock Report (Without Internal Transfers)**
   - Go to: **Inventory → Reporting → Stock Report**
   - Set parameters:
     - Start Date: `2026-01-01`
     - End Date: `2026-01-15`
     - Warehouses: `Main Warehouse` (or leave empty for all)
     - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐
   - Click **Generate Report**

#### Expected Results:
| Field | Expected Value |
|-------|----------------|
| Initial Balance (Qty) | 0 |
| Initial Balance (Amount) | 0.00 |
| Incoming (Qty) | 100 |
| Incoming (Amount) | 5,000.00 |
| Outgoing (Qty) | 0 |
| Outgoing (Amount) | 0.00 |
| Final Balance (Qty) | 100 |
| Final Balance (Amount) | 5,000.00 |

---

### Test Case 2: Delivery Order (Outgoing)

#### Setup Data:
| Field | Value |
|-------|-------|
| Product | Test Product A (from Test Case 1) |
| Current Stock | 100 units |
| Delivery Quantity | 30 units |
| Date | 2026-01-12 |

#### Steps:
1. **Create Delivery**
   - Go to: **Inventory → Operations → Transfers**
   - Click **Create**
   - Fill in:
     - **Any Operation Type** (Receipts, Deliveries, Internal, etc.)
     - Source Location: `WH/Stock`
     - Destination Location: `Partners/Customers`
     - Scheduled Date: `2026-01-12`
   - In **Operations** tab, click **Add a line**:
     - Product: `Test Product A`
     - Demand: `30`
   - Click **Save**
   - Click **Check Availability**
   - Click **Validate**

2. **Generate Stock Report (Without Internal Transfers)**
   - Go to: **Inventory → Reporting → Stock Report**
   - Set parameters:
     - Start Date: `2026-01-01`
     - End Date: `2026-01-15`
     - Warehouses: `Main Warehouse`
     - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐
   - Click **Generate Report**

#### Expected Results:
| Field | Expected Value |
|-------|----------------|
| Initial Balance (Qty) | 0 |
| Incoming (Qty) | 100 |
| Incoming (Amount) | 5,000.00 |
| Outgoing (Qty) | 30 |
| Outgoing (Amount) | 1,500.00 |
| Final Balance (Qty) | 70 |
| Final Balance (Amount) | 3,500.00 |

---

### Test Case 3: Multiple Purchases at Different Prices

#### Setup Data:
| Receipt | Date | Quantity | Unit Price | Total |
|---------|------|----------|------------|-------|
| Receipt 1 | 2026-01-05 | 50 | 40.00 | 2,000.00 |
| Receipt 2 | 2026-01-10 | 80 | 45.00 | 3,600.00 |
| Receipt 3 | 2026-01-13 | 70 | 50.00 | 3,500.00 |

#### Steps:
1. **Create Test Product B**
   - Go to: **Inventory → Products → Products**
   - Click **Create**
   - Name: `Test Product B`
   - Product Type: `Storable Product`
   - Cost: `40.00`
   - Click **Save**

2. **Create Three Purchase Orders** (follow Test Case 1 steps for each):
   - PO 1: 50 units @ 40.00 on 2026-01-05
   - PO 2: 80 units @ 45.00 on 2026-01-10
   - PO 3: 70 units @ 50.00 on 2026-01-13
   - Receive all three

3. **Generate Stock Report**
   - Start Date: `2026-01-01`
   - End Date: `2026-01-15`
   - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐

#### Expected Results for Test Product B:
| Field | Expected Value |
|-------|----------------|
| Incoming (Qty) | 200 |
| Incoming (Amount) | 9,100.00 |
| Final Balance (Qty) | 200 |

---

### Test Case 4: Internal Transfer Between Warehouses (WITHOUT Checkbox)

#### Setup Data:
| Field | Value |
|-------|-------|
| Product | Test Product C |
| Source Warehouse | Main Warehouse |
| Destination Warehouse | Secondary Warehouse |
| Quantity | 25 units |
| Date | 2026-01-11 |

#### Steps:
1. **Create Second Warehouse** (if not exists)
   - Go to: **Inventory → Configuration → Warehouses**
   - Click **Create**
   - Name: `Secondary Warehouse`
   - Short Name: `WH2`
   - Click **Save**

2. **Create Product with Initial Stock**
   - Create `Test Product C` with cost 60.00
   - Add 100 units to Main Warehouse (using receipt from vendor)

3. **Create Internal Transfer**
   - Go to: **Inventory → Operations → Transfers**
   - Click **Create**
   - **Any Operation Type** (doesn't matter)
   - Source Location: `WH/Stock`
   - Destination Location: `WH2/Stock`
   - In Operations:
     - Product: `Test Product C`
     - Demand: `25`
   - Click **Validate**

4. **Generate Stock Report (WITHOUT Internal Transfers Checkbox)**
   - Start Date: `2026-01-01`
   - End Date: `2026-01-15`
   - Leave Warehouses empty (to see both)
   - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐

#### Expected Results (Internal Transfers NOT Included):
**Main Warehouse:**
| Field | Value |
|-------|-------|
| Incoming (Qty) | 100 (from vendor) |
| Outgoing (Qty) | 0 (internal transfer not counted) |
| Final Balance (Qty) | 75 (actual stock) |

**Secondary Warehouse:**
| Field | Value |
|-------|-------|
| Incoming (Qty) | 0 (internal transfer not counted) |
| Outgoing (Qty) | 0 |
| Final Balance (Qty) | 25 (actual stock) |

**Note:** When internal transfers are excluded, the incoming/outgoing don't show internal movements, but final balance reflects actual stock.

---

### Test Case 5: Internal Transfer Between Warehouses (WITH Checkbox) ⭐ NEW

#### Setup Data:
Same as Test Case 4

#### Steps:
1. Use the same setup as Test Case 4
2. **Generate Stock Report (WITH Internal Transfers Checkbox)**
   - Start Date: `2026-01-01`
   - End Date: `2026-01-15`
   - Leave Warehouses empty (to see both)
   - **შიდა გადაცემების გათვალისწინება: CHECKED** ☑

#### Expected Results (Internal Transfers Included):
**Main Warehouse:**
| Field | Value |
|-------|-------|
| Incoming (Qty) | 100 (from vendor) |
| Outgoing (Qty) | 25 (internal transfer counted) |
| Final Balance (Qty) | 75 |

**Secondary Warehouse:**
| Field | Value |
|-------|-------|
| Incoming (Qty) | 25 (internal transfer counted) |
| Outgoing (Qty) | 0 |
| Final Balance (Qty) | 25 |

**Note:** When internal transfers are included, both warehouses show the internal movement in their incoming/outgoing columns.

---

### Test Case 6: Date Range Filtering

#### Setup Data:
| Receipt | Date | Quantity |
|---------|------|----------|
| Receipt 1 | 2025-12-28 | 40 |
| Receipt 2 | 2026-01-05 | 60 |
| Receipt 3 | 2026-01-20 | 50 |

#### Steps:
1. Create `Test Product D` with cost 30.00
2. Create three receipts on different dates (as above)
3. **Test A: Report for January 1-15**
   - Start Date: `2026-01-01`
   - End Date: `2026-01-15`
   - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐
   
4. **Test B: Report for January 1-31**
   - Start Date: `2026-01-01`
   - End Date: `2026-01-31`
   - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐

#### Expected Results:

**Test A (Jan 1-15):**
| Field | Value |
|-------|-------|
| Initial Balance (Qty) | 40 (from Dec 28) |
| Incoming (Qty) | 60 (only Jan 5) |
| Final Balance (Qty) | 100 |

**Test B (Jan 1-31):**
| Field | Value |
|-------|-------|
| Initial Balance (Qty) | 40 (from Dec 28) |
| Incoming (Qty) | 110 (Jan 5 + Jan 20) |
| Final Balance (Qty) | 150 |

---

### Test Case 7: Category Filtering

#### Setup Data:
Create products in different categories:

| Product | Category | Initial Stock |
|---------|----------|---------------|
| Product Cat-A1 | Category A | 100 units |
| Product Cat-A2 | Category A | 80 units |
| Product Cat-B1 | Category B | 60 units |

#### Steps:
1. **Create Categories**
   - Go to: **Inventory → Configuration → Product Categories**
   - Create `Category A`
   - Create `Category B`

2. **Create Products**
   - Create 3 products as per table above
   - Assign appropriate categories
   - Add initial stock via receipts

3. **Generate Report with Category Filter**
   - Go to Stock Report wizard
   - Check **Filter by Category**
   - Select `Category A`
   - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐
   - Click **Generate Report**

#### Expected Results:
- Only products from Category A appear (Product Cat-A1, Product Cat-A2)
- Category B product should NOT appear

---

### Test Case 8: Complex Scenario with Internal Transfers ⭐ NEW

#### Setup Data:
| Movement | Date | From | To | Quantity | Type |
|----------|------|------|-----|----------|------|
| Purchase | Jan 5 | Vendor | WH1 | 100 | External |
| Internal Transfer | Jan 8 | WH1 | WH2 | 30 | Internal |
| Sale | Jan 10 | WH1 | Customer | 20 | External |
| Internal Transfer | Jan 12 | WH2 | WH1 | 10 | Internal |
| Sale | Jan 15 | WH2 | Customer | 15 | External |

#### Steps:
1. Create `Test Product E` with cost 100.00
2. Execute all movements as listed above
3. **Test A: Generate report WITHOUT internal transfers**
   - Date: Jan 1-31
   - **შიდა გადაცემების გათვალისწინება: UNCHECKED** ☐

4. **Test B: Generate report WITH internal transfers**
   - Date: Jan 1-31
   - **შიდა გადაცემების გათვალისწინება: CHECKED** ☑

#### Expected Results:

**Test A (Without Internal Transfers):**

**WH1:**
- Initial: 0
- Incoming: 100 (purchase only)
- Outgoing: 20 (sale only)
- Final: 60

**WH2:**
- Initial: 0
- Incoming: 0 (no external incoming)
- Outgoing: 15 (sale only)
- Final: 15

**Test B (With Internal Transfers):**

**WH1:**
- Initial: 0
- Incoming: 100 + 10 = 110 (purchase + transfer from WH2)
- Outgoing: 30 + 20 = 50 (transfer to WH2 + sale)
- Final: 60

**WH2:**
- Initial: 0
- Incoming: 30 (transfer from WH1)
- Outgoing: 10 + 15 = 25 (transfer to WH1 + sale)
- Final: 15

---

## Testing the "View History" Button

For any product in the report:
1. Click the **History** button (history icon)
2. You should see:
   - All stock moves for that product
   - In the selected date range
   - For the selected warehouse
   - With detailed quantities and dates

---

## Amount Calculation Verification

### How Amounts Are Calculated:

1. **Incoming Amount:**
   - Uses actual purchase price from PO if available
   - Falls back to product cost if no price_unit

2. **Outgoing Amount:**
   - Uses actual cost at time of delivery
   - Based on product cost price

3. **Formula Check:**
   ```
   Final Balance Amount = Initial Balance Amount + Incoming Amount - Outgoing Amount
   ```

### Manual Verification Example:
If you have:
- Initial: 50 units @ 40.00 = 2,000.00
- Incoming: 100 units @ 45.00 = 4,500.00
- Outgoing: 30 units @ 42.00 = 1,260.00
- Final: 120 units @ current cost

**Check**: 2,000 + 4,500 - 1,260 = 5,240.00

---

## Testing the Internal Transfers Checkbox

### Test Checklist:
- [ ] Checkbox appears in wizard form
- [ ] Checkbox label is "შიდა გადაცემების გათვალისწინება"
- [ ] Default value is UNCHECKED
- [ ] When UNCHECKED: Internal transfers do NOT appear in Incoming/Outgoing
- [ ] When CHECKED: Internal transfers DO appear in Incoming/Outgoing
- [ ] Final Balance is always correct regardless of checkbox state
- [ ] Checkbox works with warehouse filtering
- [ ] Checkbox works with category filtering
- [ ] Checkbox works with date filtering

---

## Common Issues & Troubleshooting

### Issue 1: No data appears in report
**Solution:**
- Check that products have stock movements
- Verify date range includes the movements
- Ensure warehouses are properly configured

### Issue 2: Amounts showing as 0.00
**Solution:**
- Check product has Cost Price set (Inventory tab)
- Verify purchases have unit prices
- Confirm stock moves are in 'Done' state

### Issue 3: Internal transfers not showing when checkbox is checked
**Solution:**
- Verify the movements are actually internal transfers (both locations are 'internal' type)
- Check date range includes the transfer dates
- Ensure transfers are validated

### Issue 4: Wrong warehouse data
**Solution:**
- Check warehouse filter in wizard
- Verify location paths are correct
- Ensure products are in internal locations

### Issue 5: Date filtering not working
**Solution:**
- Ensure date format is correct
- Check stock move dates (not scheduled dates)
- Verify timezone settings

---

## Advanced Testing

### Performance Test:
1. Create 1000+ products
2. Create movements for 6 months
3. Generate report - should complete in under 30 seconds
4. Test with both checkbox states

### Multi-warehouse Test:
1. Create 5 warehouses
2. Create transfers between them
3. Test with checkbox UNCHECKED - verify no internal transfers shown
4. Test with checkbox CHECKED - verify internal transfers shown
5. Verify each warehouse shows correct balances in both cases

### Concurrent User Test:
1. Have multiple users generate reports simultaneously
2. Some with checkbox checked, some unchecked
3. Each should get accurate data without conflicts

---

## Reporting Template

Use this template to document your test results:

```
Test Date: _____________
Tester Name: _____________
Test Case: _____________

| Check Item | Expected | Actual | Pass/Fail |
|------------|----------|--------|-----------|
| Initial Qty | | | |
| Initial Amt | | | |
| Incoming Qty | | | |
| Incoming Amt | | | |
| Outgoing Qty | | | |
| Outgoing Amt | | | |
| Final Qty | | | |
| Final Amt | | | |
| Internal Transfers Checkbox | ☐/☑ | | |

Notes: ___________________________________
```

---

## Quick Test Checklist

- [ ] Module installed/upgraded successfully
- [ ] Can access Stock Report from menu
- [ ] Wizard opens with default dates
- [ ] **NEW:** Internal transfers checkbox appears
- [ ] **NEW:** Checkbox default is UNCHECKED
- [ ] Can select warehouses
- [ ] Can select categories
- [ ] Report generates without errors (checkbox unchecked)
- [ ] Report generates without errors (checkbox checked)
- [ ] Quantities are accurate
- [ ] Amounts are accurate
- [ ] History button works
- [ ] Date filtering works
- [ ] Warehouse filtering works
- [ ] Category filtering works
- [ ] **NEW:** Internal transfers excluded when unchecked
- [ ] **NEW:** Internal transfers included when checked
- [ ] Report totals match individual lines
- [ ] Can export report to Excel/PDF

---

## Comparison Table: Checkbox States

| Scenario | Checkbox UNCHECKED ☐ | Checkbox CHECKED ☑ |
|----------|---------------------|-------------------|
| Purchase from vendor | Included | Included |
| Sale to customer | Included | Included |
| Internal transfer WH1→WH2 | NOT included | Included |
| Internal transfer WH2→WH1 | NOT included | Included |
| Final balance | Always correct | Always correct |
| Use case | Standard reports | Detailed tracking |

---

## Contact & Support

If you encounter issues during testing:
1. Check Odoo logs for errors
2. Verify database view was created properly
3. Test with fresh data
4. Document the exact steps to reproduce
5. Test with both checkbox states

**Module Version:** 1.1  
**Odoo Version:** 18.0  
**Last Updated:** January 2026  
**New Feature:** Internal Transfers Control
