# Auto-Import and Partner Management Changes

## Summary

Modified the TBC payment wizard to automatically:
1. ✅ Create bank statement lines during transaction fetch
2. ✅ Find or create appropriate journal based on account number
3. ✅ Find or create partners from transaction details

## Changes Made

### 1. Modified `wizards/tbc_payment_wizard.py`

**Added Methods:**

#### `_find_or_create_partner(record_data)`
Automatically finds or creates partners from transaction details.

**Logic:**
1. Determines transaction direction (debit/credit)
2. Selects appropriate partner (beneficiary for debit, sender for credit)
3. Search priority:
   - First: Search by VAT (INN)
   - Second: Search by name (case-insensitive)
   - Third: Create new partner if not found

**Partner Creation:**
- Uses beneficiary_details_name or sender_details_name for partner name
- Uses beneficiary_details_inn or sender_details_inn for VAT
- Sets company_type to 'company' if VAT exists, 'person' otherwise

#### `_find_or_create_journal(account_number)`
Finds or creates bank journal matching the fetched account number.

**Logic:**
1. Searches for existing journal linked to account number via res.partner.bank
2. Searches by journal code or name containing account identifier
3. Creates new journal if not found:
   - Name: "TBC {last 12 chars of account}"
   - Code: "BNK{last 6-8 chars}" (ensures uniqueness)
   - Type: bank

**Modified `fetch_transactions()` flow:**

```python
OLD FLOW:
1. Fetch from API
2. Create transaction records
3. User manually clicks "Create Statement Lines"

NEW FLOW:
1. Fetch from API
2. Find/create partner (auto)
3. Create transaction record
4. Find/create journal (auto)
5. Create statement line (auto)
```

### 2. Modified `models/models.py`

**Updated `_create_bank_statement_line()` method:**

```python
# OLD
def _create_bank_statement_line(self):
    journal = self._find_bank_journal()
    ...

# NEW
def _create_bank_statement_line(self, journal=None):
    if not journal:
        journal = self._find_bank_journal()
    ...
```

Now accepts optional journal parameter from wizard.

## Usage

### Before (Manual Steps):
```
1. Open TBC Payment Wizard
2. Select account and dates
3. Click "Fetch Transactions"
4. Wait for fetch to complete
5. Go to ბანკის ამონაწერი menu
6. Select transactions
7. Click "Create Statement Lines"
8. Manually assign partners if missing
```

### After (Automatic):
```
1. Open TBC Payment Wizard
2. Select account and dates
3. Click "Fetch Transactions"
✅ Done! Statement lines created with partners and journals
```

## Example Log Output

```
INFO: Starting transaction fetch process
INFO: Fetched 50 records from first page
INFO: Created new partner: შპს სანუსი (VAT: 123456789)
INFO: Found existing partner by VAT: შპს ბიზნესი (VAT: 987654321)
INFO: Created new bank journal: TBC 586405640GEL (Code: BNK405640)
INFO: Created transaction and statement line for DocumentKey: 12345
INFO: Transaction processing completed: 50 new records created, 0 duplicates skipped
```

## Partner Search Logic

### For Debit Transactions (Money Out):
- Partner = Beneficiary (the one we paid)
- Uses: beneficiary_details_name, beneficiary_details_inn

### For Credit Transactions (Money In):
- Partner = Sender (the one who paid us)
- Uses: sender_details_name, sender_details_inn

### Example:
```python
Transaction:
├─ entry_amount_debit: 500 GEL
├─ beneficiary_details_name: "შპს სანუსი"
├─ beneficiary_details_inn: "123456789"
└─ Result: Partner = "შპს სანუსი" (VAT: 123456789)

Transaction:
├─ entry_amount_credit: 1000 GEL
├─ sender_details_name: "შპს კლიენტი"
├─ sender_details_inn: "987654321"
└─ Result: Partner = "შპს კლიენტი" (VAT: 987654321)
```

## Journal Matching Logic

### Account Number Format:
`GE29BG0000000586405640GEL` (Georgian IBAN + currency)

### Search Priority:
1. Search res.partner.bank for exact match
2. Search journal by code/name containing account identifier
3. Create new journal with unique code

### Journal Naming:
- Name: Uses last 12 characters for readability
- Code: Uses last 6-8 characters (ensures uniqueness)

### Example:
```
Account: GE29BG0000000586405640GEL
→ Journal Name: "TBC 586405640GEL"
→ Journal Code: "BNK405640"
```

## Duplicate Prevention

Partners are NOT duplicated:
1. ✅ Search by VAT first (exact match)
2. ✅ Search by name second (case-insensitive)
3. ✅ Only create if both searches fail

Journals are NOT duplicated:
1. ✅ Search by bank account link
2. ✅ Search by code/name identifier
3. ✅ Ensure unique code when creating

## Benefits

✅ **Faster workflow**: No manual button clicking
✅ **Auto partner creation**: Partners created from transaction data
✅ **No duplicates**: Smart search prevents duplicate partners
✅ **Correct journals**: Transactions go to account-specific journals
✅ **Better organization**: Each bank account gets its own journal
✅ **Less errors**: Automated process reduces manual mistakes

## Technical Notes

- Partner search is case-insensitive for names
- VAT search is exact match
- Journal codes are guaranteed unique
- All operations are logged for debugging
- Errors are caught and logged without breaking the import
- Original "Create Statement Lines" button still works for edge cases
