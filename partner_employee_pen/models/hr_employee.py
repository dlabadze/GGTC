from odoo import models, fields, api

class Employee(models.Model):
    _inherit = "hr.employee"

    x_studio_pension = fields.Boolean(string="საპენსიო")

    @api.model
    def create(self, vals):
        emp = super().create(vals)
        if any(field in vals for field in ['identification_id','x_studio_pension', 'x_studio_shegavati', 'x_studio_start_date_1']):
            partners = emp._get_related_partners()
            if partners:
                    partners.with_context(syncing=True).write({
                        'x_studio_': emp.x_studio_pension,
                        'x_studio_shegavati': emp.x_studio_shegavati,
                        'x_studio_start_date_1': emp.x_studio_start_date_1,
                        'vat' : emp.identification_id,
                    })
        return emp

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('syncing') and any(field in vals for field in ['x_studio_pension', 'x_studio_shegavati', 'x_studio_start_date_1','identification_id']):
            for emp in self:
                partners = emp._get_related_partners()
                if partners:
                        partners.with_context(syncing=True).write({
                            'x_studio_': emp.x_studio_pension,
                            'x_studio_shegavati': emp.x_studio_shegavati,
                            'x_studio_start_date_1': emp.x_studio_start_date_1,
                            'vat': emp.identification_id,
                        })
        return res
