from odoo import models

class SeptemberRequest(models.Model):
    _inherit = 'september.request'

    def action_open_excel_wizard(self):
        return {
            'name': 'Upload Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'september.excel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},  # <-- pass the current request id
        }
