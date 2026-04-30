from odoo import models, fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    x_internal_turnover_no = fields.Char(
        string='შიდა ბრუნვის ზედდებულის ნომერი'
    )

    x_internal_turnover_date = fields.Date(
        string='შიდა ბრუნვის ზედდებულის თარიღი'
    )

    x_pre_request_no = fields.Char(
        string='მოთხ. წინასწ. N'
    )

    x_reg_date = fields.Date(
        string='მოთხ. რეგ. თარიღი'
    )
