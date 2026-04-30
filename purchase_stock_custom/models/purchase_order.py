from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    custom_transfer_info = fields.Char(string='ხელშეკრულების ნომერი')

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res['custom_transfer_info'] = self.custom_transfer_info
        return res
