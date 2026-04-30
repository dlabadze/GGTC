from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardSelectBudgetRequest(models.TransientModel):
    _name = 'wizard.select.budget.request'
    _description = 'Select Budget Request Wizard'

    budget_request_id = fields.Many2one(
        'budgeting.request',
        string='Budget Request',
        required=True,
        help='Select the budget request where budgeting lines will be created'
    )

    def action_create_budgeting_lines(self):
        if not self.budget_request_id:
            raise UserError(_("Please select a budget request."))

        # Get all September lines
        september_lines = self.env['september.line'].search([])
        if not september_lines:
            raise UserError(_("No September lines found."))

        # Mapping for type fields
        type_to_field = {
            'ცფ': 'x_studio_float_field_3vo_1j2fk5vqk',
            'ცფს': 'x_studio_float_field_6n2_1j2fk773p',
            'კს': 'x_studio_003',
            'ჩფ': 'x_studio_004',
            'ყუ': 'x_studio_005',
            'დფ': 'x_studio_006',
            'ოდო': 'x_studio_007',
            'კდ': 'x_studio_008',
            'უკ': 'x_studio_009',
            'მეტ': 'x_studio_010',
            'ლაბ': 'x_studio_011',
            'IT': 'x_studio_012',
            'ლდ': 'x_studio_013',
            'ტრ': 'x_studio_014',
            'შმდ': 'x_studio_015',
            'სსს': 'x_studio_016',
        }

        # Aggregate data by (code, budget_name_main, product_id)
        grouped_data = {}
        for line in september_lines:
            key = (
                line.x_studio_related_field_1pq_1j2ffqufh,
                line.budget_name_main.id if line.budget_name_main else False,
                line.product_id.id if line.product_id else False
            )

            if key not in grouped_data:
                grouped_data[key] = {'quantity': 0.0}
                for field in type_to_field.values():
                    grouped_data[key][field] = 0.0

            grouped_data[key]['quantity'] += line.quantity
            line_type = getattr(line, 'x_studio_related_field_5ot_1j2hik7te', None)
            if line_type and line_type in type_to_field:
                grouped_data[key][type_to_field[line_type]] += line.quantity

        BudgetingLine = self.env['budgeting.line']
        created_lines = 0
        updated_lines = 0

        for (code, budget_id, product_id), totals in grouped_data.items():
            lines_for_key = [line.id for line in september_lines if (
                    line.x_studio_related_field_1pq_1j2ffqufh == code and
                    (line.budget_name_main.id if line.budget_name_main else False) == budget_id and
                    (line.product_id.id if line.product_id else False) == product_id
            )]

            vals = {
                'x_studio_code': code,
                'budget_name_main': budget_id,
                'product_id': product_id,
                'quantity': totals['quantity'],
                'request_id': self.budget_request_id.id,
                'name': self.env['product.product'].browse(product_id).name if product_id else (code or 'N/A'),
                'x_studio_september_requests': [(6, 0, lines_for_key)],

            }

            for field_name in type_to_field.values():
                vals[field_name] = totals[field_name]

            # Check if line exists
            existing = BudgetingLine.search([
                ('x_studio_code', '=', code),
                ('budget_name_main', '=', budget_id),
                ('product_id', '=', product_id),
                ('request_id', '=', self.budget_request_id.id)

            ], limit=1)

            if existing:
                existing.write(vals)
                updated_lines += 1
            else:
                BudgetingLine.create(vals)
                created_lines += 1

        message = _("Created {} new lines and updated {} existing lines in budget request '{}'.").format(
            created_lines, updated_lines, self.budget_request_id.name
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Budgeting Lines Created Successfully"),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
