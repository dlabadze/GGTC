from odoo import models, api, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    @property
    def _sequence_date_field(self):

        if self.move_type == 'in_invoice' and self.invoice_date:
            return 'invoice_date'
        return super()._sequence_date_field

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'invoice_date')
    def _compute_name(self):
        super()._compute_name()
