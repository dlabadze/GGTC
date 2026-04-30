# Migration Guide: TBC Payment Integration v1.0 → v2.0

## Summary of Changes

The `tbc_payment_integration` module has been completely reworked to follow Odoo's standard accounting reconciliation workflow instead of creating journal entries directly.

## What Was Changed

### ✅ Models Reworked (Class Names Kept)

1. **`TBCPaymentIntegration` (tbc_payment_integration.tbc_payment_integration)**
   - **Removed**: Direct journal entry creation logic
   - **Added**: Bank statement line creation method `_create_bank_statement_line()`
   - **Added**: New action `action_create_statement_lines()`
   - **Changed**: `state` field values (now: draft/imported/reconciled/error)
   - **Added**: `statement_line_id` field (link to bank statement line)
   - **Added**: Computed fields: `partner_id`, `suggested_mapping_id`, `is_reconciled`
   - **Deprecated**: `action_process_multiple_transactions()` (redirects to new method)
   - **Kept**: All existing transaction data fields

2. **`TBCCodeMapping` (tbc.code.mapping)**
   - **Kept**: All existing fields unchanged
   - **Added**: `reconcile_model_ids` M2M field (tracks which reconcile models use this mapping)
   - **Kept**: Logic for comment-based keyword matching

3. **`AccountReconcileModel` (account.reconcile.model)** - NEW EXTENSION
   - **Added**: `use_tbc_mapping` boolean field
   - **Added**: `tbc_code_mapping_ids` M2M field
   - **Added**: `tbc_match_product_group` char field
   - **Added**: Custom matching method `_get_tbc_mapping_match()`
   - **Overridden**: `_apply_lines_for_bank_widget()` to use TBC mappings

4. **`AccountBankStatementLine` (account.bank.statement.line)** - NEW EXTENSION
   - **Added**: `tbc_transaction_id` computed field
   - **Uses**: JSON `transaction_details` field to store TBC data

5. **`TBCMovements` (tbc.movements)**
   - **Kept**: All existing fields
   - **Added**: Similar statement line creation logic
   - **Added**: `action_create_statement_lines()` method

6. **`TBCPartnerSelectionWizard`, `CustomBank`, `AccountAccount`, `ResUsersExtended`**
   - **Kept**: Completely unchanged

### ❌ What Was Removed

1. **Removed 2000+ lines of direct journal entry creation logic**
   - Old `action_process_transaction()` method body
   - Direct `account.move` creation code
   - Custom payment creation logic
   - Manual reconciliation attempts
   - Complex partner finding in transaction processing

2. **Removed unused helper methods**:
   - `_prepare_payment_vals()`
   - `_get_bank_journal_for_transaction()` (replaced with `_find_bank_journal()`)
   - `_get_or_create_statement()`
   - `_find_existing_partner()` (now uses computed field)
   - `_get_bank_account_from_transaction_exact()`

## New Architecture

### Old Flow (v1.0):
```
TBC Transaction Import
    ↓
Direct Journal Entry Creation
    ↓
Payment Creation (optional)
    ↓
Bank Statement Line Creation (optional)
    ↓
Manual Reconciliation Attempts
```

### New Flow (v2.0):
```
TBC Transaction Import
    ↓
Bank Statement Line Creation
    ↓
Odoo Reconciliation Widget
    ↓
TBC Mapping-Based Matching
    ↓
Auto Reconciliation
```

## Benefits of New Architecture

1. **Odoo Standard Compliance**: Uses Odoo's built-in reconciliation lifecycle
2. **Better Audit Trail**: Full reconciliation history via Odoo models
3. **Less Code**: ~2000 lines removed, logic delegated to Odoo core
4. **More Flexible**: Users can use Odoo's reconciliation widget
5. **Easier Maintenance**: No custom reconciliation logic to maintain
6. **Partner Management**: Computed fields instead of complex finding logic

## Migration Steps

### For Developers

1. **Update dependencies** in `__manifest__.py`:
   ```python
   'depends': ['base', 'account', 'web', 'account_accountant'],
   ```

2. **Update any custom code calling old methods**:
   ```python
   # OLD
   transaction.action_process_transaction()

   # NEW
   transaction.action_create_statement_lines()
   ```

3. **Create reconciliation models** for automatic matching:
   - Go to Accounting → Configuration → Reconciliation Models
   - Create models with "Use TBC Code Mapping" checked
   - Configure matching rules

### For Users

1. **Existing data**: No migration needed - old transactions remain as-is
2. **New transactions**:
   - Import transactions (same as before)
   - Click "Create Statement Lines" action
   - Use Odoo's reconciliation widget to reconcile

3. **Set up reconciliation models** (one-time):
   - Configure automatic matching rules
   - Map TBC product groups to accounts
   - Enable auto-reconciliation if desired

## Backward Compatibility

### What Still Works:
- ✅ All existing TBC transactions (with `payment_id` or `related_journal_entry_id`)
- ✅ All TBC code mappings
- ✅ Partner detection from INN
- ✅ Comment-based keyword matching
- ✅ Import wizards (TBC Payment, Movements, BOG PDF)
- ✅ Old action methods (deprecated but functional)

### What Needs Updating:
- ⚠️ Custom code calling transaction processing methods
- ⚠️ Views/actions expecting direct journal entry creation
- ⚠️ Workflows expecting `payment_id` on new transactions

## Testing Checklist

After installing v2.0:

- [ ] Import TBC transactions via wizard
- [ ] Create statement lines from transactions
- [ ] Verify statement lines appear in reconciliation widget
- [ ] Check partner auto-detection works
- [ ] Test TBC code mapping suggestions
- [ ] Create and test reconciliation model
- [ ] Verify auto-reconciliation works
- [ ] Check legacy transactions still accessible
- [ ] Test with transactions requiring partner selection

## Rollback Plan

If issues occur:

1. **Module level**: Keep backup at `/models/models.py.backup`
2. **Data level**: Old transactions unaffected, new statement lines can be deleted
3. **Quick fix**: Revert to v1.0 code from backup

## Code Comparison

### Transaction Processing (v1.0 vs v2.0)

**v1.0 (OLD):**
```python
def action_process_transaction(self):
    # 500+ lines of code
    # - Find or create partner
    # - Determine account from mapping
    # - Create journal entry lines manually
    # - Post journal entry
    # - Create payment
    # - Create bank statement line
    # - Attempt reconciliation
    pass
```

**v2.0 (NEW):**
```python
def action_create_statement_lines(self):
    for transaction in self:
        statement_line = transaction._create_bank_statement_line()
        transaction.write({
            'statement_line_id': statement_line.id,
            'state': 'imported'
        })
    # Odoo handles the rest via reconciliation widget
```

### Reconciliation (v1.0 vs v2.0)

**v1.0 (OLD):**
```python
# Manual reconciliation in transaction processing
move_lines = [...]  # Manual creation
move.line_ids.reconcile()  # Custom reconciliation
```

**v2.0 (NEW):**
```python
# Extends Odoo's reconciliation model
class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_tbc_mapping_match(self, st_line, partner):
        # Odoo calls this during reconciliation
        # Returns matching candidates
        # Odoo creates entries automatically
        pass
```

## Performance Comparison

| Metric | v1.0 | v2.0 | Improvement |
|--------|------|------|-------------|
| Lines of Code | ~2,400 | ~650 | -73% |
| Transaction Processing | Direct DB writes | Odoo ORM | More reliable |
| Reconciliation | Custom logic | Odoo core | Better tested |
| Audit Trail | Custom fields | Odoo tables | Standard reports |

## Support

If you encounter issues during migration:

1. Check the backup at `models/models.py.backup`
2. Review the README.md for new usage patterns
3. Check Odoo logs for specific errors
4. Test with a single transaction first before bulk processing

## Questions?

- **Where did the journal entry creation go?** → Odoo creates it during reconciliation
- **How do I process transactions now?** → Create statement lines, then reconcile
- **Do I lose my custom mappings?** → No, they're used in reconciliation models
- **What about existing transactions?** → They remain unchanged and functional
- **Can I still auto-reconcile?** → Yes, via reconciliation models with auto-validate
