from odoo import fields, models


class PurchaseRequisitionAvansi(models.Model):
    _name = 'purchase.requisition.avansi'
    _description = 'Purchase Requisition Avansi'

    requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Purchase Requisition',
        required=True,
        ondelete='cascade',
    )
    amount = fields.Float(string='ავანსი', required=True)
    date = fields.Date(string='თარიღი', required=True, default=fields.Date.today)


class PurchaseRequisitionInheritAvansi(models.Model):
    _inherit = 'purchase.requisition'

    avansi_ids = fields.One2many(
        'purchase.requisition.avansi',
        'requisition_id',
        string='ავანსები',
    )
