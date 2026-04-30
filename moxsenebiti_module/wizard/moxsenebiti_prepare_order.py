from odoo import api, fields, models, _
from datetime import datetime

class MoxsenebitiPrepareOrder(models.TransientModel):
    _name = "moxsenebiti.prepare.order"
    _description = "Prepare Order Wizard"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="მოხსენებითი ბარათი", required=True)
    approval_category_id = fields.Many2one("approval.category", string="ბრძანების კატეგორია", required=True)

    def action_create_order(self):
        self.ensure_one()
        moxsenebiti = self.moxsenebiti_id
        
        approver_user_id = self.env.user.id
        if moxsenebiti.env.user.id in moxsenebiti.order_receiver_ids.ids:
             approver_user_id = moxsenebiti.env.user.id
        elif moxsenebiti.order_receiver_id:
             approver_user_id = moxsenebiti.order_receiver_id.id
        elif moxsenebiti.order_receiver_ids:
             approver_user_id = moxsenebiti.order_receiver_ids[0].id

        vals = {
            'name': moxsenebiti.number + ' - ' + (moxsenebiti.comment or ''),
            'request_owner_id': approver_user_id,
            'category_id': self.approval_category_id.id,
            'moxsenebiti_id': moxsenebiti.id,
            'date': datetime.combine(moxsenebiti.start_date, datetime.min.time()) if moxsenebiti.start_date else False,
            'reason': moxsenebiti.comment,
            # Studio Fields Mapping
            'x_studio_adresati': moxsenebiti.adresati_id.id if moxsenebiti.adresati_id else False,
            'x_studio_comment1': moxsenebiti.number,
        }
        
        request = self.env['approval.request'].create(vals)
        moxsenebiti.generated_approval_id = request.id
            
        if approver_user_id:
            request.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=approver_user_id,
                summary=_("მოხსენება გამოგეწერათ"),
                note=_("შეიქმნა ახალი მოთხოვნა: %s") % request.name
            )
        
        # Mark preparation task done
        moxsenebiti._done_activity_for_user(self.env.user, "მოხსენება - გადაწერა")
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
        }
