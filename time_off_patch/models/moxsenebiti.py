from odoo import models, fields, _
from odoo.exceptions import UserError


class MoxsenebitiPatch(models.Model):
    _inherit = "moxsenebiti"

    def action_sign(self):
        self.ensure_one()

        if self.state != "sent":
            raise UserError(_("Document is not in approval flow."))

        if not self.all_approved:
            raise UserError(_("All approvers must approve before signing."))

        if not self.author_id:
            raise UserError(_("Please set Author first."))
        if self.author_id.id != self.env.user.id:
            raise UserError(_("Only the author can sign."))

        if self.category_code != 'biul':
            if not self.word_file:
                raise UserError(_("ხელმოწერამდე აუცილებელია ფაილის მიბმა."))

        if self.word_file:
            self._sign_word_file()

        self.signed_document = True
        self.state = "signed"

        if self.category_code == 'biul':
            if not (self.leave_employee_id and self.time_off_type_id and self.start_date and self.end_date):
                raise UserError(_("Insufficient data to create Time Off (Employee, Type, Dates required)."))

            leave_vals = {
                'holiday_status_id': self.time_off_type_id.id,
                'employee_id': self.leave_employee_id.id,
                'request_date_from': self.start_date,
                'request_date_to': self.end_date,
                'name': self.number,
                #odoo calculates number of days
            }

            try:
                self.env['hr.leave'].sudo().create(leave_vals)
            except Exception as e:
                # Roll back state changes if leave creation fails
                self.signed_document = False
                self.state = "sent"
                raise UserError(_("Failed to create Time Off: %s") % str(e))

        self.message_post(
            body=_("ხელმოწერილია %s-ის მიერ. გადაწერის მოლოდინში.") % self.env.user.name
        )
        self._done_activity_for_user(self.env.user, "მოხსენება - ხელმოწერა")
        self._notify_adresati()