from odoo import models, fields, api


class SeptemberRequest(models.Model):
    _inherit = "inventory.request"

    department_id = fields.Many2one('x_request_deps', string="Department")
    # gadaakete department id

    dep_code = fields.Char(string="Dep.Code", compute='_compute_dep_code',readonly=True)

    september_request_id = fields.Many2one('september.request', string="September Request")

    status = fields.Char(string="Status")

    dep_head = fields.Many2one('res.users', string="Dep Head")
    head = fields.Many2one('res.users', string="Head")
    finance_1 = fields.Many2one('res.users', string="Finance")
    location = fields.Many2one('x_location_specific', string="ლოკაცია")
    location_object = fields.Many2one('x_object_location', string='ობიექტი-ლოკაცია')


    @api.depends("department_id.x_studio_")  # adjust to real field name
    def _compute_dep_code(self):
        for rec in self:
            if rec.department_id and rec.department_id.x_studio_:
                rec.dep_code = rec.department_id.x_studio_
            else:
                rec.dep_code = False

