from odoo import models, fields

class FleetFuelRemain(models.Model):
    _name = 'fleet.fuel.remain'
    _description = 'საწვავის ნაშთები'
    _order = 'date desc'

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    reservoir_name = fields.Char(string='რეზერვუარის დასახელება', required=True)
    initial_remain = fields.Float(string='საწყისი ნაშთი', digits=(16, 2))
    final_remain = fields.Float(string='საბოლოო ნაშთი', digits=(16, 2))
