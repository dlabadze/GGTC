from odoo import models, fields, api

class InventoryRequestTag(models.Model):
    _name = 'inventory.request.tag'
    _description = 'Inventory Request Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)


class InventoryLineTag(models.Model):
    _name = 'inventory.line.tag'
    _description = 'Inventory Line Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)