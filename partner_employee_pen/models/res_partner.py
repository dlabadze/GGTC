from odoo import models, fields, api

class Partner(models.Model):
    _inherit = "res.partner"

    x_studio_ = fields.Boolean(string="საპენსიო")
    x_studio_shegavati = fields.Float(string="შეღავათი")
    x_studio_start_date_1 = fields.Date(string="დაწყების თარიღი")

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('syncing'):
            for partner in self:
                emp = self.env['hr.employee'].search(['|', ('work_contact_id', '=', partner.id), ('user_id.partner_id', '=', partner.id)])
                if emp and any(field in vals for field in ['x_studio_', 'x_studio_shegavati', 'x_studio_start_date_1','vat']):
                    emp.with_context(syncing=True).write({
                        'x_studio_pension': partner.x_studio_,
                        'x_studio_shegavati': partner.x_studio_shegavati,
                        'x_studio_start_date_1': partner.x_studio_start_date_1,
                        'identification_id': partner.vat,
                    })
        return res