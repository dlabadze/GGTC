from odoo import models, fields

class FuelTrip(models.Model):
    _name = 'fuel.trip'
    _description = 'Fuel Trip'

    date = fields.Date(string='თარიღი', default=fields.Date.context_today, required=True)
    approval_id = fields.Many2one('approval.request', string='ბრძანება', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='ტრანსპორტი', required=True)
    fuel_amount = fields.Float(string='საწვავის ჯამი', digits=(16, 2), required=True)
    is_fueled = fields.Boolean(string='ჩასხმული', default=False)
    employee_id = fields.Many2one('hr.employee', string='თანამშრომელი')
    trip_type = fields.Char(string='ტიპი')
    trip_purpose = fields.Text(string='მივლინების მიზანი')
