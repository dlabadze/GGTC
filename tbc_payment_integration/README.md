# TBC Payment Integration v2.0

## Overview

This module has been completely reworked to use Odoo's standard bank reconciliation workflow. It now follows the standard Odoo accounting lifecycle instead of creating journal entries directly.

## New Workflow (v2.0)

```
1. Import TBC Transactions (from BOG API)
   ↓
2. Create Bank Statement Lines (NEW!)
   ↓
3. Odoo Reconciliation Widget
   ↓
4. Auto-match using TBC Code Mappings
   ↓
5. Create Reconciled Journal Entries
```

## Key Changes from v1.0

### What Changed:
- **No more direct journal entry creation** - Transactions now create bank statement lines
- **Standard Odoo reconciliation** - Uses Odoo's built-in reconciliation widget
- **Custom reconciliation models** - TBC mappings integrated into Odoo's reconcile models
- **Better audit trail** - Full reconciliation history via Odoo's standard models

### What Stayed the Same:
- **TBC Code Mapping** - Your existing code mappings still work
- **Partner detection** - Auto-detects partners from INN/tax codes
- **Comment-based matching** - Keyword matching in comments
- **All class names** - No breaking changes to model names

## Usage Guide

### 1. Import TBC Transactions

Use the existing wizards to import transactions from BOG API:
- **TBC Payment Wizard** (`tbc.payment.wizard`)
- **TBC Movements Wizard** (`tbc.movements.wizard`)
- **BOG Statement PDF Wizard** (`bog.statement.pdf.wizard`)

### 2. Create Bank Statement Lines

After importing transactions, select them and click:
```
Action → Create Statement Lines
```

This will:
- Create a bank statement line for each transaction
- Set transaction state to "Imported"
- Store TBC transaction data in JSON field
- Auto-detect partner from INN

### 3. Reconcile Transactions

#### Option A: Use Odoo's Reconciliation Widget
1. Go to **Accounting → Bank → Reconciliation**
2. Your TBC transactions will appear as unreconciled lines
3. Odoo will suggest matches based on:
   - TBC code mappings
   - Product group codes
   - Partner matching
   - Invoice matching

#### Option B: Use TBC Reconciliation Models
1. Go to **Accounting → Configuration → Reconciliation Models**
2. Create a new model with:
   - **Use TBC Code Mapping** = checked
   - **TBC Code Mappings** = select your mappings
   - **Match Product Group** = specific TBC product group (optional)
3. Set matching conditions (amount, label, partner, etc.)
4. Enable **Auto-validate** if you want automatic reconciliation

### 4. View Reconciliation Status

From TBC transaction form:
- **Status** field shows: Draft → Imported → Reconciled
- **Statement Line** button opens the bank statement line
- **Is Reconciled** checkbox shows reconciliation status

## TBC Code Mapping Configuration

Your existing mappings work with the new system:

```python
# Example: Salary Payment Mapping
Code: 210105
Debit/Credit: Debit
Account: Salary Expense Account
Partner Required: Yes
Comment Keywords: ხელფასი, salary, wage
```

When a transaction with product group "210105" is imported:
1. System creates bank statement line
2. Auto-detects partner from beneficiary INN
3. Suggests mapping based on comment keywords
4. Reconciliation model creates counterpart entry with mapped account

## API for Developers

### Create Statement Line Programmatically

```python
# From TBC transaction
transaction = self.env['tbc_payment_integration.tbc_payment_integration'].browse(transaction_id)
statement_line = transaction._create_bank_statement_line()

# Or use the action
transaction.action_create_statement_lines()
```

### Access TBC Data from Statement Line

```python
# From bank statement line
st_line = self.env['account.bank.statement.line'].browse(line_id)
tbc_data = st_line.transaction_details
tbc_transaction_id = tbc_data.get('tbc_transaction_id')
product_group = tbc_data.get('product_group')
sender_inn = tbc_data.get('sender_inn')
```

### Custom Reconciliation Model

Extend `account.reconcile.model` to add custom logic:

```python
class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_tbc_mapping_match(self, st_line, partner):
        # Custom matching logic here
        # Check TBC transaction details
        # Return match candidates
        pass
```

## Migration from v1.0

### Existing Data:
- Old transactions (with `payment_id` or `related_journal_entry_id`) remain unchanged
- Legacy methods `action_process_multiple_transactions()` redirect to new flow
- No data migration needed

### New Transactions:
- Use `action_create_statement_lines()` instead of `action_process_transaction()`
- Reconcile via Odoo's widget instead of direct posting
- Check `statement_line_id` instead of `payment_id`

### Deprecation Warnings:
```python
# DEPRECATED (still works but logs warning)
transaction.action_process_multiple_transactions()

# NEW WAY
transaction.action_create_statement_lines()
```

## Troubleshooting

### "No bank journal found"
- Check that journal exists for the account number in transaction
- Journal must be of type "bank"
- Match by journal name or bank_account_id.acc_number

### "Transaction already imported"
- Transaction state is already "imported"
- Check `statement_line_id` field
- To re-import: set state back to "draft"

### "Partner not found"
- Partner with matching VAT/INN doesn't exist
- Create partner first with correct tax code
- Or use Partner Selection Wizard

### Reconciliation not auto-matching
1. Check reconciliation model is active
2. Verify "Use TBC Code Mapping" is checked
3. Ensure TBC code mapping exists for product group
4. Check matching conditions (journal, amount, etc.)

## Technical Details

### Database Schema Changes
- **New fields on `tbc_payment_integration.tbc_payment_integration`:**
  - `state` - changed values (draft/imported/reconciled/error)
  - `statement_line_id` - link to bank statement line
  - `partner_id` - computed from INN
  - `suggested_mapping_id` - computed from product group
  - `is_reconciled` - related from statement_line

- **New model extensions:**
  - `account.reconcile.model` - added TBC-specific fields
  - `account.bank.statement.line` - added `tbc_transaction_id` computed field

### JSON Data Structure

`transaction_details` field on bank statement line:
```json
{
  "tbc_transaction_id": 123,
  "document_key": "1234567",
  "product_group": "210105",
  "sender_inn": "123456789",
  "sender_name": "Company Name",
  "beneficiary_inn": "987654321",
  "beneficiary_name": "Employee Name"
}
```

## Support

For issues or questions:
1. Check Odoo logs for detailed error messages
2. Verify TBC code mappings are configured correctly
3. Test with a single transaction first
4. Review reconciliation model matching conditions

## License

Same as Odoo Community Edition (LGPL-3)
