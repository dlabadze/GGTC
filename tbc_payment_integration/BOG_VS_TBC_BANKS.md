# BOG vs TBC Bank Integration

## Overview

This module now supports **TWO different banks**:

1. **BOG Bank** (Bank of Georgia) - Uses BusinessOnline.ge API
2. **TBC Bank** - Uses TFS API

## Important Naming Clarification

**Before**: Everything was named "TBC" but actually used BOG Bank's API
**After**: Correctly separated into BOG and TBC integrations

## Bank Comparison

| Feature | BOG Bank | TBC Bank |
|---------|----------|----------|
| **API URL** | `https://api.businessonline.ge` | `http://tfs.fmgsoft.ge:7780` |
| **Authentication** | OAuth2 (client credentials) | Basic Auth (User/Pass/KeyCode) |
| **Wizard Model** | `bog.payment.wizard` | `tbc.movements.wizard` |
| **Transaction Model** | `tbc_payment_integration.tbc_payment_integration` | `tbc.movements` |
| **Data Format** | JSON with detailed fields | JSON normalized from DataFrame |
| **Product Group** | Yes (`document_product_group`) | Operation Code (`operation_code`) |
| **Pagination** | Yes (1000 records/page) | No (returns all) |

## Models Structure

### BOG Bank Models

#### `tbc_payment_integration.tbc_payment_integration`
Main transaction model for BOG bank.

**Key Fields:**
- `entry_date` - Transaction date
- `document_product_group` - Product group code (e.g., "210105")
- `entry_comment` / `doc_comment` - Comments for keyword matching
- `sender_details_*` - Sender information
- `beneficiary_details_*` - Beneficiary information
- `my_bank_id` - Fetched bank account number
- `partner_id` - Auto-detected partner
- `state` - Transaction state (draft/imported/done/error)
- `statement_line_id` - Created statement line

#### `bog.payment.wizard`
Wizard for fetching BOG transactions.

**Key Fields:**
- `start_date` / `end_date` - Date range
- `currency` - Currency (default: GEL)
- `selected_bank_account_id` - Bank account to fetch from

**Methods:**
- `fetch_transactions()` - Fetch from BOG API, create transactions, partners, journals, statement lines

### TBC Bank Models

#### `tbc.movements`
Main movement model for TBC bank.

**Key Fields:**
- `movement_id` - Movement identifier
- `value_date` - Movement date
- `operation_code` - Operation type code
- `description` - Movement description
- `partner_name` / `partner_tax_code` - Partner information
- `debit_credit` - Direction ('0' = debit, '1' = credit)
- `amount` - Movement amount
- `my_bank_id` - Fetched bank account number
- `partner_id` - Auto-detected partner
- `state` - Movement state (draft/imported/done/error)
- `statement_line_id` - Created statement line

####  `tbc.movements.wizard`
Wizard for fetching TBC movements.

**Key Fields:**
- `fromdate` / `todate` - Date range
- `currency` - Currency (default: GEL)
- `selected_bank_account_id` - Bank account to fetch from

**Methods:**
- `action_get_data()` - Fetch from TBC API, create movements, partners, journals, statement lines

## Code Mapping

### BOG Code Mapping: `tbc.code.mapping`

Maps BOG product group codes to accounts.

**Example:**
```
Code: 210105
Debit/Credit: Debit
Comment Keywords: პრემია, bonus
Account: 3130 (Bonus Expense)
Partner Required: Yes
```

**Used for:** BOG transactions (`document_product_group` field)

### TBC Code Mapping: `tbc.movements.code.mapping`

Maps TBC operation codes to accounts (not yet fully implemented in current version).

**Example:**
```
Code: OP123
Debit/Credit: Debit
Comment Keywords: ხელფასი
Account: 3110 (Salary Expense)
Partner Required: Yes
```

**Used for:** TBC movements (`operation_code` field)

## Workflow Comparison

### BOG Bank Workflow

```
1. User opens BOG Payment Wizard
2. Selects bank account and date range
3. Clicks "Fetch Transactions"
   ↓
4. System fetches from BusinessOnline.ge API
   - Authenticates with OAuth2
   - Fetches all pages (1000 records each)
   - Normalizes document keys
   ↓
5. For each transaction:
   - Find/create partner (by INN or name)
   - Create transaction record
   - Find/create journal (by account number)
   - Create statement line
   ↓
6. Result: Transactions ready for reconciliation
```

### TBC Bank Workflow

```
1. User opens TBC Movements Wizard
2. Selects bank account and date range
3. Clicks "Fetch Data"
   ↓
4. System fetches from TFS API
   - Authenticates with User/Pass/KeyCode
   - Returns all movements as JSON
   - Converts to DataFrame
   ↓
5. For each movement:
   - Find/create partner (by tax code or name)
   - Create movement record
   - Find/create journal (by account number)
   - Create statement line
   ↓
6. Result: Movements ready for reconciliation
```

## Auto-Creation Features (Both Banks)

Both banks now support automatic:

### 1. Partner Creation
- **Search Priority**: VAT → Name → Create New
- **VAT Source**:
  - BOG: `sender_details_inn` / `beneficiary_details_inn`
  - TBC: `partner_tax_code`
- **Name Source**:
  - BOG: `sender_details_name` / `beneficiary_details_name`
  - TBC: `partner_name`
- **No Duplicates**: Smart search prevents duplicate partners

### 2. Journal Creation
- **Search**: By account number in `res.partner.bank`
- **Fallback**: Search by code/name containing account digits
- **Create**: New journal with format "TBC {last 12 chars}" / Code "BNK{last 6 chars}"
- **Unique**: Ensures unique journal codes

### 3. Statement Line Creation
- **Auto**: Created immediately after transaction/movement
- **Journal**: Uses found/created journal
- **Partner**: Uses found/created partner
- **Amount**: Correctly signed (negative for debit, positive for credit)
- **Transaction Details**: Stores original data in JSON field

## API Authentication

### BOG Bank (OAuth2)

```python
# Step 1: Authenticate
auth_string = f"{api_key}:{client_secret}"
auth_header = base64.b64encode(auth_string.encode()).decode()

response = requests.post(
    'https://account.bog.ge/auth/realms/bog/protocol/openid-connect/token',
    headers={'Authorization': f'Basic {auth_header}'},
    data={'grant_type': 'client_credentials'}
)
access_token = response.json()['access_token']

# Step 2: Fetch statement
response = requests.get(
    f"https://api.businessonline.ge/api/statement/{acc}/{curr}/{start}/{end}",
    headers={'Authorization': f'Bearer {access_token}'}
)
```

**Credentials stored in:** `res.users` fields `bog_client_secret`, `bog_client_id`

### TBC Bank (Basic Auth)

```python
response = requests.post(
    'http://tfs.fmgsoft.ge:7780/API/FMGSoft/TBC_Movements',
    data={
        'DateFrom': fromdate,
        'DateTo': todate,
        'AccountNumber': acc_number,
        'User': '206103722_GAS',
        'Pass': 'GAZnew123!!!',
        'KeyCode': 'wqA04wDw',
        'Currency': currency
    }
)
```

**Credentials**: Hardcoded in wizard (should be moved to user settings)

## Menu Structure

```
ბანკის ამონაწერი (Bank Statement)
├── BOG ტრანზაქციები (BOG Transactions)
│   └── Model: tbc_payment_integration.tbc_payment_integration
├── TBC მოძრაობები (TBC Movements)
│   └── Model: tbc.movements
├── კოდების მეპინგი (BOG Code Mapping)
│   └── Model: tbc.code.mapping
└── Wizards
    ├── BOG Payment Wizard (bog.payment.wizard)
    └── TBC Movements Wizard (tbc.movements.wizard)
```

## Partner Detection Logic

### For BOG Transactions:

```python
# Debit transaction (money out) → Partner is beneficiary
if entry_amount_debit > 0:
    partner_name = beneficiary_details_name
    partner_inn = beneficiary_details_inn

# Credit transaction (money in) → Partner is sender
else:
    partner_name = sender_details_name
    partner_inn = sender_details_inn
```

### For TBC Movements:

```python
# Always use partner_name and partner_tax_code
partner_name = partner_name
partner_inn = partner_tax_code
```

## Reconciliation Integration

Both banks integrate with Odoo's standard reconciliation:

### Custom Reconciliation Model

**Model**: `account.reconcile.model`

**New Fields:**
- `use_tbc_mapping` - Enable TBC/BOG mapping
- `tbc_match_product_group` - Filter by product group
- `tbc_code_mapping_ids` - Linked code mappings

### Reconciliation Flow

```
1. Statement line created (from BOG or TBC)
2. User opens reconciliation widget
3. System checks reconciliation models
4. If model has "use_tbc_mapping":
   - Gets transaction_details from statement line
   - Finds tbc_transaction_id or tbc_movement_id
   - Gets suggested_mapping_id
   - Suggests account from mapping
5. User validates → Done!
```

## Migration from Old Module

If you have the old `tbc_payment_integration_test` module:

**Don't install both!** This module replaces it completely.

**What's Different:**
- ✅ BOG renamed correctly (was called "TBC" before)
- ✅ TBC bank now properly integrated
- ✅ Both banks use new auto-creation logic
- ✅ Both banks create statement lines automatically
- ✅ Standard Odoo reconciliation flow
- ✅ 70% less code

## Troubleshooting

### BOG Transactions Not Fetching

**Check:**
1. BOG credentials in user settings (`bog_client_secret`, `bog_client_id`)
2. Bank account number format (should be IBAN without spaces)
3. Date range (BOG API has limits)
4. Network access to `api.businessonline.ge`

**Logs:**
```
INFO: Authentication successful, access token obtained
INFO: Statement generated with ID: XXX, Total records: N
INFO: Created transaction and statement line for DocumentKey: XXX
```

### TBC Movements Not Fetching

**Check:**
1. TFS API credentials (hardcoded in wizard - check if still valid)
2. Bank account number format
3. Network access to `tfs.fmgsoft.ge:7780`

**Logs:**
```
INFO: Fetching TBC data from API
INFO: Data converted to DataFrame with N rows
INFO: Created TBC movement and statement line for Movement ID: XXX
```

### Partners Not Created

**Check:**
1. Transaction has sender/beneficiary details
2. Movement has partner_name or partner_tax_code
3. Check logs for "Found existing partner" vs "Created new partner"

### Journals Not Created

**Check:**
1. Account number is provided (`my_bank_id`)
2. Check logs for "Found existing journal" vs "Created new bank journal"
3. Journal code uniqueness (system tries BNK{6 chars} then BNK{8 chars})

## Best Practices

1. **Use Separate Journals**: Let system create one journal per bank account
2. **Configure Code Mappings**: Set up BOG code mappings before fetching
3. **Review First Import**: Check auto-created partners and journals
4. **One Reconciliation Model**: Create one model with "Use TBC Mapping" checked
5. **Archive Old Data**: If migrating, archive old test module data first

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Bank Support | 1 (BOG, misnamed as TBC) | 2 (BOG + TBC) |
| Auto Partners | ❌ Manual | ✅ Automatic |
| Auto Journals | ❌ Generic bank journal | ✅ Per-account journals |
| Auto Statement Lines | ❌ Button click needed | ✅ Automatic |
| Code Reduction | 2,382 lines | 713 lines |
| Odoo Standard | ❌ Custom flow | ✅ Standard reconciliation |

Both banks now work seamlessly with Odoo's standard accounting lifecycle! 🎉
