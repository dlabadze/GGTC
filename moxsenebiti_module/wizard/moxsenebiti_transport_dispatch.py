from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MoxsenebitiTransportDispatch(models.TransientModel):
    _name = "moxsenebiti.transport.dispatch"
    _description = "Transport Dispatch Wizard"

    moxsenebiti_id = fields.Many2one(
        "moxsenebiti",
        string="მოხსენება",
        required=True,
    )

    # Transport approvers to add
    transport_approver_ids = fields.Many2many(
        "res.users",
        string="ვიზირება - ტრანსპორტი",
        required=True,
        domain=[('share', '=', False)],
    )

    # Read-only summary of employee lines from the moxsenebiti
    employee_line_ids = fields.One2many(
        related="moxsenebiti_id.employee_line_ids",
        string="თანამშრომლები / მანქანები",
        readonly=False,
    )

    def action_confirm(self):
        self.ensure_one()

        mox = self.moxsenebiti_id

        if mox.transport_state != 'pending_dispatch':
            raise UserError(_("ეს ეტაპი აღარ არის აქტიური."))

        if not mox.can_dispatch and mox.env.user.id != (
            mox.x_studio_transport_disp.id if hasattr(mox, 'x_studio_transport_disp') else False
        ):
            raise UserError(_("მხოლოდ სატრანსპორტო Dispatcher-ს შეუძლია ამ ეტაპის შესრულება."))

        if not self.transport_approver_ids:
            raise UserError(_("გთხოვთ მიუთითოთ სულ მცირე ერთი ვიზიტორი."))

        # Add transport approver lines to the moxsenebiti
        for user in self.transport_approver_ids:
            self.env['moxsenebiti.approver.line'].create({
                'moxsenebiti_id': mox.id,
                'user_id': user.id,
                'approver_type': 'transport',
                'state': 'waiting',
                'sequence': 99,
            })

        # Advance transport state
        mox.transport_state = 'pending_transport_appr'
        mox.message_post(
            body=_(
                "დისპეტჩერმა დაამატა მანქანები და გაუგზავნა ვიზიტორებს: %s"
            ) % ', '.join(self.transport_approver_ids.mapped('name'))
        )

        # Mark dispatcher's own activity done
        mox._done_activity_for_user(
            self.env.user, "ვიზირება - ტრანსპორტი"
        )

        # Notify transport approvers
        mox._notify_approvers()

        return {'type': 'ir.actions.act_window_close'}
