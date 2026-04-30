from odoo import models, fields, api


class InventoryRequestStage(models.Model):
    _name = 'inventory.request.stage'
    _description = 'Inventory Request Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    fold = fields.Boolean(string='Folded in Kanban', default=False,
                          help="This stage is folded in the kanban view when there are no records in that stage to display.")
    active = fields.Boolean(string='Active', default=True)

    # Color for kanban view
    color = fields.Integer(string='Color Index', default=0)


class InventoryLineStage(models.Model):
    _name = 'inventory.line.stage'
    _description = 'Inventory Line Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    fold = fields.Boolean(string='Folded in Kanban', default=False,
                          help="This stage is folded in the kanban view when there are no records in that stage to display.")
    active = fields.Boolean(string='Active', default=True)

    # Color for kanban view
    color = fields.Integer(string='Color Index', default=0)