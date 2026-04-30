from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    gas_contact_person = fields.Char(string='საკონტაქტო პირი')
    gas_contact_phone = fields.Char(string='ტელეფონის ნომერი')
