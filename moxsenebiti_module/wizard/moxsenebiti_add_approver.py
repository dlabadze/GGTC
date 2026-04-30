from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MoxsenebitiAddApprover(models.TransientModel):
    _name = "moxsenebiti.add.approver"
    _description = "Add Approver Wizard"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Moxsenebiti", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="დამდასტურებელი",
        required=True,
        domain=[('share', '=', False)],
    )

    def action_confirm(self):
        self.ensure_one()
        mox = self.moxsenebiti_id
        if mox.state != 'sent':
            raise UserError(_("დამდასტურებლის დამატება შესაძლებელია მხოლოდ გადაგზავნილ მოხსენებაზე."))
        if mox.signed_document:
            raise UserError(_("ხელმოწერის შემდეგ დამდასტურებლის დამატება არ არის შესაძლებელი."))

        allowed = (
            self.env.user.id in (mox.request_owner_id.id, mox.author_id.id)
            or self.env.user.has_group("base.group_system")
        )
        if not allowed:
            raise UserError(_("დამდასტურებლის დამატება შეუძლია მხოლოდ ინიციატორს, ავტორს ან ადმინისტრატორს."))

        existing_active = mox.approver_line_ids.filtered(
            lambda l: l.user_id.id == self.user_id.id and l.state in ('pending', 'waiting', 'approved')
        )
        if existing_active:
            raise UserError(_("ეს მომხმარებელი უკვე დამატებულია დამდასტურებლად."))

        max_seq = max(mox.approver_line_ids.mapped('sequence') or [0])
        line = self.env['moxsenebiti.approver.line'].create({
            'moxsenebiti_id': mox.id,
            'user_id': self.user_id.id,
            'approver_type': 'regular',
            'sequence': max_seq + 10,
            'state': 'waiting',
        })

        mox.message_post(
            body=_("დაემატა დამდასტურებელი: %s (%s-ის მიერ).") % (self.user_id.name, self.env.user.name)
        )
        mox._create_activity_for_user(
            self.user_id,
            summary="მოხსენება - დადასტურება",
            note=_("გთხოვთ დაადასტუროთ მოხსენება: %s") % mox.display_name,
        )
        return {'type': 'ir.actions.act_window_close'}
