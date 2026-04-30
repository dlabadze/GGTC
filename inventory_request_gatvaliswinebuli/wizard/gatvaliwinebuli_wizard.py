from odoo import models, fields, api

class GatvaliwinebuliWizard(models.TransientModel):
    _name = 'gatvaliwinebuli.wizard'
    _description = 'Gatvaliwinebuli Wizard'

    request_id = fields.Many2one('inventory.request', string='Request')
    line_ids = fields.Many2many('inventory.line', string='Lines')


    def action_ok(self):
        return {'type': 'ir.actions.act_window_close'}