from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)



class AccountMove(models.Model):
    _inherit = 'account.move'

    inverse_company_rate = fields.Float(compute='_compute_inverse_company_rate', readonly=False, store=True)

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date')
    def _compute_inverse_company_rate(self):
        for move in self:
            currency_rate = move.currency_id
            if currency_rate and currency_rate.rate_ids:
                rate = currency_rate.rate_ids.filtered(lambda r: r.name == move.invoice_date)
                if len(rate) > 1:
                    raise ValidationError("Multiple currency rates found for the same date.")
                if rate:
                    move.inverse_company_rate = 1 / rate.company_rate
                else:
                    move.inverse_company_rate = 1
            else:
                move.inverse_company_rate = 1

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date', 'inverse_company_rate')
    def _compute_invoice_currency_rate(self):
        super()._compute_invoice_currency_rate()
        for move in self:
            currency_rate = move.currency_id
            if currency_rate and currency_rate.rate_ids:
                rate = currency_rate.rate_ids.filtered(lambda r: r.name == move.invoice_date)
                if len(rate) > 1:
                    raise ValidationError("Multiple currency rates found for the same date.")
                if rate:
                    inverse_company_rate = 1 / rate.company_rate
                    move.invoice_currency_rate = 1 / inverse_company_rate
                    _logger.info(f"აბა ვანახოთ invoice_currency_rate inverse_company_rate:დ |{move.invoice_currency_rate} - {inverse_company_rate}|")
                else:
                    move.invoice_currency_rate = 1
            else:
                move.invoice_currency_rate = 1
            _logger.info(f"აბა ვანახოთ invoice_currency_rate inverse_company_rate:დ |{move.invoice_currency_rate} - {move.inverse_company_rate}|")
            _logger.info(f"აბა ვანახოთ invoice_currency_rate inverse_company_rate:დ |{move.invoice_currency_rate} - {move.inverse_company_rate}|")

    def button_create_landed_costs(self):
        """Create landed cost with cost_lines price_unit = invoice line price_unit * inverse_company_rate."""
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)
        rate = self.inverse_company_rate if self.inverse_company_rate else 1.0

        landed_costs = self.env['stock.landed.cost'].with_company(self.company_id).create({
            'vendor_bill_id': self.id,
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                'price_unit': l.price_subtotal * rate,
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in landed_costs_lines],
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])
