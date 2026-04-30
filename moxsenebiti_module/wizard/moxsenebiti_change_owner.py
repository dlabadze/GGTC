from odoo import api, fields, models, _
from odoo.exceptions import UserError

class MoxsenebitiChangeOwner(models.TransientModel):
    _name = "moxsenebiti.change.owner"
    _description = "Change Owner Wizard"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Moxsenebiti", required=True)
    new_owner_id = fields.Many2one("res.users", string="ახალი მფლობელი (ინიციატორი)", required=True, domain=[('share', '=', False)])

    def action_confirm(self):
        self.ensure_one()
        mox = self.moxsenebiti_id
        if mox.state != 'draft':
            raise UserError(_("მხოლოდ დრაფტში მყოფი მოხსენების გადაწერაა შესაძლებელი."))
            
        old_owner = mox.request_owner_id
        mox.request_owner_id = self.new_owner_id.id
        
        mox.message_post(body=_("დოკუმენტი გადაწერილია %s-ზე %s-ის მიერ.") % (self.new_owner_id.name, self.env.user.name))
        
        # Complete activity for old owner
        mox._done_activity_for_user(old_owner, "ახალი სატრანსპორტო მოხსენება")
        
        # Create activity for new owner
        mox._create_activity_for_user(
            self.new_owner_id,
            summary="ახალი სატრანსპორტო მოხსენება",
            note=_("გთხოვთ იხილოთ და შეავსოთ ახალი მოხსენება: %s") % mox.display_name,
        )
        return {'type': 'ir.actions.act_window_close'}
