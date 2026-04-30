from odoo import models, fields, api

class SeptemberRequestTag(models.Model):
    _name = 'september.request.tag'
    _description = 'September Request Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)


class SeptemberLineTag(models.Model):
    _name = 'september.line.tag'
    _description = 'September Line Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)