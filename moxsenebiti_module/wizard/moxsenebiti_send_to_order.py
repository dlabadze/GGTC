from odoo import api, fields, models

class MoxsenebitiSendToOrder(models.TransientModel):
    _name = "moxsenebiti.send.to.order"
    _description = "Send to Order Wizard"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Moxsenebiti", required=True)
    approver_ids = fields.Many2many("res.users", string="მიმღები", required=True, domain=[('share', '=', False)])

    def action_confirm(self):
        self.ensure_one()
        self.moxsenebiti_id.action_finalize_send_to_order(self.approver_ids.ids)
        return {'type': 'ir.actions.act_window_close'}
