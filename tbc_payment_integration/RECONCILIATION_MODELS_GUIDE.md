# TBC Reconciliation Models - Configuration Guide

## Overview

The module extends Odoo's standard reconciliation models with TBC-specific fields, allowing you to automatically match and reconcile TBC bank transactions based on product group codes and your custom TBC code mappings.

## New Fields Added to Reconciliation Models

When you open a reconciliation model (Accounting → Configuration → Reconciliation Models), you'll see a new section called **"TBC Bank Integration"** with these fields:

### 1. **Use TBC Mapping** (Boolean)
- **Type**: Toggle switch
- **Purpose**: Enable TBC bank integration for this reconciliation model
- **When to use**: Check this for any reconciliation model that should process TBC bank transactions

### 2. **Match Product Group** (Char)
- **Type**: Text field
- **Purpose**: Match only TBC transactions with this specific product group code
- **Example**: `210105` (for salary payments)
- **Leave empty**: To match all TBC transactions regardless of product group
- **Visible**: Only when "Use TBC Mapping" is checked

### 3. **TBC Code Mappings** (Many2many)
- **Type**: Tags widget
- **Purpose**: Link TBC code mappings that will be used to create counterpart entries
- **Filtered by**: Product group (shows only mappings matching the product group above)
- **Visible**: Only when "Use TBC Mapping" is checked

## How It Works

### Workflow:
```
1. TBC transaction imported → Statement line created
2. Odoo reconciliation widget opens
3. Reconciliation model checks if TBC integration enabled
4. If enabled, checks product group match (if specified)
5. Uses TBC code mapping to determine account
6. Creates counterpart entry automatically
7. Auto-validates if configured
```

## Step-by-Step Configuration

### Example 1: Auto-Reconcile Salary Payments

**Scenario**: Automatically reconcile all salary payments (product group 210105)

1. Go to: **Accounting → Configuration → Reconciliation Models**
2. Click **Create**
3. Fill in:
   - **Name**: "TBC Salary Payments"
   - **Rule Type**: "Suggestion of counterpart values"
   - **Match Journals**: Select your bank journal(s)
   - **Match Nature**: "Payments" (or leave empty)
   - **Match Label**: Leave empty or add keywords like "salary, ხელფასი"

4. In **TBC Bank Integration** section:
   - ✅ Check **Use TBC Mapping**
   - **Match Product Group**: `210105`
   - **TBC Code Mappings**: Select your salary-related TBC mappings

5. Set **Auto-validate**: ✅ (if you want automatic reconciliation)
6. **Save**

### Example 2: General TBC Transaction Matching

**Scenario**: Match all TBC transactions using their mappings

1. Go to: **Accounting → Configuration → Reconciliation Models**
2. Click **Create**
3. Fill in:
   - **Name**: "TBC All Transactions"
   - **Rule Type**: "Suggestion of counterpart values"
   - **Match Journals**: Select your bank journal(s)

4. In **TBC Bank Integration** section:
   - ✅ Check **Use TBC Mapping**
   - **Match Product Group**: (leave empty to match all)
   - **TBC Code Mappings**: Select all your TBC mappings

5. Set **Auto-validate**: ❌ (review before confirming)
6. **Save**

### Example 3: Specific Utility Payments

**Scenario**: Auto-reconcile utility payments with product group 340120

1. Create reconciliation model:
   - **Name**: "TBC Utility Payments"
   - **Rule Type**: "Suggestion of counterpart values"
   - **Match Amount**: Between 50 and 5000 (typical utility range)

2. In **TBC Bank Integration** section:
   - ✅ Check **Use TBC Mapping**
   - **Match Product Group**: `340120`
   - **TBC Code Mappings**: Select utility expense mappings

3. Set **Auto-validate**: ✅
4. **Save**

## Accessing TBC Reconciliation Models

### Method 1: From Main Menu
```
ბანკის ამონაწერი → TBC Reconciliation Models
```
This shows only reconciliation models with TBC integration enabled.

### Method 2: From Accounting
```
Accounting → Configuration → Reconciliation Models
```
Then filter or search for models with "Use TBC Mapping" checked.

## Testing Your Reconciliation Model

### Test Process:
1. **Import a test transaction** (via TBC Payment Wizard)
2. **Create statement line** (click "Create Statement Lines")
3. **Open reconciliation widget** (Accounting → Bank → Reconciliation)
4. **Check suggestions**: Your TBC reconciliation model should suggest a match
5. **Verify account**: Check that the suggested account matches your TBC mapping
6. **Validate**: Confirm the reconciliation

### What to Check:
- ✅ Model appears in suggestions
- ✅ Correct account suggested (from TBC mapping)
- ✅ Correct partner assigned (if applicable)
- ✅ Description/label matches transaction
- ✅ Auto-validation works (if enabled)

## Common Configurations

### 1. By Transaction Type

**Income Transactions:**
```
Name: TBC Income
Match Nature: Receipts
Match Product Group: (leave empty or specific code)
Auto-validate: Yes (if confident)
```

**Expense Transactions:**
```
Name: TBC Expenses
Match Nature: Payments
Match Product Group: (leave empty or specific code)
Auto-validate: No (review first)
```

### 2. By Amount Range

**Small Transactions:**
```
Name: TBC Small Transactions
Match Amount: Lower than 1000
Auto-validate: Yes
```

**Large Transactions:**
```
Name: TBC Large Transactions
Match Amount: Greater than 10000
Auto-validate: No (always review)
```

### 3. By Partner

**Known Partners:**
```
Name: TBC Known Partners
Match Partner: Yes
Match Partner IDs: Select specific partners
Auto-validate: Yes
```

**Unknown Partners:**
```
Name: TBC Unknown
Match Partner: No
Auto-validate: No (assign partner first)
```

## Priority and Order

Odoo applies reconciliation models in sequence. Configure priority by:

1. **Most specific first**: Product group + amount + partner
2. **Medium specific**: Product group only
3. **General last**: All TBC transactions

Set **Sequence** field to control order (lower number = higher priority).

## Troubleshooting

### Model Not Suggesting Matches

**Check:**
1. ✅ "Use TBC Mapping" is checked
2. ✅ Transaction is from TBC (has `tbc_transaction_id`)
3. ✅ Product group matches (if specified)
4. ✅ TBC code mapping exists for product group
5. ✅ Journal match condition met
6. ✅ Amount conditions met (if specified)

### Wrong Account Suggested

**Fix:**
1. Check TBC code mapping for that product group
2. Verify debit/credit direction matches
3. Check comment keywords in mapping
4. Review multiple mappings for same product group

### Auto-validation Not Working

**Check:**
1. ✅ "Auto-validate" is checked on model
2. ✅ All matching conditions are met
3. ✅ Account and partner are valid
4. ✅ No validation errors (check Odoo logs)

## Best Practices

### 1. Start Conservative
- ❌ Don't enable auto-validate immediately
- ✅ Test with manual review first
- ✅ Enable auto-validate after confidence builds

### 2. Use Specific Models
- ✅ Create separate models for different transaction types
- ✅ Use product group matching for precision
- ✅ Set appropriate amount ranges

### 3. Monitor and Adjust
- 📊 Review reconciliation results weekly
- 🔧 Adjust matching conditions as needed
- 📝 Update TBC code mappings based on new transaction types

### 4. Document Your Models
- 📝 Use clear, descriptive names
- 📋 Add notes in model description
- 🗂️ Organize by transaction category

## Advanced: Multiple Mappings

If you have multiple TBC code mappings for the same product group:

```
Product Group: 210105
Mapping 1: Keywords: "ხელფასი" → Salary Expense
Mapping 2: Keywords: "პრემია" → Bonus Expense
Mapping 3: No keywords → General Salary Expense
```

The system will:
1. Try to match comment keywords first
2. Fall back to no-keyword mapping
3. Use first available if multiple matches

## Quick Reference

| Field | Required | Purpose |
|-------|----------|---------|
| Use TBC Mapping | Yes | Enable TBC integration |
| Match Product Group | No | Filter by product group code |
| TBC Code Mappings | No* | Mappings to use for account selection |

*Not required but recommended for best results

## Example Complete Setup

Here's a complete setup for a typical Georgian business:

```
1. TBC Salaries (210105)
   - Auto-validate: Yes
   - Product Group: 210105
   - Mapping: Salary expense accounts

2. TBC Utilities (340120)
   - Auto-validate: Yes
   - Product Group: 340120
   - Mapping: Utility expense accounts

3. TBC Vendor Payments (210103)
   - Auto-validate: No
   - Product Group: 210103
   - Mapping: Trade payables

4. TBC Customer Receipts (210104)
   - Auto-validate: No
   - Product Group: 210104
   - Mapping: Trade receivables

5. TBC Other (catch-all)
   - Auto-validate: No
   - Product Group: (empty)
   - Mapping: All mappings
```

## Getting Help

### Logs to Check:
```python
# In Odoo shell
env['account.reconcile.model'].search([('use_tbc_mapping', '=', True)])
```

### Debug Mode:
Enable debug mode to see:
- Which reconciliation models are triggered
- Match scores and priorities
- Why a model matched or didn't match

---

**Remember**: TBC reconciliation models work **on top of** Odoo's standard reconciliation. You still have full control and can manually adjust any suggestions!
