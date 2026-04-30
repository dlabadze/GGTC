from odoo import models, fields, api
from datetime import timedelta


class InventoryRequestApproverUsers(models.Model):
    _name = 'inventory.request.approver.users'
    _description = 'Inventory Request Approver Users'
    _order = 'is_first_approver desc, id'

    is_first_approver = fields.Boolean(string='First Approver (Requested By)', default=False)
    user_id = fields.Many2one('res.users', string='User')
    job_position = fields.Many2one('hr.job', string='Job Position')
    approve_datetime = fields.Datetime(string='Approve Datetime')
    approve_datetime_plus_4h = fields.Char(string='Approve Datetime +4h', compute='_compute_approve_datetime_plus_4h')
    user_signature = fields.Binary(related='user_id.sign_signature', readonly=False)
    inventory_request_id = fields.Many2one('inventory.request', string='Inventory Request')

    @api.depends('approve_datetime')
    def _compute_approve_datetime_plus_4h(self):
        for rec in self:
            if rec.approve_datetime:
                datetime_plus_4h = rec.approve_datetime + timedelta(hours=4)
                rec.approve_datetime_plus_4h = datetime_plus_4h.strftime('%Y-%m-%d %H:%M:%S')
            else:
                rec.approve_datetime_plus_4h = False