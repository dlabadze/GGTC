from odoo import models, fields, api


class FleetBranch(models.Model):
    _name = 'fleet.branch'
    _description = 'Fleet Branch'

    name = fields.Char(string='Name', required=True)