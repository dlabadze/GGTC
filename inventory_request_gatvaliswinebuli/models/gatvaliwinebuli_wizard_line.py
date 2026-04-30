from odoo import models, fields


class GatvaliwinebuliWizardLine(models.TransientModel):
    _name = 'gatvaliwinebuli.wizard.line'
    _description = 'Gatvaliwinebuli Wizard Line'

    request_number = fields.Char(string='Request Number')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    line_type = fields.Selection([
        ('purchase', 'შესასყიდი'),
        ('planned', 'გათვალისწინებული'),
    ], string='Line Type', required=True)
    wizard_id = fields.Many2one('gatvaliwinebuli.wizard', string='Wizard', ondelete='cascade')
    source_inventory_line_id = fields.Many2one('inventory.line', string='Source Line')


class GatvaliwinebuliRequestWizardLine(models.TransientModel):
    _name = 'gatvaliwinebuli.request.wizard.line'
    _description = 'Gatvaliwinebuli Request Wizard Line'

    request_number = fields.Char(string='Request Number')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    line_type = fields.Selection([
        ('purchase', 'შესასყიდი'),
        ('planned', 'გათვალისწინებული'),
    ], string='Line Type', required=True)
    wizard_id = fields.Many2one('gatvaliwinebuli.request.wizard', string='Wizard', ondelete='cascade')
