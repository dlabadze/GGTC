import requests
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError
import logging
from datetime import datetime
import pandas as pd

_logger = logging.getLogger(__name__)


class res_users_ex(models.Model):
    _inherit='res.users'

    rs_acc = fields.Char(string='rs.ge ექაუნთი')
    rs_pass = fields.Char(string='rs.ge პაროლი')
    rs_fasi = fields.Boolean(string='რს ფასის გადაცემა შიდა გადაზიდვაზე')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    buyer_tin = fields.Char(string='buyer_tin')
    company_review=fields.Char(string='company_name')
    amount=fields.Float(string='amount')


    is_pension = fields.Boolean(
        string='Has Pension',
        default=False,
        help='Check if employee has pension benefits'
    )


    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    status = fields.Char('Status')
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model')
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი')
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID')
    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char(string="End Location")
    editable_end_location = fields.Char(string="ტრანსპორტირების დასრულების ადგილი")
    error_field = fields.Char(string="error_field")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    show_all_fields = fields.Boolean(string='რს-ის ველები')



    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                # Convert the Datetime field to a datetime object
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)

                # Format the datetime object to a string in the desired format
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.end_location = self.partner_id.street
            if not self.editable_end_location:
                self.editable_end_location = self.partner_id.street

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.start_location = self.warehouse_id.additional_address
        else:
            self.start_location = False


    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')

    is_start_location_required = fields.Boolean(string="Is Start Location Required", compute="_compute_is_start_location_required")

    @api.depends('delivery')
    def _compute_is_start_location_required(self):
        for record in self:
            record.is_start_location_required = record.delivery == '2'

    is_editable_end_location_required = fields.Boolean(
        string="Is Editable End Location Required", compute="_compute_is_editable_end_location_required"
    )


    @api.depends('delivery')
    def _compute_is_editable_end_location_required(self):
        for record in self:
            record.is_editable_end_location_required = record.delivery == '2'


    @api.onchange('delivery')
    def _onchange_delivery(self):
        if self.delivery == '3':
            self.editable_end_location = self.start_location

    TRANSPORT_TYPES = [
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ]
    trans_id = fields.Selection(TRANSPORT_TYPES, string='ტრანსპორტირების სახე', default='1')


    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')



    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')

    BUYER_TYPES = [
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ]

    DRIVER_TYPES = [
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ]

    TRANSPORT_COST_PAYER_TYPES = [
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ]
    buyer_type = fields.Selection(BUYER_TYPES, string='მყიდველი', default='1')
    driver_type = fields.Selection(DRIVER_TYPES, string='მძღოლის ტიპი', default='1')
    transport_cost_payer = fields.Selection(TRANSPORT_COST_PAYER_TYPES, string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')
    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char('მძღოლის სახელი')
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    comment = fields.Text('კომენტარი')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    completed_soap = fields.Char(string = 'გაგზავნილია')



    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'
    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    @api.onchange('delivery', 'location_id')
    def _onchange_delivery_or_location(self):
        if self.delivery == '2':
            self.warehouse_id.additional_address
            self.editable_end_location = self.partner_id.street


    @api.onchange('driver_id')
    def get_driver_name(self):
        # This method will be implemented when SOAP integration is added
        pass




    def _prepare_invoice(self):
        """
        Override _prepare_invoice method to include additional fields and order line items in the invoice creation.
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        _logger.info("Preparing invoice for sale order %s", self.id)


        # Log the original invoice lines prepared by the super call
        _logger.info("Original invoice lines: %s", invoice_vals.get('invoice_line_ids', []))

        invoice_vals.update({
            'partner_vat': self.partner_vat,
            'status': self.status,
            'invoice_number': self.invoice_number,
            'invoice_id': self.invoice_id,
            'start_location': self.start_location,
            'end_location': self.end_location,
            'editable_end_location': self.editable_end_location,
            'delivery': self.delivery,
            'trans_id': self.trans_id,
            'trans_txt': self.trans_txt,
            'is_trans_id_4': self.is_trans_id_4,
            'buyer_type': self.buyer_type,
            'driver_type': self.driver_type,
            'car_number': self.car_number,
            'driver_id': self.driver_id,
            'driver_name': self.driver_name,
            'transport_cost': self.transport_cost,
            'transport_cost_payer': self.transport_cost_payer,
            'comment': self.comment,
            'rs_acc': self.user_id.rs_acc,
            'rs_pass': self.user_id.rs_pass,
            'completed_soap': self.completed_soap,
            'begin_date': self.begin_date,
            'combined_invoice_id': self.combined_invoice_id.id,
            'rs_acc':self.rs_acc,
            'rs_pass':self.rs_pass,

            # 'invoice_line_ids': invoice_line_data,  # Only include the new invoice line data
        })

        _logger.info("Final invoice values: %s", invoice_vals)

        return invoice_vals

    def update_currency_rates_from_api(self):
        api_url = 'https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date=2024-09-09'

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            # The response is a list, so we need to access the first element
            data = data[0]  # Get the first item from the list

            # Extract the relevant data
            currencies = data.get('currencies', [])

            # Convert to DataFrame
            df = pd.DataFrame(currencies)

            # Fetch the currency model and rate model
            currency_model = self.env['res.currency']
            rate_model = self.env['res.currency.rate']

            # Process API data
            if not df.empty:
                for _, row in df.iterrows():
                    currency_code = row['code']  # Use 'code' for currency code
                    rate_relative_to_gel = row['rate']   # Use 'rate' for GEL-based rate
                    date_str = row['validFromDate']

                    # Convert date format
                    try:
                        date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError:
                        _logger.warning('Date format for %s is invalid: %s', currency_code, date_str)
                        continue

                    # Set rate for GEL
                    if currency_code == 'GEL':
                        company_rate = 1.0  # GEL should always have a rate of 1.0
                    else:
                        # Use the rate as provided by the API (relative to GEL)
                        company_rate = rate_relative_to_gel

                    # Search for the currency in Odoo
                    currency = currency_model.search([('name', '=', currency_code)], limit=1)
                    if not currency:
                        _logger.warning('Currency with code %s not found.', currency_code)
                        continue

                    # Prepare the rate values
                    rate_vals = {
                        'name': date,
                        'rate': company_rate,
                        'currency_id': currency.id,
                    }

                    # Check if the rate for this currency already exists for the given date
                    existing_rate = rate_model.search([
                        ('currency_id', '=', currency.id),
                        ('name', '=', date),
                    ], limit=1)

                    if existing_rate:
                        existing_rate.write(rate_vals)
                        _logger.info('Updated existing currency rate for %s to %s on %s.', currency_code, company_rate, date)
                    else:
                        rate_model.create(rate_vals)
                        _logger.info('Created new currency rate for %s to %s on %s.', currency_code, company_rate, date)

        except requests.RequestException as e:
            _logger.error('Failed to fetch data from the API: %s', e)
            raise UserError(_('Failed to fetch data from the API.'))





class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    barcode = fields.Char(related='product_id.barcode', string="ბარკოდი", store=True)
    unit_id = fields.Selection(related='product_id.unit_id', string = 'ერთეული rs.ge', store=True)
    unit_txt = fields.Char(related='product_id.unit_txt', string = 'სხვა ერთეული', store=True)

    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_stock_moves(picking)

        import logging
        _logger = logging.getLogger(__name__)

        for move_values in res:
            _logger.info("=== DEBUG INFO ===")
            _logger.info(f"Self: {self}")
            _logger.info(f"x_studio_ value: {self.x_studio_}")
            _logger.info(f"Move values before: {move_values}")

            move_values.update({
                'unit_price': self.price_unit,
                'x_studio_request_number': self.x_studio_,
            })

            _logger.info(f"Move values after: {move_values}")

        return res



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    unit_id = fields.Selection([
        ('1', 'ცალი'),
        ('3', 'გრამი'),
        ('4', 'ლიტრი'),
        ('5', 'ტონა'),
        ('7', 'სანტიმეტრი'),
        ('8', 'მეტრი'),
        ('9', 'კილომეტრი'),
        ('10', 'კვ.სმ'),
        ('11', 'კვ.მ'),
        ('12', 'მ³'),
        ('13', 'მილილიტრი'),
        ('2', 'კგ'),
        ('99', 'სხვა')
    ], string='ერთეული rs.ge')

    unit_txt = fields.Char(string='სხვა ერთეული')
    buyer_info_ids = fields.One2many('product.template.buyer.info', 'product_id', string='Buyer Info')







class AccountMove(models.Model):
    _inherit = 'account.move'
    status = fields.Char('Status')
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model')
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი')
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID')
    factura_num=fields.Char(related='combined_invoice_id.factura_num', string= 'ფაქტურის id')
    get_invoice_id = fields.Char(related='combined_invoice_id.get_invoice_id', string='ფაქტურის ნომერი')
    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    editable_end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    error_field = fields.Char('error_field')
    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')
    trans_id = fields.Selection([
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ], string='ტრანსპორტირების სახე', default='1')

    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')
    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')

    buyer_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მყიდველი', default='1')

    driver_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მძღოლის ტიპი', default='1')
    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char('მძღოლის სახელი')
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    transport_cost_payer = fields.Selection([
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ], string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')
    comment = fields.Text('კომენტარი')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    completed_soap = fields.Char(string = 'გაგზავნილია')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    show_all_fields = fields.Boolean(string='რს-ის ველები')
    extracted_data = fields.Text(string='Extracted Data')


    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')

    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                # Convert the Datetime field to a datetime object
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)

                # Format the datetime object to a string in the desired format
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.end_location = self.partner_id.street
            if not self.editable_end_location:
                self.editable_end_location = self.partner_id.street

    @api.onchange('delivery')
    def _onchange_delivery(self):
        if self.delivery == '3':
            self.start_location = self.editable_end_location


    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    @api.onchange('driver_id')
    def get_driver_name(self):
        # This method will be implemented when SOAP integration is added
        pass




class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    barcode = fields.Char(related='product_id.barcode', string="Barcode", store=True)
    unit_id = fields.Selection(related='product_id.unit_id', string="Unit", store=True)
    unit_txt= fields.Char(related='product_id.unit_txt', string="სხვა ერთეული", store=True)



class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')
    completed_soap = fields.Char(string='გაგზავნილია')
    rs_fasi = fields.Boolean(related='user_id.rs_fasi', string='რს ფასის გადაცემა შიდა გადაზიდვაზე', store=True)
    show_internal_fields = fields.Boolean(compute='_compute_show_internal_fields', store=True)
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model', compute='_compute_combined_invoice_id', store=True)
    car_number=fields.Char(string='მანქანის ნომერი')
    driver_id=fields.Char(string='მძღოლის პირადი ნომერი')

    @api.depends('origin')
    def _compute_combined_invoice_id(self):
        for picking in self:
            if picking.origin:
                # Fetch the related sale order
                sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                if sale_order:
                    self._copy_values_from_order(picking, sale_order)
                else:
                    # If not a sale order, check for purchase order
                    purchase_order = self.env['purchase.order'].search([('name', '=', picking.origin)], limit=1)
                    if purchase_order:
                        self._copy_values_from_order(picking, purchase_order)

    def _copy_values_from_order(self, picking, order):
        picking.combined_invoice_id = order.combined_invoice_id
        picking.driver_id = order.driver_id
        picking.driver_name = order.driver_name
        picking.car_number = order.car_number
        picking.editable_end_location = order.editable_end_location
        picking.start_location = order.start_location
        picking.comment = order.comment
        picking.trans_id = order.trans_id
        picking.show_all_fields = order.show_all_fields
        picking.transport_cost = order.transport_cost
        picking.delivery = order.delivery
        picking.trans_txt = order.trans_txt
        picking.driver_type = order.driver_type
        picking.buyer_type = order.buyer_type
        picking.transport_cost_payer = order.transport_cost_payer








    @api.depends('origin')
    def _compute_field_editability(self):
        for picking in self:
            is_origin_empty = not bool(picking.origin)
            picking.is_origin_empty = is_origin_empty

    is_origin_empty = fields.Boolean(compute='_compute_field_editability', store=False)

    invoice_number = fields.Char(
        related='combined_invoice_id.invoice_number',
        string='ზედნადების ნომერი',
        readonly=False,
        store=True,
        compute_sudo=True,
        depends=['origin']
    )

    invoice_id = fields.Char(
        related='combined_invoice_id.invoice_id',
        string='ზედნადების ID',
        readonly=False,
        store=True,
        compute_sudo=True,
        depends=['origin']
    )
    factura_num=fields.Char(related='combined_invoice_id.factura_num', string= 'ფაქტურის ნომერი')
    get_invoice_id = fields.Char(related='combined_invoice_id.get_invoice_id', string='ფაქტურის ID')
    error_field = fields.Char('error_field')
    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')
    trans_id = fields.Selection([
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ], string='ტრანსპორტირების სახე', default='1')

    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')
    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')

    buyer_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მყიდველი', default='1')

    driver_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მძღოლის ტიპი', default='1')
    driver_name = fields.Char('მძღოლის სახელი')
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    transport_cost_payer = fields.Selection([
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ], string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')
    comment = fields.Text('კომენტარი')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    completed_soap = fields.Char(string = 'გაგზავნილია')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    field5 = fields.Char('field5')
    show_all_fields = fields.Boolean(string='რს-ის ველები')
    is_start_location_required = fields.Boolean(string="Is Start Location Required", compute="_compute_is_start_location_required")

    @api.depends('delivery')
    def _compute_is_start_location_required(self):
        for record in self:
            record.is_start_location_required = record.delivery == '2'

    is_editable_end_location_required = fields.Boolean(
        string="Is Editable End Location Required", compute="_compute_is_editable_end_location_required"
    )


    @api.depends('delivery')
    def _compute_is_editable_end_location_required(self):
        for record in self:
            record.is_editable_end_location_required = record.delivery == '2'

    @api.depends('picking_type_id')
    def _compute_show_internal_fields(self):
        for record in self:
            record.show_internal_fields = record.picking_type_id.name == 'Internal Transfers'

    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'

    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    end_location = fields.Char(string="End Location")
    editable_end_location = fields.Char(string="ტრანსპორტირების დასრულების ადგილი")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.end_location = self.partner_id.street
            if not self.editable_end_location:
                self.editable_end_location = self.partner_id.street

    @api.onchange('delivery')
    def delivery_change(self):
        if self.delivery == '2':
            self.editable_end_location = self.partner_id.street

    @api.onchange('driver_id')
    def get_driver_name(self):
        # This method will be implemented when SOAP integration is added
        pass

    start_location = fields.Char('ტრანსპორტირების საწყისი')

    @api.onchange('delivery')
    def endlocation(self):
        if self.delivery == '3':
            self.editable_end_location = self.start_location

    @api.onchange('location_id')
    def start_location_warehouse(self):
        if self.location_id:
            # Directly access the warehouse's additional_address
            self.start_location = self.location_id.warehouse_id.additional_address or self.location_id.location_address
        else:
            self.start_location = ''




from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    barcode = fields.Char(related='product_id.barcode', string="Barcode", store=True, readonly=False)
    unit_id = fields.Selection(related='product_id.unit_id', string="rs.ge ერთეული", store=True, readonly=False)
    unit_txt = fields.Char(related='product_id.unit_txt', string="სხვა ერთეული", store=True, readonly=False)

    cost_including_tax = fields.Float(string="Cost Including Tax", compute='_compute_cost_including_tax', store=True, readonly=False)
    tax_included = fields.Boolean(string="Tax Included", default=False, readonly=False)
    tax_id = fields.Many2one('account.tax', string='Tax', store=True, readonly=False)
    unit_price = fields.Float(string="Unit Price")

    @api.onchange('unit_price', 'tax_id', 'quantity', 'state')
    def _compute_cost_including_tax(self):
        for line in self:
            if line.tax_id:
                tax_rate = 1 + line.tax_id.amount / 100
                line.cost_including_tax = line.unit_price * tax_rate * line.product_uom_qty  # Use line.product_uom_qty or line.quantity

    @api.model
    def create(self, vals):
        move = super(StockMove, self).create(vals)

        if move.sale_line_id:
            move._set_price_and_tax_from_order_line(move.sale_line_id, 'sale')
        elif move.purchase_line_id:
            move._set_price_and_tax_from_order_line(move.purchase_line_id, 'purchase')

        return move

    def _set_price_and_tax_from_order_line(self, order_line, order_type):
        # Set the unit price from the order line
        self.write({
            'unit_price': order_line.price_unit,
        })

        # Check each tax in order_line tax field and assign it to stock.move.tax_id
        if order_type == 'sale':
            taxes = order_line.tax_id
        else:  # purchase
            taxes = order_line.taxes_id

        if taxes:
            tax = taxes.filtered(lambda t: t.type_tax_use == order_type)
            if tax:
                self.write({
                    'tax_id': tax[0].id  # Use the first tax (or modify logic as needed)
                })

        # Recalculate the cost including tax after setting the price and tax
        self._compute_cost_including_tax()



class StockLocationInherit(models.Model):
    _inherit = 'stock.location'

    location_address = fields.Char(string="location address")
    warehouse_id = fields.Many2one('stock.warehouse', string='Parent Warehouse')
    warehouse_partner_id = fields.Many2one('res.partner', string='Warehouse Partner', related='warehouse_id.partner_id')


class CombinedInvoiceModel(models.Model):
    _name = 'combined.invoice.model'
    _description = 'Combined Model for Storing Invoice Information'
    _rec_name = 'invoice_number'

    invoice_number = fields.Char(string='ზედნადების ნომერი')
    invoice_id = fields.Char(string='ზედნადების ID')
    factura_num = fields.Char(string='ფაქტურის ნომერი')
    get_invoice_id = fields.Char(string='ფაქტურის ID')
    account_move_id = fields.Many2one('account.move', string="Linked Invoice/Bill", ondelete='set null')


class ProductTemplateBuyerInfo(models.Model):
    _name = 'product.template.buyer.info'
    _description = 'Product Template Buyer Info'

    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')
    buyer_tin = fields.Char(string='მომწოდებელი/კლიენტი')
    barcode = fields.Char(string='ბარკოდი')
    koef = fields.Char(string='კოეფიციენტი', default = 1)



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # New fields
    status = fields.Char('Status')
    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model')
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი')
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID')
    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char(string="End Location")
    editable_end_location = fields.Char(string="ტრანსპორტირების დასრულების ადგილი")
    error_field = fields.Char(string="error_field")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    show_all_fields = fields.Boolean(string='რს-ის ველები')

    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')

    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                # Convert the Datetime field to a datetime object
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)
                # Format the datetime object to a string in the desired format
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.end_location = self.partner_id.street
            if not self.editable_end_location:
                self.editable_end_location = self.partner_id.street

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            self.start_location = self.warehouse_id.partner_id.name
        else:
            self.start_location = False

    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')

    is_start_location_required = fields.Boolean(string="Is Start Location Required", compute="_compute_is_start_location_required")

    @api.depends('delivery')
    def _compute_is_start_location_required(self):
        for record in self:
            record.is_start_location_required = record.delivery == '2'

    is_editable_end_location_required = fields.Boolean(
        string="Is Editable End Location Required", compute="_compute_is_editable_end_location_required"
    )

    @api.depends('delivery')
    def _compute_is_editable_end_location_required(self):
        for record in self:
            record.is_editable_end_location_required = record.delivery == '2'

    @api.onchange('delivery')
    def _onchange_delivery(self):
        if self.delivery == '3':
            self.editable_end_location = self.start_location

    TRANSPORT_TYPES = [
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ]
    trans_id = fields.Selection(TRANSPORT_TYPES, string='ტრანსპორტირების სახე', default='1')

    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')

    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')

    BUYER_TYPES = [
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ]

    DRIVER_TYPES = [
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ]

    TRANSPORT_COST_PAYER_TYPES = [
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ]
    buyer_type = fields.Selection(BUYER_TYPES, string='მყიდველი', default='1')
    driver_type = fields.Selection(DRIVER_TYPES, string='მძღოლის ტიპი', default='1')
    transport_cost_payer = fields.Selection(TRANSPORT_COST_PAYER_TYPES, string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')
    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char(' motorista_name')
    transport_cost = fields.Float('Transport cost')
    comment = fields.Text('Comment')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge Account', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge Password', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    completed_soap = fields.Char(string='Completed SOAP')

    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'

    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    # Landed costs functionality for PurchaseOrder
    has_landed_costs = fields.Boolean(
        string='Has Landing Costs',
        compute='_compute_has_landed_costs',
        store=True
    )

    landed_cost_count = fields.Integer(
        string='Landing Cost Count',
        compute='_compute_has_landed_costs',
        store=True
    )

    @api.depends('picking_ids')
    def _compute_has_landed_costs(self):
        for order in self:
            landed_costs = self.env['stock.landed.cost'].search([
                ('picking_ids', 'in', order.picking_ids.ids)
            ])
            order.has_landed_costs = bool(landed_costs)
            order.landed_cost_count = len(landed_costs)

    def action_view_landed_costs(self):
        self.ensure_one()
        landed_costs = self.env['stock.landed.cost'].search([
            ('picking_ids', 'in', self.picking_ids.ids)
        ])

        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")

        if len(landed_costs) == 1:
            action['views'] = [(self.env.ref('stock_landed_costs.view_stock_landed_cost_form').id, 'form')]
            action['res_id'] = landed_costs.id
        else:
            action['views'] = [
                (self.env.ref('stock_landed_costs.view_stock_landed_cost_tree').id, 'list'),
                (self.env.ref('stock_landed_costs.view_stock_landed_cost_form').id, 'form')
            ]
            action['domain'] = [('id', 'in', landed_costs.ids)]

        return action


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    additional_address = fields.Char(string="საწყობის მისამართი")



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_pension = fields.Boolean(
        string='Has Pension',
        default=False,
        help='Check if employee has pension benefits'
    )

    amount=fields.Float(string='amount')


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    categ_id = fields.Many2one(
        'product.category',
        string='Category',
        related='product_tmpl_id.categ_id',
        store=True
    )


