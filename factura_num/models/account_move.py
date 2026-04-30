from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_number = fields.Char(
        related='combined_invoice_id.invoice_number',
        string='ზედნადების ნომერი',
        readonly=False
    )

    get_invoice_id = fields.Char(
        related='combined_invoice_id.get_invoice_id',
        string='ფაქტურის ნომერი',
        readonly=False
    )
