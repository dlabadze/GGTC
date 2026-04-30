from odoo import models, fields, api, _


class CombinedInvoiceModel(models.Model):
    _inherit = 'combined.invoice.model'

    account_move_id = fields.Many2one('account.move', string="Linked Invoice/Bill", ondelete='set null')