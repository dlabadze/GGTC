from odoo import fields, models


class StockReportFilter(models.Model):
    _name = 'stock.report.filter'
    _description = 'Saved Stock Report Filter'

    user_id = fields.Many2one('res.users', required=True, index=True, ondelete='cascade')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    location_ids = fields.Many2many(
        'stock.location',
        'stock_report_filter_location_rel',
        'filter_id',
        'location_id',
        string='Locations',
    )
    category_ids = fields.Many2many(
        'product.category',
        'stock_report_filter_category_rel',
        'filter_id',
        'category_id',
        string='Product Categories',
    )
    use_category_filter = fields.Boolean(string='Filter by Category')
    include_internal_transfers = fields.Boolean(string='Include Internal Transfers', default=True)
    show_amount_columns = fields.Boolean(string='Show Amount Columns')

    _sql_constraints = [
        ('stock_report_filter_user_uniq', 'unique(user_id)', 'Only one filter per user is allowed.'),
    ]
