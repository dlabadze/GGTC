# Batch Upload Plan for RS.GE Integration

## Current Upload Methods Analysis

### 1. **SaleOrder** (sale.order) - Line 17
- `button_send_soap_request()` (Line 364) - Uploads waybill from Sale Order
- Status check: `self.combined_invoice_id`

### 2. **AccountMove** (account.move) - Line 371
- `button_send_soap_request()` (Line 705) - Uploads waybill from Invoice
- Status check: `self.invoice_id`

### 3. **AccountMove** (account.move) - Line 1704  
- `button_factura()` (Line 2273) - Uploads factura from Invoice
- Status check: `self.factura_num`

### 4. **StockMove** (stock.picking) - Line 817
- `button_send_soap_request()` (Line 1286) - Uploads waybill from Delivery Order
- `button_send_soap_request_return()` (Line 1691) - Uploads return waybill
- Status check: `self.invoice_id`

### 5. **ResPartner** (res.partner) - Line 714 & 758
- `button_send_soap_request()` (Line 717) - Gets buyer_tin
- `button_get_name_from_tin()` - Gets company name from TIN

---

## Proposed Batch Upload Strategy

### **Option A: Modify Existing Buttons** (Simplest)
Change existing methods to handle multiple records automatically.

#### Pros:
- No new UI changes needed
- Works immediately from list view
- Users can select multiple records and click existing button

#### Cons:
- Single button must handle both single and batch
- All records fail if one fails (current behavior)

---

### **Option B: Separate Batch Methods** (Recommended)
Create separate batch-specific methods with better error handling.

#### Implementation Plan:

#### 1. **AccountMove - Waybill Batch** 
```python
def button_send_soap_request_batch(self):
    """Upload waybills for multiple invoices"""
    success = []
    errors = []
    skipped = []
    
    for record in self:
        try:
            if record.invoice_id:
                skipped.append(f"{record.name}: ზედნადები უკვე ატვირთულია")
                continue
            
            record.send_soap_request()
            success.append(record.name)
            self.env.cr.commit()  # Save each success
            
        except Exception as e:
            errors.append(f"{record.name}: {str(e)}")
            self.env.cr.rollback()
            
    return self._show_batch_result(success, errors, skipped, 'ზედნადები')
```

#### 2. **AccountMove - Factura Batch**
```python
def button_factura_batch(self):
    """Upload facturas for multiple invoices"""
    success = []
    errors = []
    skipped = []
    
    for record in self:
        try:
            if record.factura_num:
                skipped.append(f"{record.name}: ფაქტურა უკვე ატვირთულია")
                continue
            
            record.faqturebi()
            success.append(record.name)
            self.env.cr.commit()
            
        except Exception as e:
            errors.append(f"{record.name}: {str(e)}")
            self.env.cr.rollback()
            
    return self._show_batch_result(success, errors, skipped, 'ფაქტურა')
```

#### 3. **StockPicking - Waybill Batch**
```python
def button_send_soap_request_batch(self):
    """Upload waybills for multiple deliveries"""
    success = []
    errors = []
    skipped = []
    
    for record in self:
        try:
            if record.invoice_id:
                skipped.append(f"{record.name}: ზედნადები უკვე ატვირთულია")
                continue
            
            record.send_soap_request()
            success.append(record.name)
            self.env.cr.commit()
            
        except Exception as e:
            errors.append(f"{record.name}: {str(e)}")
            self.env.cr.rollback()
            
    return self._show_batch_result(success, errors, skipped, 'ზედნადები')
```

#### 4. **Helper Method** (Add to both AccountMove and StockPicking)
```python
def _show_batch_result(self, success, errors, skipped, doc_type):
    """Show batch processing results"""
    messages = []
    
    if success:
        messages.append(f"✓ წარმატებული ({len(success)}):\n  " + "\n  ".join(success))
    
    if skipped:
        messages.append(f"⊘ გამოტოვებული ({len(skipped)}):\n  " + "\n  ".join(skipped))
    
    if errors:
        messages.append(f"✗ შეცდომები ({len(errors)}):\n  " + "\n  ".join(errors))
    
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': f'{doc_type} - ბათჩ ატვირთვა',
            'message': '\n\n'.join(messages),
            'type': 'success' if errors else 'info',
            'sticky': True,
        }
    }
```

---

### **Option C: Smart Auto-Detect** (Most User Friendly)
Modify existing buttons to automatically detect single vs batch.

```python
def button_send_soap_request(self):
    # Auto-detect batch mode
    if len(self) > 1:
        return self._process_batch()
    else:
        return self._process_single()
```

---

## UI Changes Needed

### **For Option B (Separate Batch Methods):**

#### 1. **account_move.xml** - Add batch actions
```xml
<!-- Add to tree view -->
<record id="view_invoice_tree_batch_actions" model="ir.ui.view">
    <field name="name">account.move.tree.batch</field>
    <field name="model">account.move</field>
    <field name="inherit_id" ref="account.view_invoice_tree"/>
    <field name="arch" type="xml">
        <tree position="inside">
            <header>
                <button name="button_send_soap_request_batch" 
                        string="RS ზედნადები (ბათჩი)" 
                        type="object" 
                        class="btn-primary"/>
                <button name="button_factura_batch" 
                        string="RS ფაქტურა (ბათჩი)" 
                        type="object" 
                        class="btn-primary"/>
            </header>
        </tree>
    </field>
</record>
```

#### 2. **stockpickinginherit.xml** - Add batch actions
```xml
<!-- Add to tree view -->
<record id="view_picking_tree_batch_actions" model="ir.ui.view">
    <field name="name">stock.picking.tree.batch</field>
    <field name="model">stock.picking</field>
    <field name="inherit_id" ref="stock.vpicktree"/>
    <field name="arch" type="xml">
        <tree position="inside">
            <header>
                <button name="button_send_soap_request_batch" 
                        string="RS ზედნადები (ბათჩი)" 
                        type="object" 
                        class="btn-primary"/>
            </header>
        </tree>
    </field>
</record>
```

---

## Recommended Approach: **Option C (Smart Auto-Detect)**

### Advantages:
1. **No UI changes needed** - existing buttons work for both
2. **Better UX** - users don't need to remember different buttons
3. **Backward compatible** - existing workflows unchanged
4. **Progressive enhancement** - add batch capability to existing code

### Implementation Steps:

1. **Add batch detection to each button method:**
   ```python
   def button_send_soap_request(self):
       if len(self) == 1:
           # Single record - original behavior with page refresh
           return self._process_single_waybill()
       else:
           # Multiple records - batch mode
           return self._process_batch_waybills()
   ```

2. **Move current logic to _process_single methods**

3. **Add _process_batch methods with error handling**

4. **No view changes required!**

---

## Error Handling Strategy

### Current Issues:
1. ❌ `raise UserError()` stops entire batch
2. ❌ No transaction control between records
3. ❌ No progress feedback for long batches
4. ❌ `self.env.cr.commit()` in middle of processing

### Proposed Fixes:
1. ✅ Try-except per record
2. ✅ Commit after each successful record
3. ✅ Rollback only failed record
4. ✅ Collect all results and show summary
5. ✅ Log all errors for debugging

---

## Testing Checklist

- [ ] Test single record upload (backward compatibility)
- [ ] Test batch of 2 records (both succeed)
- [ ] Test batch with 1 failure (partial success)
- [ ] Test batch where all fail (error message)
- [ ] Test batch with already uploaded records (skip)
- [ ] Test network timeout handling
- [ ] Test RS.GE API errors
- [ ] Test invalid credentials
- [ ] Test missing required fields

---

## Rollout Plan

### Phase 1: Add batch capability to AccountMove
- [ ] Implement waybill batch method
- [ ] Implement factura batch method
- [ ] Test with 5-10 records

### Phase 2: Add batch capability to StockPicking
- [ ] Implement waybill batch method
- [ ] Test with deliveries

### Phase 3: Add UI indicators
- [ ] Optional: Add batch progress bar
- [ ] Optional: Add batch history log

### Phase 4: Optimization (if needed)
- [ ] Parallel SOAP requests (advanced)
- [ ] Batch API calls (if RS.GE supports)
- [ ] Queue system for large batches (100+ records)

---

## Current Workflow Summary

### Account Move (Invoice):
1. User clicks "RS- ზედნადები" → uploads waybill → creates combined_invoice_id
2. User clicks "RS - ფაქტურა" → uploads factura → adds factura_num to combined_invoice_id

### Stock Picking (Delivery):
1. User clicks "RS ზედნადები" → uploads waybill → creates combined_invoice_id
2. Updates related sale order with combined_invoice_id

### Key Fields:
- `invoice_id` - RS waybill ID
- `invoice_number` - RS waybill number  
- `factura_num` - RS factura ID
- `get_invoice_id` - RS factura series/number
- `combined_invoice_id` - Link to combined.invoice.model

---

## My Recommendation

**Use Option C (Smart Auto-Detect)** because:

1. ✅ Works immediately - just select multiple records and click existing button
2. ✅ No training needed - users already know the buttons
3. ✅ No view updates required
4. ✅ Backward compatible
5. ✅ Better error handling than current implementation
6. ✅ Each record commits independently
7. ✅ Clear summary of results

**Implementation:** 
- Modify 3 methods (2 in AccountMove, 1 in StockPicking)
- Add 1 helper method for result display
- Total: ~150 lines of code
- Time: ~2 hours including testing

Would you like me to proceed with this approach?

