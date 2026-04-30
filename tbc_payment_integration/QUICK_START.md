# TBC Payment Integration - Quick Start Guide

## 🚀 Quick Start (3 Steps)

### Step 1: Import Transactions
```
Accounting → TBC Payment Integration → Import Transactions
```
- Use TBC Payment Wizard for BOG API import
- Or use BOG Statement PDF Wizard for PDF import

### Step 2: Create Bank Statement Lines
```
Select transactions → Action → Create Statement Lines
```
- Transactions change from "Draft" to "Imported"
- Bank statement lines are created automatically
- Partners detected from INN automatically

### Step 3: Reconcile
```
Accounting → Bank → Reconciliation
```
- Your transactions appear as unreconciled lines
- Odoo suggests matches based on TBC mappings
- Click "Validate" to reconcile

## 📋 Setup Checklist

### One-Time Setup

- [ ] Configure TBC Code Mappings (if not already done)
  ```
  Accounting → Configuration → TBC Code Mappings
  ```

- [ ] Create Reconciliation Models (recommended)
  ```
  Accounting → Configuration → Reconciliation Models
  → Create New
  → Check "Use TBC Code Mapping"
  → Add your TBC mappings
  → Set matching conditions
  → Enable "Auto-validate" (optional)
  ```

- [ ] Configure BOG API credentials
  ```
  Settings → Users → Your User
  → BOG Client ID
  → BOG Client Secret
  ```

- [ ] Set up Bank Journals
  ```
  Accounting → Configuration → Journals
  → Create bank journals matching your account numbers
  ```

## 🔄 Daily Workflow

```
┌─────────────────────────┐
│ 1. Morning: Import      │
│    Yesterday's TBC      │
│    Transactions         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. Create Statement     │
│    Lines (Bulk Action)  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 3. Review Suggestions   │
│    in Reconciliation    │
│    Widget               │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. Validate/Adjust      │
│    and Post             │
└─────────────────────────┘
```

## 🎯 Common Tasks

### Import from BOG API
```
1. Go to: TBC Payment Wizard
2. Select: Company and Bank Account
3. Set: Date Range
4. Click: Fetch Transactions
5. Result: Transactions imported in "Draft" state
```

### Process Single Transaction
```
1. Open: Transaction form
2. Verify: Partner detected correctly
3. Check: Suggested mapping
4. Click: "Create Statement Lines"
5. Then: "Open Reconciliation" button
```

### Process Multiple Transactions
```
1. Select: Multiple transactions (list view)
2. Click: Action → Create Statement Lines
3. Go to: Accounting → Reconciliation
4. Review: All transactions at once
```

### Manual Partner Assignment
```
If partner not auto-detected:
1. Transaction form → Partner field
2. Or use: Partner Selection Wizard
3. Then: Create statement line
```

## 📊 Understanding States

| State | Meaning | Next Action |
|-------|---------|-------------|
| **Draft** | Just imported from bank | Create statement line |
| **Imported** | Statement line created | Reconcile in widget |
| **Reconciled** | Fully reconciled | Done! |
| **Error** | Something went wrong | Check logs, fix, retry |

## 🔍 Troubleshooting

### "No bank journal found"
**Fix**: Create a bank journal with name matching your account number

### "Partner not found"
**Fix**: Either:
- Create partner with correct VAT/INN code
- Or manually assign partner before creating statement line

### "Transaction already imported"
**Fix**: Check if statement line already exists. To re-import:
1. Set state back to "Draft"
2. Delete existing statement line
3. Try again

### Reconciliation not suggesting matches
**Fix**:
1. Check reconciliation model is active
2. Verify "Use TBC Code Mapping" is checked
3. Ensure matching conditions are correct
4. Check that TBC code mapping exists for the product group

## 💡 Tips & Tricks

### Bulk Processing
- Import entire month at once
- Create all statement lines in one action
- Review and validate in reconciliation widget

### Auto-Reconciliation
- Enable "Auto-validate" on reconciliation models
- Set strict matching conditions
- Review auto-reconciled entries daily

### Partner Management
- Keep VAT/INN fields up to date on partners
- System will auto-detect partners for future transactions
- Use partner categories for bulk mapping

### Mapping Strategy
- Start with broad mappings (empty comment)
- Add specific mappings for common transactions
- Use comment keywords for fine-grained matching

## 📈 Best Practices

1. **Import Daily**: Don't let transactions pile up
2. **Review Before Validation**: Check suggestions before confirming
3. **Keep Mappings Updated**: Add new product groups as needed
4. **Use Reconciliation Models**: Set up rules for common transactions
5. **Monitor Errors**: Check error state transactions regularly

## 🆘 Getting Help

### Check These First:
1. **README.md** - Full documentation
2. **MIGRATION_GUIDE.md** - What changed from v1.0
3. **Odoo Logs** - Detailed error messages
4. **Transaction Details** - Check all fields are populated

### Still Stuck?
1. Test with one transaction first
2. Check TBC code mapping configuration
3. Verify bank journal setup
4. Review reconciliation model conditions

## 📞 Support Resources

- **Module Version**: 2.0.0
- **Odoo Version**: 18.0
- **Module Path**: `custom_modules/tbc_payment_integration`
- **Backup Location**: `models/models.py.backup` (v1.0 code)

## ⚡ Quick Commands

### For Developers (via shell)

```python
# Import transactions
wizard = env['tbc.payment.wizard'].create({...})
wizard.fetch_transactions()

# Create statement lines
transactions = env['tbc_payment_integration.tbc_payment_integration'].search([('state', '=', 'draft')])
transactions.action_create_statement_lines()

# Find unreconciled lines
unreconciled = env['account.bank.statement.line'].search([
    ('is_reconciled', '=', False),
    ('tbc_transaction_id', '!=', False)
])
```

## 🎓 Learning Path

1. **Day 1**: Import 1 transaction, create statement line, reconcile manually
2. **Day 2**: Import 10 transactions, use bulk actions
3. **Day 3**: Create first reconciliation model
4. **Day 4**: Enable auto-validation for simple cases
5. **Day 5**: Process full month confidently!

---

**Remember**: The new flow is:
`Import → Create Lines → Reconcile → Done` ✅

No more manual journal entry creation! Let Odoo do the work. 🎉
