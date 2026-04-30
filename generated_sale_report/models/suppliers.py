from odoo import models, fields, api, _


class Suppliers(models.Model):
    _name = 'suppliers'

    name = fields.Char(string='სახელი')