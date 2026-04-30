from odoo import models, api
from odoo.exceptions import UserError

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        for attachment in self:
            if attachment.res_model == 'approval.request' and attachment.res_id:
                approval = self.env['approval.request'].sudo().browse(attachment.res_id)
                if approval.exists() and approval.request_status not in ['new', 'cancel']:
                    if self.env.user.id != 2:
                        raise UserError("ამ სტატუსზე მიმაგრებული ფაილის წაშლა შეზღუდულია. წაშლა შეუძლია მხოლოდ ადმინისტრატორს.")
                    else:
                        attachment.sudo().write({'res_model': False, 'res_id': 0})
        return super(IrAttachment, self).unlink()
