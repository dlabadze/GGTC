from odoo import api, fields, models, _
from odoo.exceptions import UserError

class MoxsenebitiReinitiateWizard(models.TransientModel):
    _name = "moxsenebiti.reinitiate"
    _description = "Reinitiate Wizard"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="მოხსენებითი", required=True)
    reason = fields.Text(string="დაბრუნების მიზეზი", required=True)

    def action_reinitiate_confirm(self):
        self.ensure_one()
        mox = self.moxsenebiti_id
        
        if not mox.is_order_receiver_user:
             raise UserError(_("Only order receiver can reinitiate."))
        
        # remove attached files
        mox.word_file = False
        mox.word_filename = False
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', mox._name),
            ('res_id', '=', mox.id)
        ])
        if attachments:
            attachments.unlink()

        # close pending activities and empty receivers
        if mox.activity_ids:
            mox.activity_ids.action_feedback(_("გაუქმებულია (დაბრუნდა დრაფტში)"))
        mox.order_receiver_ids = [(5, 0, 0)]
        mox.order_receiver_id = False

        # reset state to draft and clear signs
        mox.approver_line_ids.write({"state": "pending", "decision_date": False})
        mox.state = "draft"
        mox.signed_document = False
        mox.transport_state = 'none'

        # send notification to initiator with the reason
        if mox.request_owner_id:
            mox._create_activity_for_user(
                mox.request_owner_id,
                summary="მოხსენება - რედაქტირება (დაბრუნებული)",
                note=self.reason
            )
        
        mox.message_post(body=self.reason)
