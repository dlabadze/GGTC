from odoo import fields, models


class FacturaChecking(models.Model):
    _name = 'factura.checking'
    _description = 'Factura Checking'

    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
    )
    f_number = fields.Char(string='Factura Number', required=True)
    rs_tanxa = fields.Float(string='RS Tanxa', readonly=True, copy=False)
    factura_status = fields.Selection([
        ('0', 'დადასტურებული'),
        ('1', 'დაუდასტურებელი'),
        ('2', 'ვერ მოიძებნა'),
    ], string='Factura Status', copy=False, default='1')
