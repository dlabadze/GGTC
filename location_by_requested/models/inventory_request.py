from odoo import models, fields, api

class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    x_studio_many2one_field_49t_1j431uvkl = fields.Many2one('stock.location', string="User Location",
                                                            # compute='_onchange_requested_by',
                                                            store=True, readonly=False)


    # @api.depends('requested_by')
    # def _onchange_requested_by(self):
    #     for rec in self:
    #         if rec.requested_by and rec.requested_by.employee_id:
    #             employee = rec.requested_by.employee_id
    #             location = self.env['stock.location'].search([
    #                 ('x_studio_many2one_field_2sg_1ivajtn79', '=', employee.id)
    #             ], limit=1)
    #             rec.x_studio_many2one_field_49t_1j431uvkl = location.id if location else False
    #         else:
    #             rec.x_studio_many2one_field_49t_1j431uvkl = False

    def action_set_user_location(self):
        for rec in self:
            location = False
            if rec.requested_by and rec.requested_by.employee_id:
                employee = rec.requested_by.employee_id
                location = self.env['stock.location'].search([
                    ('x_studio_many2one_field_2sg_1ivajtn79', '=', employee.id)
                ], limit=1)
            rec.x_studio_many2one_field_49t_1j431uvkl = location.id if location else False