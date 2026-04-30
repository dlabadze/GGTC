from odoo import models, fields,api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    factura_num_helper = fields.Char(
        string='ფაქტურის ნომერი',
        compute='_compute_factura_num_helper',
        store=True,
        readonly=False
    )
    # zednd_num_helper = fields.Char(
    #     string='ზედნადების ნომერი',
    #     compute='_compute_zednd_helper',
    #     store=True,
    #     readonly=False
    # )

    @api.depends('combined_invoice_id.factura_num')
    def _compute_factura_num_helper(self):
        for record in self:
            if record.combined_invoice_id.factura_num and record.factura_num:
                record.factura_num_helper = record.factura_num
            else:
                record.factura_num_helper = record.factura_num_helper


    # @api.depends('combined_invoice_id.invoice_number')
    # def _compute_zednd_helper(self):
    #     for record in self:
    #         if record.combined_invoice_id.invoice_number and record.invoice_number:
    #             record.zednd_num_helper = record.invoice_number
    #         else:
    #             record.zednd_num_helper = record.zednd_num_helper

    def _prepare_invoice(self):
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        invoice_vals['get_invoice_id_helper'] = self.factura_num_helper
        # invoice_vals['get_zednd_number_helper'] = self.zednd_num_helper
        # invoice_vals['basis'] = self.x_studio_comment

        return invoice_vals

