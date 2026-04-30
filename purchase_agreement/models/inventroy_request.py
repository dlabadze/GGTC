from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'


    purchase_agreements = fields.Many2many(
        'purchase.requisition',
        'inventory_request_pur_agreement_rel',
        'inventory_request_id',
        'purchase_agreement_id',
        string='Purchase Agreements',
        compute='_compute_purchase_agreements',
    )
    purchase_count = fields.Integer(string='Purchase Count',default=0, compute='_compute_purchase_count')

    @api.depends('purchase_agreements')
    def _compute_purchase_count(self):
        for record in self:
            record.purchase_count = len(record.purchase_agreements)

    @api.depends('line_ids')
    def _compute_purchase_agreements(self):
        for record in self:
            record.purchase_agreements = record.line_ids.mapped('purchase_agreement_directly')

    def action_view_purchase_agreements(self):
        self.ensure_one()

        # Get all unique purchase agreements from this request’s lines
        agreements = self.line_ids.mapped('purchase_agreement_directly')
        agreements = agreements.filtered(lambda a: a.exists())  # safety filter

        if not agreements:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Purchase Agreements'),
                    'message': _('No purchase agreements found for this request.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Load the base Purchase Agreement action from the Purchase Requisition module
        action = self.env.ref('purchase_requisition.action_purchase_requisition').read()[0]

        if len(agreements) == 1:
            action.update({
                'res_id': agreements.id,
                'view_mode': 'form',
                'domain': [('id', '=', agreements.id)],
            })
        else:
            action.update({
                'domain': [('id', 'in', agreements.ids)],
                'view_mode': 'list,form',
            })

        return action

