from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env['account.payment.line'].search([('budget_line_id', '!=', False)])
    lines._compute_budget_line_display()


gross_amount = categories.get('GROSS', 0.0)
result = 0.0
pension_flag = employee.x_studio_pension

if gross_amount > 0:
    shegavati_limit = employee.x_studio_shegavati or 0.0
    pension_mult = 0.98

    year_start = employee.x_studio_start_date_1 or payslip.date_from.replace(month=1, day=1)

    previous_payslips = payslip.env['hr.payslip'].search([
        ('employee_id', '=', employee.id),
        ('date_from', '>=', year_start),
        ('id', '!=', payslip.id),
        ('state', 'in', ['done', 'paid'])
    ])

    shegavati_used = 0.0
    for prev in previous_payslips:
        if prev.struct_id.name == 'კომპანიის დაზღვევა':
            target_code = 'INSD'
        else:
            target_code = 'GROSS'

        lines = prev.line_ids.filtered(lambda l: l.code == target_code)
        shegavati_used += sum(lines.mapped('total'))

    total_ytd = shegavati_used + gross_amount
    left_shegavati = shegavati_limit - shegavati_used
    remainder = categories['INSD'] - left_shegavati
    remainder_grossed = remainder / 0.784
    left_grossed = left_shegavati / 0.98
    sum_left_rem = remainder_grossed + left_grossed
    sum_gr = sum_left_rem * 0.02
    k = sum_left_rem - sum_gr
    L_result = (k - left_shegavati) * 0, 2
    result = L_result

    # if total_ytd > shegavati_limit:
    #     if shegavati_used < shegavati_limit:
    #         taxable_excess = total_ytd - shegavati_limit
    #     else:
    #         taxable_excess = gross_amount
    #     if pension_flag:
    #         result = round((taxable_excess * pension_mult) * 0.20, 2)
    #     else:
    #         result = round((taxable_excess) * 0.20, 2)
    #
    # else:
    #     result = 0.0

gross_amount = categories.get('GROSS', 0.0)
result = 0.0
pension_flag = employee.x_studio_pension

if gross_amount > 0:
    shegavati_limit = employee.x_studio_shegavati or 0.0
    pension_mult = 0.98

    year_start = employee.x_studio_start_date_1 or payslip.date_from.replace(month=1, day=1)

    previous_payslips = payslip.env['hr.payslip'].search([
        ('employee_id', '=', employee.id),
        ('date_from', '>=', year_start),
        ('id', '!=', payslip.id),
        ('state', 'in', ['done', 'paid'])
    ])

    shegavati_used = 0.0
    for prev in previous_payslips:
        if prev.struct_id.name == 'კომპანიის დაზღვევა':
            target_code = 'INSD'
        else:
            target_code = 'GROSS'

        lines = prev.line_ids.filtered(lambda l: l.code == target_code)
        shegavati_used += sum(lines.mapped('total'))

    total_ytd = shegavati_used + gross_amount
    left_shegavati = shegavati_limit - shegavati_used
    remainder = categories['INSD'] - left_shegavati
    remainder_grossed = remainder / 0.784
    left_grossed = left_shegavati / 0.98
    sum_left_rem = remainder_grossed + left_grossed
    sum_gr = sum_left_rem * 0.02
    k = sum_left_rem - sum_gr
    L_result = (k - left_shegavati) * 0.2
    result = L_result

    # if total_ytd > shegavati_limit:
    #     if shegavati_used < shegavati_limit:
    #         taxable_excess = total_ytd - shegavati_limit
    #     else:
    #         taxable_excess = gross_amount
    #     if pension_flag:
    #         result = round((taxable_excess * pension_mult) * 0.20, 2)
    #     else:
    #         result = round((taxable_excess) * 0.20, 2)
    #
    # else:
    #     result = 0.0