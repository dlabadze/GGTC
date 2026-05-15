from odoo import fields, models


class DoneFacturaDaily(models.Model):
    _inherit = 'done.factura'

    requisition_avansi_daily_id = fields.Many2one(
        'purchase.requisition.avansi',
        string='ავანსის ხაზი (დღიური)',
        copy=False,
        ondelete='set null',
    )
