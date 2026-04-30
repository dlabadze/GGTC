from odoo import models, fields, api, _


class ReturnButtonWizard(models.TransientModel):
    _name = 'return.button.wizard'
    _description = 'Return Button Wizard'

    stage_sequence = fields.Integer(string='Stage Sequence', required=True)
    stage_id = fields.Many2one(
        'inventory.request.stage',
        string='Stage',
        required=True,
    )
    request_id = fields.Many2one('inventory.request', string='Request', required=True)

    def action_return(self):
        self.request_id.stage_id = self.stage_id
        if self.request_id.stage_id.name in [
            'ინიციატორი', 'ადგ. საწყობი',
            'ფილიალის უფროსი', 'ზემდგომი',
            'დეპ. ხელმძღვანელი', 'ხელმძღვანელი',
            'სასაწყობე მეურ. სამმ.'
        ]:
            self.request_id.action_delete_internal_transfers()
        if not self.request_id.is_returned:
            self.request_id.name += ' 🔴(დაბრუნებული) 🔴'
        self.request_id.is_returned = True
        return {'type': 'ir.actions.act_window_close'}