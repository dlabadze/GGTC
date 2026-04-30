from odoo import models, fields


class InventoryDeptReportLine(models.Model):
    _name = 'inventory.dept.report.line'
    _description = 'Department Request Report Line (aggregated by product)'
    _order = 'product_id'

    request_ids = fields.Many2many(
        'inventory.request',
        string='Requests',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        ondelete='cascade',
    )
    quantity = fields.Float(string='Summed Quantity')
    september_quantity = fields.Float(string='September Quantity')
    difference = fields.Float(string='Difference')
    amount = fields.Float(string='Summed Amount')
    september_amount = fields.Float(string='September Amount')
    difference_amount = fields.Float(string='Difference Amount')
    is_red = fields.Boolean(string='Is Red', default=False)
