# BOG Bank Rename Summary

## Overview

The module was incorrectly using "TBC" naming for BOG Bank (Bank of Georgia) integration. This has been corrected.

## Changes Made

### Python Files

#### `wizards/tbc_payment_wizard.py`

**Class Renamed:**
```python
# OLD
class TbcPaymentWizard(models.TransientModel):
    _name = 'tbc.payment.wizard'
    _description = 'TBC Payment Integration Wizard'

# NEW
class BogPaymentWizard(models.TransientModel):
    _name = 'bog.payment.wizard'
    _description = 'BOG Payment Integration Wizard'
```

**Note:** The file name `tbc_payment_wizard.py` was NOT renamed to avoid breaking imports. It still contains both BOG and TBC wizards.

### XML Files

#### `views/wizard_view.xml`

**View Record ID:** `view_tbc_payment_wizard_form` → `view_bog_payment_wizard_form`

```xml
<!-- OLD -->
<record id="view_tbc_payment_wizard_form" model="ir.ui.view">
    <field name="name">tbc.payment.wizard.form</field>
    <field name="model">tbc.payment.wizard</field>
    <field name="arch" type="xml">
        <form string="TBC Payment Integration">

<!-- NEW -->
<record id="view_bog_payment_wizard_form" model="ir.ui.view">
    <field name="name">bog.payment.wizard.form</field>
    <field name="model">bog.payment.wizard</field>
    <field name="arch" type="xml">
        <form string="BOG Payment Integration">
```

#### `views/views.xml`

**1. View Record:**
```xml
<!-- OLD -->
<record id="view_tbc_payment_wizard_form" model="ir.ui.view">
    <field name="name">tbc.payment.wizard.form</field>
    <field name="model">tbc.payment.wizard</field>

<!-- NEW -->
<record id="view_bog_payment_wizard_form" model="ir.ui.view">
    <field name="name">bog.payment.wizard.form</field>
    <field name="model">bog.payment.wizard</field>
```

**2. Action Record:**
```xml
<!-- OLD -->
<record id="action_tbc_payment_wizard" model="ir.actions.act_window">
    <field name="name">TBC Payment Wizard</field>
    <field name="res_model">tbc.payment.wizard</field>
    <field name="view_id" ref="view_tbc_payment_wizard_form"/>

<!-- NEW -->
<record id="action_bog_payment_wizard" model="ir.actions.act_window">
    <field name="name">BOG Payment Wizard</field>
    <field name="res_model">bog.payment.wizard</field>
    <field name="view_id" ref="view_bog_payment_wizard_form"/>
```

**3. Access Rights:**
```xml
<!-- OLD -->
<record id="access_tbc_payment_wizard_user" model="ir.model.access">
    <field name="name">tbc.payment.wizard access for user</field>
    <field name="model_id" ref="model_tbc_payment_wizard"/>

<!-- NEW -->
<record id="access_bog_payment_wizard_user" model="ir.model.access">
    <field name="name">bog.payment.wizard access for user</field>
    <field name="model_id" ref="model_bog_payment_wizard"/>
```

### JavaScript Files

#### `static/src/js/button.js`

**Function Update:**
```javascript
// OLD
onOpenPaymentWizardClick() {
    this.actionService.doAction({
        res_model: 'tbc.payment.wizard',
        name: 'Open Payment Wizard',

// NEW
onOpenPaymentWizardClick() {
    this.actionService.doAction({
        res_model: 'bog.payment.wizard',  // BOG Bank wizard
        name: 'Open BOG Payment Wizard',
```

## What Was NOT Changed

### File Names
- `wizards/tbc_payment_wizard.py` - Kept as is (contains both BOG and TBC wizards)
- All other file names remain unchanged

### Model Names That Are Correct
- `tbc.movements` - Correct (this is actual TBC Bank)
- `tbc.movements.wizard` - Correct (this is actual TBC Bank)
- `tbc.code.mapping` - Kept for backward compatibility (used by BOG transactions)
- `tbc_payment_integration.tbc_payment_integration` - Kept for backward compatibility (BOG transactions)

### Imports
- `wizards/__init__.py` - No change needed (imports module, not class)

## Verification Checklist

✅ Python class renamed: `TbcPaymentWizard` → `BogPaymentWizard`
✅ Model name updated: `tbc.payment.wizard` → `bog.payment.wizard`
✅ All XML view records updated
✅ All XML action records updated
✅ Access rights records updated
✅ JavaScript references updated
✅ No breaking changes to existing data

## Migration Notes

**For existing installations:**

1. **Module Upgrade Required**: Run module upgrade after pulling these changes
2. **No Data Migration Needed**: The transaction model name didn't change
3. **View References**: All views now correctly point to `bog.payment.wizard`
4. **JavaScript**: Button will now open correct BOG wizard

**Breaking Changes:** None - this is purely a naming correction

## Summary Table

| Item | Old Value | New Value | Status |
|------|-----------|-----------|--------|
| Python Class | `TbcPaymentWizard` | `BogPaymentWizard` | ✅ Updated |
| Model Name | `tbc.payment.wizard` | `bog.payment.wizard` | ✅ Updated |
| View Record ID | `view_tbc_payment_wizard_form` | `view_bog_payment_wizard_form` | ✅ Updated |
| Action ID | `action_tbc_payment_wizard` | `action_bog_payment_wizard` | ✅ Updated |
| Access Rights ID | `access_tbc_payment_wizard_user` | `access_bog_payment_wizard_user` | ✅ Updated |
| Form Title | "TBC Payment Integration" | "BOG Payment Integration" | ✅ Updated |
| JS res_model | `'tbc.payment.wizard'` | `'bog.payment.wizard'` | ✅ Updated |

## Testing Recommendations

After upgrade, test:

1. ✅ Open BOG Payment Wizard from menu
2. ✅ Click "Import BOG Transactions" button in list view
3. ✅ Fetch transactions successfully
4. ✅ Verify auto-creation of partners/journals/statement lines
5. ✅ Check that TBC Movements Wizard still works (separate bank)

## Bank Clarification

| Bank | API | Model Name | Wizard Class |
|------|-----|------------|--------------|
| **BOG** (Bank of Georgia) | `api.businessonline.ge` | `bog.payment.wizard` | `BogPaymentWizard` |
| **TBC** (TBC Bank) | `tfs.fmgsoft.ge` | `tbc.movements.wizard` | `TBCMovementsWizard` |

Now correctly separated! 🎉
