# View Updates for TBC Payment Integration v2.0

## Summary of View Changes

All view XML files have been updated to work with the new Odoo-standard reconciliation flow.

## Files Modified

### 1. `views/Tbc_view.xml`
**TBC Movements views updated:**

#### List View (`view_tbc_movements_list`):
- **Changed button**: `action_process_multiple_movements` → `action_create_statement_lines`
- **Button label**: "Process Selected Movements" → "Create Statement Lines"
- **Removed field**: `payment_id`
- **Added field**: `statement_line_id` (optional/hidden)
- **Removed fields**: `exchange_rate`, `operation_code_mapping` (don't exist in model)

#### Form View (`view_tbc_movements_form`):
- **Changed button**: `action_process_movement` → `action_create_statement_lines`
- **Button label**: "სისტემაში გატარება" → "Create Statement Line"
- **Added**: State field in statusbar
- **Removed field**: `payment_id`
- **Added field**: `statement_line_id`
- **Removed fields**: `exchange_rate`, `operation_code_mapping`

### 2. `views/views.xml`
**TBC Payment Integration views updated:**

#### Form View (`view_tbc_payment_integration_form`):
**Header changed from:**
```xml
<button name="action_process_transaction" string="სისტემაში გატარება"/>
```

**To:**
```xml
<button name="action_create_statement_lines" string="Create Statement Line"/>
<button name="action_open_reconciliation" string="Open Reconciliation"/>
<field name="state" widget="statusbar"/>
```

**Fields changed:**
- **Removed**: `payment_id`, `related_journal_entry_id`
- **Added**: `statement_line_id`, `partner_id`, `suggested_mapping_id`, `is_reconciled`

#### List View (`view_tbc_payment_integration_list`):
**Header changed from:**
```xml
<button name="action_process_multiple_transactions" string="Process Selected Transactions"/>
```

**To:**
```xml
<button name="action_create_statement_lines" string="Create Statement Lines"/>
```

**Fields changed:**
- **Removed**: `payment_id`, `related_journal_entry_id`
- **Added**: `partner_id`, `statement_line_id`, `is_reconciled`

#### Search View (`view_tbc_payment_integration_search`):
**Filters changed from:**
```xml
<filter name="filter_draft" domain="[('state','=','draft')]"/>
<filter name="filter_done" domain="[('state','=','done')]"/>
```

**To:**
```xml
<filter name="filter_draft" domain="[('state','=','draft')]"/>
<filter name="filter_imported" domain="[('state','=','imported')]"/>
<filter name="filter_reconciled" domain="[('state','=','reconciled')]"/>
<filter name="filter_error" domain="[('state','=','error')]"/>
```

#### Partner Selection Wizard:
- **Kept**: `tbc.partner.selection.wizard` view (backward compatibility)
- **Removed**: `tbc.movement.partner.selection.wizard` view (didn't exist in model)
- **Updated help text**: To reflect new flow

#### Code Mappings:
- **Removed**: All `tbc.movements.code.mapping` views/actions/menus
  - Model doesn't exist - users should use `tbc.code.mapping` instead
- **Kept**: All `tbc.code.mapping` views unchanged

## New State Values

The `state` field now uses these values:

| Old Value | New Value | Description |
|-----------|-----------|-------------|
| `draft` | `draft` | Not yet imported to statement |
| `done` | `imported` | Statement line created |
| N/A | `reconciled` | Fully reconciled |
| `error` | `error` | Error occurred |

## Button Actions Summary

| Old Action | New Action | Model |
|------------|------------|-------|
| `action_process_transaction` | `action_create_statement_lines` | tbc_payment_integration.tbc_payment_integration |
| `action_process_multiple_transactions` | `action_create_statement_lines` | tbc_payment_integration.tbc_payment_integration |
| `action_process_movement` | `action_create_statement_lines` | tbc.movements |
| `action_process_multiple_movements` | `action_create_statement_lines` | tbc.movements |
| N/A | `action_open_reconciliation` | tbc_payment_integration.tbc_payment_integration (NEW) |

## Removed Model References

These models were referenced in views but don't exist in the new models.py:

1. **`tbc.movement.partner.selection.wizard`** - Removed entirely
   - Use `tbc.partner.selection.wizard` instead

2. **`tbc.movements.code.mapping`** - Removed entirely
   - Use `tbc.code.mapping` instead (works for both transactions and movements)

## Field Visibility Changes

### TBC Payment Integration:
**Now visible:**
- `statement_line_id` - Link to created statement line
- `partner_id` - Auto-detected partner
- `suggested_mapping_id` - Suggested code mapping
- `is_reconciled` - Reconciliation status

**Hidden/Removed:**
- `payment_id` - Deprecated field
- `related_journal_entry_id` - Deprecated field

### TBC Movements:
**Now visible:**
- `statement_line_id` - Link to created statement line
- `state` - In statusbar

**Removed:**
- `payment_id` - Deprecated field
- `exchange_rate` - Field doesn't exist
- `operation_code_mapping` - Field doesn't exist

## Testing Checklist

After these view updates:

- [ ] TBC Payment Integration list view loads
- [ ] TBC Payment Integration form view loads
- [ ] "Create Statement Lines" button works (list)
- [ ] "Create Statement Line" button works (form)
- [ ] "Open Reconciliation" button works
- [ ] State statusbar displays correctly
- [ ] Search filters work for all states
- [ ] TBC Movements list view loads
- [ ] TBC Movements form view loads
- [ ] Partner selection wizard loads
- [ ] TBC Code Mapping views load

## Migration Notes

### For Existing Views:

If you have custom views or inherited views, update any references to:

1. **Old buttons** → New button names
2. **Old fields** (`payment_id`, `related_journal_entry_id`) → New fields
3. **Old state values** (`done`) → New state values (`imported`, `reconciled`)

### For Reports:

If you have custom reports using:
- `payment_id` → Use `statement_line_id` instead
- `state='done'` → Use `state in ('imported', 'reconciled')`

## Backward Compatibility

✅ **Preserved:**
- All existing transaction data visible
- Partner selection wizard still works
- Code mapping configuration unchanged
- All menu items preserved

⚠️ **Changed:**
- Button labels and actions
- State field values
- Field names for new functionality

❌ **Removed:**
- References to non-existent models
- Deprecated fields from views
- Movements-specific code mapping (use main TBC code mapping instead)
