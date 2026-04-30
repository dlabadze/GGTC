from odoo import models, fields, api


class SeptemberRequest(models.Model):
    _inherit = "inventory.line"


    dep_code = fields.Char(string="Dep.Code", compute='_compute_dep_code',readonly=True)

    @api.depends("request_id.department_id")
    def _compute_dep_code(self):
        for rec in self:
            if rec.request_id.department_id and rec.request_id.department_id.x_studio_:
                rec.dep_code = rec.request_id.department_id.x_studio_
            else:
              rec.dep_code = False