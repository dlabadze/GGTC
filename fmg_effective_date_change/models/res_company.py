from odoo import api, fields, models

class ResCompanyEffectiveSet(models.Model):
    _inherit = 'res.company'

    def create(self, vals):
        res = super().create(vals)

        self.env['journal.setup.effective'].sudo().create({
            'company_id': res.id,
            'name': 'Default Effective Stock Journal',
        })

        return res

