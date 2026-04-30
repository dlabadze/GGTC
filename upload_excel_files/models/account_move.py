from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    identification_code = fields.Char(string="ს/კ (საიდენტიფიკაციო)", compute="_onchange_partner_id_set_identification_code",store=True,readonly=False)
    basis = fields.Text(string="საფუძველი")
    contract_num = fields.Char(string="კონტრაქტის ნომერი")
    danishnuleba = fields.Char(string="დანიშნულება")

    @api.depends('partner_id')
    def _onchange_partner_id_set_identification_code(self):
        for rec in self:
            if rec.partner_id:
                rec.identification_code = rec.partner_id.vat
            else:
                rec.identification_code = False