from odoo import models, fields, _
from odoo.exceptions import UserError


class InventoryDepartmentReportWizard(models.TransientModel):
    _name = 'inventory.department.report.wizard'
    _description = 'Department Request Lines Report Wizard'

    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    request_id = fields.Many2one(
        'september.request',
        string='Request',
        required=True,
        help='Products from this September request define which inventory lines to include.',
    )

    def action_generate_report(self):
        self.ensure_one()
        if self.date_end < self.date_start:
            raise UserError(_('End date must be on or after start date.'))

        ref = self.request_id.sudo()

        product_ids = ref.line_ids.filtered('product_id').mapped('product_id').ids
        if not product_ids:
            raise UserError(_('The selected request has no lines with products.'))

        domain = [
            ('request_date', '>=', self.date_start),
            ('request_date', '<=', self.date_end),
            ('september_request_ids', 'in', [ref.id]),
        ]
        requests = self.env['inventory.request'].sudo().search(domain)

        Line = self.env['inventory.dept.report.line'].sudo()

        sep_qty_by_product = {}
        for sep_line in ref.line_ids.filtered('product_id'):
            product_id = sep_line.product_id.id
            sep_qty_by_product[product_id] = sep_qty_by_product.get(product_id, 0.0) + sep_line.quantity

        grouped = {}
        main_request = self.env['inventory.request'].sudo().search([
            ('id', '!=', ref.id),
            ('display_name', '=', ref.display_name),
        ], limit=1)
        main_amount_by_product = {}
        if main_request:
            for main_line in main_request.line_ids.filtered('product_id'):
                product_id = main_line.product_id.id
                main_amount_by_product[product_id] = (
                    main_amount_by_product.get(product_id, 0.0) + (main_line.amount or 0.0)
                )

        for req in requests:
            for inv_line in req.line_ids.filtered(
                lambda l: l.product_id and l.product_id.id in product_ids
            ):
                product_id = inv_line.product_id.id
                if product_id not in grouped:
                    grouped[product_id] = {
                        'product_id': product_id,
                        'quantity': 0.0,
                        'amount': 0.0,
                        'september_amount': main_amount_by_product.get(product_id, 0.0),
                        'request_ids': set(),
                    }

                grouped[product_id]['quantity'] += inv_line.quantity or 0.0
                grouped[product_id]['amount'] += inv_line.amount or 0.0
                grouped[product_id]['request_ids'].add(req.id)

        line_vals = []
        for product_id, data in grouped.items():
            september_quantity = sep_qty_by_product.get(product_id, 0.0)
            difference = september_quantity - data['quantity']
            difference_amount = (data.get('september_amount') or 0.0) - (data.get('amount') or 0.0)
            line_vals.append({
                'product_id': product_id,
                'quantity': data['quantity'],
                'september_quantity': september_quantity,
                'difference': difference,
                'amount': data['amount'],
                'september_amount': data['september_amount'],
                'difference_amount': difference_amount,
                'request_ids': [(6, 0, list(data['request_ids']))],
                'is_red': september_quantity < data['quantity'],
            })

        if not line_vals:
            raise UserError(_('No matching inventory lines found.'))

        lines = Line.create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Report Lines'),
            'res_model': 'inventory.dept.report.line',
            'view_mode': 'list',
            'domain': [('id', 'in', lines.ids)],
            'target': 'current',
        }
