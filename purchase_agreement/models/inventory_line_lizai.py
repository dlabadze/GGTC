from odoo import models, fields, api

class BudgetingLine(models.Model):
    _inherit = 'inventory.line'

    purchase_agreements = fields.Many2many('purchase.requisition', string="Purchase Agreements")
    budget_line = fields.Many2one('budget.line', string='Budget Line')

    purchase_agreements_count = fields.Integer(
        string='Transfer Count',
        compute='_compute_purchase_agreements_count'
    )
    budget_analytic= fields.Many2one('budget.analytic', string='Budget Analytic')
    budget_analytic_line = fields.Many2one('budget.line', string='Budget Analytic Line')

    @api.depends('purchase_agreements')
    def _compute_purchase_agreements_count(self):
        for record in self:
            record.purchase_agreements_count = len(record.purchase_agreements)


    def create_purchase_agreement(self):
        PurchaseAgreement = self.env["purchase.requisition"]
        Vendor = self.env["res.partner"]
        RequisitionLine = self.env["purchase.requisition.line"]

        default_vendor = Vendor.search([('supplier_rank', '>', 0)], limit=1)

        agreement = PurchaseAgreement.create({
            'vendor_id': default_vendor.id if default_vendor else False,
        })



        for line in self:
            agreement.write({
                "line_ids": [(0, 0, {
                    "product_id": line.product_id.id,
                    "x_studio_": line.x_studio_requset_number,
                    "product_description_variants": line.name,
                    "product_qty": line.quantity,
                    "product_uom_id": line.uom_id.id,
                    "price_unit": line.unit_price,
                    "total_amount": line.amount,
                })]
            })

        for line in self:
            existing_line = RequisitionLine.search([
                ("requisition_id", "=", agreement.id),
                ("product_id", "=", line.product_id.id),
                ("product_qty", "=", line.quantity),
                ("product_uom_id", "=", line.uom_id.id),
                ("price_unit", "=", line.unit_price),
                ("total_amount", "=", line.amount),
                ("product_description_variants", "=", line.name),
                ("x_studio_", "=", line.x_studio_requset_number),
            ], limit=1)

            if not existing_line:
                new_line = RequisitionLine.create({
                    "requisition_id": agreement.id,
                    "product_id": line.product_id.id,
                })
                new_line.write({
                    "x_studio_": line.x_studio_requset_number,
                    "product_description_variants": line.name,
                    "product_uom_id": line.uom_id.id if line.uom_id else False,
                    "price_unit": line.unit_price,
                    "total_amount": line.amount,
                })
            self.write({
                "purchase_agreements": [(4, agreement.id)]
            })

        message = "Created Purchase agreement {} on lines: {}.".format(
            agreement.name, self.ids
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Purchase Agreement Created Successfully",
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_purchase_agreements(self):
        self.ensure_one()

        action = self.env.ref('purchase_requisition.action_purchase_requisition').read()[0]

        if len(self.purchase_agreements) == 1:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.requisition',
                'res_id': self.purchase_agreements.id,
                'view_mode': 'form',
                'target': 'current',
                'context': dict(self._context, default_origin=self.name),
            }
        elif self.purchase_agreements:
            action['domain'] = [('id', 'in', self.purchase_agreements.ids)]
            action['context'] = dict(self._context, default_origin=self.name)
        else:
            action = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Purchase Agreements',
                    'message': 'No purchase agreements found for this line.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return action
