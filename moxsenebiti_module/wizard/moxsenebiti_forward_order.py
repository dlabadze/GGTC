from odoo import api, fields, models

class MoxsenebitiForwardOrder(models.TransientModel):
    _name = "moxsenebiti.forward.order"
    _description = "Forward Order Wizard"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Moxsenebiti", required=True)
    new_receiver_id = fields.Many2one("res.users", string="ახალი მიმღები", required=True, domain=[('share', '=', False)])

    def action_forward(self):
        self.ensure_one()
        # 1. Update the receiver
        self.moxsenebiti_id.order_receiver_id = self.new_receiver_id.id
        
        # 2. Mark current user's activity as done (if any)
        current_user = self.env.user
        self.moxsenebiti_id._done_activity_for_user(current_user, "მოხსენება - გადაწერა")
        
        # 3. Create activity for new user
        self.moxsenebiti_id._create_activity_for_user(
            self.new_receiver_id,
            summary="მოხსენება - გადაწერა",
            note="თქვენ გადმოგეწერათ ბრძანების მოსამზადებლად: %s" % self.moxsenebiti_id.name
        )
        
        # 4. Post message
        self.moxsenebiti_id.message_post(
            body="გადაწერა განხორციელდა %s-ის მიერ -> %s-ზე" % (current_user.name, self.new_receiver_id.name)
        )

        return {'type': 'ir.actions.act_window_close'}
