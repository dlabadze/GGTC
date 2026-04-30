## Request Report Wizard: `request.report.line.budget_amount`

This module generates an SQL view named `request_report_line` from the transient model `request.report.wizard`.

For each `product.category` (`pt.categ_id`) the view exposes:
- `budget_amount`: the planned/budgeted value for the selected `budgeting.request` (wizard field `budget_request_id`)
- `budget_quantity`: the budget quantity basis used to compute the amount
- `actual_amount` / `actual_quantity`: summed from `inventory_line` for the wizard-selected `department_id` and year

The implementation is done in `RequestReportWizard.action_generate_report()` by dynamically creating/updating the SQL view.

---

### 1) How `budget_qty_field` is chosen (depends on department)

Inside `action_generate_report()`, the wizard determines a department code `dep_code` from `department_id`:
- Prefer any `x_studio_*` field on the department whose value is one of:
  `["ცფ", "ცფს", "კს", "ჩფ", "ყუ", "დფ", "ოდო", "მეტ"]`
- If not found, try direct `department_id.dep_code` (if the field exists)
- If still not found, try to find any `inventory.request` with the same `department_id` and read its `dep_code`

Then the wizard maps `dep_code` to a budgeting quantity basis field:

| `dep_code` | SQL field used for quantities (`budget_qty_field`) |
|---|---|
| `ცფ` | `x_studio_float_field_607_1j3r255vi` |
| `ცფს` | `x_studio_float_field_971_1j3r2i8ah` |
| `კს` | `x_studio_float_field_3bu_1j3r2insu` |
| `ჩფ` | `x_studio_float_field_7rg_1j3r2j0fc` |
| `ყუ` | `x_studio_float_field_1p5_1j3r2j88f` |
| `დფ` | `x_studio_float_field_349_1j3r2jgm8` |
| `ოდო` | `x_studio_float_field_366_1j3r2jrui` |
| `მეტ` | `x_studio_float_field_9r_1j3r2kjpn` |

If none of the above matches (i.e. `dep_code` is missing), it falls back to:
- `budget_qty_field = quantity`

---

### 2) SQL definition of `budget_amount`

In the final `SELECT`, the view sets:

`budget_amount = COALESCE(bd.budget_amt, 0.0)`

Where `bd` is computed by a subquery grouped by category (`GROUP BY pt.categ_id`).

`bd.budget_amt` is calculated from `budgeting_line` for the selected wizard budget request (`WHERE bl.request_id = <wizard budget_request_id>`) and the category derived from:

`bl.product_id -> product_product pp -> product_template pt -> pt.categ_id`

Per category, the view aggregates `budgeting_line` as follows:

1. `budget_quantity` (quantity basis, still dependent on `budget_qty_field`):
   - `budget_quantity = SUM(COALESCE(bl.<budget_qty_field>, bl.quantity, 0.0))`

2. `unit_cost` is computed per `budgeting_line` record as an SQL expression (not a stored field):

```
unit_cost =
  x_studio_float_field_4nk_1j1fvng8q
  / (x_studio_float_field_38e_1j1ftullr + x_studio_float_field_8ss_1j1ftvflr)
```

3. `budget_amount` is the sum of per-line `budget_quantity_line * unit_cost_line`:

```
budget_amt = SUM(
  COALESCE(bl.<budget_qty_field>, bl.quantity, 0.0)
  *
  unit_cost
)
```

---

### 3) Notes about related fields (used in the same view)

Although not part of `budget_amount` itself, the view also computes `diff_amount` as:
- `diff_amount = budget_amount - actual_amount`

`actual_amount` is computed from `inventory_line` for:
- the wizard-selected `department_id`
- the year extracted from `budget_request_id.request_date` (inclusive `>= year_start`, exclusive `< year_end`)
- `ir.x_studio_selection_field_6ca_1j76p9boc = 'მარაგები'`
- `ir.september_request_id IS NULL`

