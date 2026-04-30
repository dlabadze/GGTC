# Quick Usage Guide for DOCX Templates

## Problem 1: False Values Showing as "False"

### ❌ Before (Problem):
In your DOCX template:
```
Customer: {{ docs.name }}
Mobile: {{ docs.mobile }}
Phone: {{ docs.phone }}
```

If `phone` field is empty (False), output shows:
```
Customer: John Doe
Mobile: +1234567890
Phone: False
```

### ✅ After (Solution):
In your DOCX template:
```
Customer: {{ docs.name }}
Mobile: {{ field1(docs.mobile) }}
Phone: {{ field1(docs.phone) }}
```

Output when phone is empty:
```
Customer: John Doe
Mobile: +1234567890
Phone: 
```

---

## Problem 2: Date Format is YYYY-MM-DD

### ❌ Before (Problem):
In your DOCX template:
```
Order Date: {{ docs.date_order }}
Delivery Date: {{ docs.date_delivery }}
```

Output shows:
```
Order Date: 2025-10-16
Delivery Date: 2025-10-20
```

### ✅ After (Solution):
In your DOCX template:
```
Order Date: {{ date1(docs.date_order) }}
Delivery Date: {{ date1(docs.date_delivery) }}
```

Output shows:
```
Order Date: 16/10/2025
Delivery Date: 20/10/2025
```

---

## Problem 3: Need Georgian Month Names

### ❌ Before (Problem):
In your DOCX template:
```
Contract Date: {{ docs.date_start }}
```

Output shows:
```
Contract Date: 2025-01-16
```

### ✅ After (Solution):
In your DOCX template:
```
Contract Date: {{ date2(docs.date_start) }}
```

Output shows:
```
Contract Date: 16 იანვარი 2025
```

**Different formats:**
```
{{ date2(docs.date_start, 'full') }}      → 16 იანვარი 2025
{{ date2(docs.date_start, 'short') }}     → 16 იანვარი
{{ date2(docs.date_start, 'month_year') }} → იანვარი 2025
```

---

## Recommended Approach: Use format_value()

For most fields, use `format_value()` which handles both problems:

```
Name: {{ docs.name }}
Email: {{ format_value(docs.email) }}
Phone: {{ format_value(docs.phone) }}
Website: {{ format_value(docs.website) }}
Birth Date: {{ format_value(docs.birthday) }}
Join Date: {{ format_value(docs.date_join) }}
```

This function:
- Converts False → empty string
- Formats dates → dd/mm/yyyy
- Keeps other values unchanged

---

## Common Use Cases

### 1. Partner/Customer Information
```
{{ docs.name }}
{{ format_value(docs.street) }}
{{ format_value(docs.street2) }}
{{ format_value(docs.city) }} {{ format_value(docs.zip) }}
{{ format_value(docs.country_id.name) }}

Phone: {{ format_value(docs.phone) }}
Mobile: {{ format_value(docs.mobile) }}
Email: {{ format_value(docs.email) }}
```

### 2. Sales Order
```
Order Number: {{ docs.name }}
Order Date: {{ date1(docs.date_order) }}
Customer: {{ docs.partner_id.name }}
Delivery Address: {{ format_value(docs.partner_shipping_id.street) }}
Expected Date: {{ date1(docs.expected_date) }}
```

### 3. Employee Information
```
Name: {{ docs.name }}
Employee ID: {{ docs.identification_id }}
Birth Date: {{ date2(docs.birthday) }}
Join Date: {{ date2(docs.date_join) }}
Department: {{ format_value(docs.department_id.name) }}
Manager: {{ format_value(docs.parent_id.name) }}
```

### 4. Invoice
```
Invoice: {{ docs.name }}
Date: {{ date2(docs.invoice_date) }}
Due Date: {{ date2(docs.invoice_date_due) }}
Customer: {{ docs.partner_id.name }}
Reference: {{ format_value(docs.ref) }}
```

### 5. Contract (Georgian format)
```
ხელშეკრულება №{{ docs.name }}
თარიღი: {{ date2(docs.date_contract, 'full') }}
პერიოდი: {{ date2(docs.date_start, 'short') }} - {{ date2(docs.date_end, 'short') }}
თვე: {{ date2(docs.date_start, 'month_year') }}
```

---

## Tips

1. **Always use format_value() or field1()** for optional fields
2. **Use date1()** specifically for date fields when you need dd/mm/yyyy format
3. **Don't use these functions** for required fields that will never be False
4. **Test your template** with records that have empty optional fields

---

## Problem 4: Accessing Records from One2many/Many2many Fields

### ❌ Before (Problem):
In your DOCX template:
```
{{ docs.employee_line_ids.employee_id.name }}
```

**Error:**
```
ValueError: Expected singleton: hr.employee(1, 831)
```

This happens because `employee_line_ids` contains multiple records, and you can't directly access fields on multiple records.

### ✅ After (Solution):

#### Option 1: Get Specific Record by Index
```
First employee: {{ get_record(docs.employee_line_ids, 0).employee_id.name }}
Second employee: {{ get_record(docs.employee_line_ids, 1).employee_id.name }}
Third employee: {{ get_record(docs.employee_line_ids, 2).employee_id.name }}
```

#### Option 2: Get First or Last Record
```
First employee: {{ get_first(docs.employee_line_ids).employee_id.name }}
Last employee: {{ get_last(docs.employee_line_ids).employee_id.name }}
```

#### Option 3: Join All Values into One String
```
All employees: {{ join_field(docs.employee_line_ids, 'employee_id.name') }}
```
Output: `John Doe, Jane Smith, Bob Johnson`

**With custom separator:**
```
All employees: {{ join_field(docs.employee_line_ids, 'employee_id.name', ' | ') }}
```
Output: `John Doe | Jane Smith | Bob Johnson`

#### Option 4: Count Records
```
Total employees: {{ count_records(docs.employee_line_ids) }}
```

---

### Real-World Examples

#### Example 1: Access First 3 Lines
```
Employee 1: {{ get_record(docs.employee_line_ids, 0).employee_id.name }} - {{ get_record(docs.employee_line_ids, 0).position }}
Employee 2: {{ get_record(docs.employee_line_ids, 1).employee_id.name }} - {{ get_record(docs.employee_line_ids, 1).position }}
Employee 3: {{ get_record(docs.employee_line_ids, 2).employee_id.name }} - {{ get_record(docs.employee_line_ids, 2).position }}
```

#### Example 2: Show All Names on One Line
```
Team Members: {{ join_field(docs.employee_line_ids, 'employee_id.name', ', ') }}
```

#### Example 3: Conditional Display
```
{% if count_records(docs.employee_line_ids) > 0 %}
Lead Employee: {{ get_first(docs.employee_line_ids).employee_id.name }}
Total Team Size: {{ count_records(docs.employee_line_ids) }}
{% endif %}
```

#### Example 4: Sale Order Lines
```
First Product: {{ get_first(docs.order_line).product_id.name }}
First Quantity: {{ get_record(docs.order_line, 0).product_uom_qty }}
First Price: {{ get_record(docs.order_line, 0).price_unit }}

All Products: {{ join_field(docs.order_line, 'product_id.name') }}
Total Lines: {{ count_records(docs.order_line) }}
```

---

## Quick Reference

| Use Case | Function | Example |
|----------|----------|---------|
| Optional text field | `field1()` | `{{ field1(docs.street2) }}` |
| Date (dd/mm/yyyy) | `date1()` | `{{ date1(docs.date) }}` |
| Date (Georgian months) | `date2()` | `{{ date2(docs.date) }}` |
| Any field (auto-detect) | `format_value()` | `{{ format_value(docs.field) }}` |
| Required field | No function needed | `{{ docs.name }}` |
| Get specific record | `get_record()` | `{{ get_record(docs.lines, 0).name }}` |
| Get first record | `get_first()` | `{{ get_first(docs.lines).name }}` |
| Get last record | `get_last()` | `{{ get_last(docs.lines).name }}` |
| Join all field values | `join_field()` | `{{ join_field(docs.lines, 'name') }}` |
| Count records | `count_records()` | `{{ count_records(docs.lines) }}` |

