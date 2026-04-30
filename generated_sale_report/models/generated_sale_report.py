from odoo import models, fields, api, _


class generatedSaleReport(models.Model):
    _name = 'generated.sale.report'
    _description = 'Generated Sale Report'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    pos_order_id = fields.Many2one('pos.order', string='POS Order')
    pos_order_line_id = fields.Many2one('pos.order.line', string='POS Order Line')
    sale_status = fields.Selection(
        [
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sales Order'),
            ('cancel', 'Cancelled'),
        ],
        string='Sale Status',
    )
    pos_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('cancel', 'Cancel'),
            ('paid', 'Paid'),
            ('done', 'Done'),
            ('invoiced', 'Invoiced'),
        ],
        string='POS Status',
    )
    date_order = fields.Datetime(string='Order Date')
    delivery_date = fields.Datetime(string='Effective Date')
    product_id = fields.Many2one('product.product', string='Product')
    sale_quantity = fields.Float(string='Quantity')
    is_manufactured_product = fields.Boolean(
        string='Is Manufactured Product',
        compute='_compute_is_manufactured_product',
    )
    weight = fields.Float(related='product_id.weight')
    sale_delivery_quantity = fields.Float(string='Delivery Quantity')
    refunded_qty = fields.Float(string='Refunded Quantity')
    sale_invoice_quantity = fields.Float(string='SO Invoice Quantity')
    sale_product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', string='Product UOM')
    sale_packaging_quantity = fields.Float(string='SO Packaging Quantity')
    sale_packaging_id = fields.Many2one('product.packaging', string='SO Packaging')
    unit_price = fields.Float(string='Unit Price')
    sale_amount_until_discount = fields.Float(string='SO Amount Until Discount')
    sale_price_total = fields.Float(string='SO Price Total')
    sale_product_group_id = fields.Many2one(
        'product.group',
        string='პროდუქტის ჯგუფი',
    )
    # პარტინიორიდან (set when generating report from sale_order_id or pos_order_id)
    partner_id = fields.Many2one('res.partner', string='Partner')
    gaertianeba = fields.Char(related='partner_id.x_studio_char_field_5ps_1iv0rlrub')
    savachro_point_type = fields.Selection(related='partner_id.x_studio_selection_field_48_1iv0r23v6')
    # salesperson (set when generating report from sale_order_id or pos_order_id)
    salesperson_id = fields.Many2one('res.users', string='Salesperson')

    cost = fields.Float(string='Cost')
    erteuli_cost = fields.Float(string='Unit Cost')
    delivery_amount = fields.Float(string='Invoice Amount')
    delivery_untaxed_amount = fields.Float(string='Invoice Untaxed Amount')
    returned_invoice_amount = fields.Float(string='Returned Invoice Amount')
    real_invoice_amount = fields.Float(string='Real Invoice Amount')
    real_invoice_untaxed_amount = fields.Float(string='Real Invoice Untaxed Amount')
    returned_qty = fields.Float(string='Returned Quantity')
    earned_amount = fields.Float(string='Earned Amount')
    margin = fields.Float(string='Margin')

    article_id = fields.Many2one('product.article', string='არტიკული')
    category_id = fields.Many2one('product.category', string='კატეგორია')
    supplier_id = fields.Many2one(
        'suppliers',
        string='მომწოდებელი',
        related='product_id.supplier_id',
        store=True,
        readonly=True,
    )
    litri = fields.Float(
        string='ლიტრი',
        store=True,
        readonly=True,
    )
    volume = fields.Float(string='მოცულობა')
    buyer_group = fields.Char(string='მყიდველის ჯგუფი')
    city_region = fields.Char(string='ქალაქი/რეგიონი')
    discount_percent = fields.Float(string='ფასდაკლების პროცენტი')
    loyalty_program_id = fields.Many2one('loyalty.program', string='ფასდაკლების სახელი')
    discount_difference = fields.Float(string='ფასდაკლების სხვაობა რეალურთან')


    @api.depends('product_id')
    def _compute_is_manufactured_product(self):
        for record in self:
            if not record.product_id:
                record.is_manufactured_product = False
                continue
            record.is_manufactured_product = bool(
                getattr(record.product_id, 'is_manufactured_product', False)
            )


