from odoo import models, fields, api, _,Command
from odoo.exceptions import UserError
import logging
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from odoo.exceptions import ValidationError  # Import ValidationError
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)




class Waybill(models.Model):
    _name = 'waybill'
    _description = 'Waybill'

    def unlink(self):
        for record in self:
            if record.sale_order_id or record.purchase_order_id or record.vendor_bill_id or record.customer_invoice_id:
                raise UserError(_("You cannot delete a waybill that has a linked document (Sale Order, Purchase Order, or Invoice)."))
            
            if record.invoice_id:
                try:
                    # Treat invoice_id as potential ID linkage
                    potential_id = int(record.invoice_id)
                    
                    # Check for Stock Picking (Inventory Receipt / Internal Transfer)
                    if self.env['stock.picking'].browse(potential_id).exists():
                         raise UserError(_("You cannot delete a waybill that is linked to a Stock Picking."))
                    
                    # Check for Account Move (Generic fallback if other fields missed it)
                    if self.env['account.move'].browse(potential_id).exists():
                         raise UserError(_("You cannot delete a waybill that is linked to an Invoice."))
                except ValueError:
                    pass

        return super(Waybill, self).unlink()

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No Sale Order linked to this waybill.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return {
            'name': 'Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No Purchase Order linked to this waybill.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return {
            'name': 'Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
            'target': 'current',
        }

    def action_view_customer_invoice(self):
        self.ensure_one()
        if not self.customer_invoice_id:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No Customer Invoice linked to this waybill.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return {
            'name': 'Customer Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.customer_invoice_id.id,
            'target': 'current',
        }

    def action_view_vendor_bill(self):
        self.ensure_one()
        move_id = self.vendor_bill_id.id
        
        # Fallback to invoice_id if vendor_bill_id is empty
        if not move_id and self.invoice_id:
            try:
                # Check if invoice_id is an integer (Odoo ID)
                potential_id = int(self.invoice_id)
                # Verify the record actually exists in account.move
                if self.env['account.move'].browse(potential_id).exists():
                    move_id = potential_id
            except ValueError:
                # invoice_id might be a non-integer string (e.g., original Waybill ID), ignore it
                pass

        if not move_id:
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No Vendor Bill linked to this waybill.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
             
        return {
            'name': 'Vendor Bill',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move_id,
            'target': 'current',
        }

    waybill_line_history_ids = fields.One2many('waybill.line.history', 'waybill_id', string='Waybill Line Histories')
    waybill_id_number = fields.Char(string='ზედნადების ID')
    waybill_number = fields.Char(string='ზედნადების ნომერი')
    waybill_type = fields.Char(string='ზედნადების ტიპი')
    create_date = fields.Char(string='შექმნის თარიღი')
    buyer_tin = fields.Char(string='მყიდველის საიდენტიფიკაციო')
    buyer_name = fields.Char(string='მყიდველის სახელი')
    seller_name = fields.Char(string='გამყიდველის სახელი')
    seller_tin = fields.Char(string='გამყიდველის საიდინტიფიკაციო')
    start_address = fields.Char(string='საწყისი მისამართი')
    end_address = fields.Char(string='საბოლოო მისამართი')
    transport_cost = fields.Float(string='ტრანსპორტირების ფასი')
    full_amount = fields.Float(string='მთლიანი ფასი')
    activate_date = fields.Char(string='აქტივაციის რიცხვი')
    s_user_id = fields.Integer(string='გამყიდველის User ID')
    begin_date = fields.Char(string='საწყისი თარიღი')
    is_confirmed = fields.Char(string='დადასტურებულია')
    is_corrected = fields.Char(string='დაკორეკტირებულია')
    seller_st = fields.Char(string='Seller ST')
    is_med = fields.Boolean(string='ჯანდაცვა')
    waybill_comment = fields.Text(string='კომენტარი')
    refund_id = fields.Many2one('account.move', string='Refund', readonly=True)
    delivery_picking_id = fields.Many2one('stock.picking', string='Delivery', readonly=True)
    driver_tin = fields.Char(string='მძღოლის პირადი ნომერი')
    driver_name = fields.Char(string='მძღოლის სახელი')
    car_number = fields.Char(string='მანქანის ნომერი')
    delivery_date = fields.Char(string='მიტანის თარიღი')
    close_date = fields.Char(string='დახურვის თარიღი')
    invoice_id = fields.Char(string='ფაქტურის ID')
    line_ids = fields.One2many('waybill.line', 'waybill_id', string='Lines', ondelete='cascade')
    error_text = fields.Text(string='შეცდომის ტექსტი')
    product_id = fields.Many2one('product.template', string='Product', ondelete='set null')
    xarjgat = fields.Boolean(string='დებეტი|დებეტის ანგარიში')
    katId_O = fields.Char(string='katId_O')
    katName_O = fields.Char(string='პროდ.კატ|პროდუქციის კატეგორია')
    stock_Name = fields.Char(string='საწყობი')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True)
    stockId1 = fields.Many2one('stock.location', string='საწყობი 1', help="Link to the first stock location.")
    stockId2 = fields.Many2one('stock.location', string='საწყობი 2', help="Link to the second stock location.")
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    
    
    @api.depends()  # No need for dependency on user_id
    def _compute_rs_acc(self):
        for record in self:
            record.rs_acc = self.env.user.rs_acc  # Fetch rs_acc directly from the current user
    
    @api.depends()  # No need for dependency on user_id
    def _compute_rs_pass(self):
        for record in self:
            record.rs_pass = self.env.user.rs_pass  # Fetch rs_pass directly from the current user

    uom_mapping = {
        '1': 'Unit(s)',
        '3': 'Gram(s)',
        '4': 'Liter(s)',
        '5': 'Tonne',
        '7': 'Centimeter(s)',
        '8': 'Meter(s)',
        '9': 'Kilometer(s)',
        '10': 'Square Centimeter(s)',
        '11': 'Square Meter(s)',
        '12': 'Cubic Meter(s)',
        '13': 'Milliliter(s)',
        '2': 'Kilogram(s)',
        '99': 'Other'
    }
    def _get_or_create_product(self, bar_code, w_name, unit_id, product_id=None, product_category_id=None, koef=1, unit_txt=None, strict_vendor_check=False, price=0.0):
        _logger.info(f"Starting product lookup: {bar_code} - {w_name}")

        try:
            # Get/create UoM first
            uom = self._get_or_create_uom(unit_id, unit_txt)

            # Normalize barcode
            normalized_barcode = bar_code.strip() if bar_code else ''

            # Find the partner first, as it's required for supplierinfo
            partner = self.env['res.partner'].search([('vat', '=', self.seller_tin)], limit=1)

            # 0. Manual Selection Priority
            # If product_id is provided (User manually selected), use it immediately.
            if product_id:
                product = self.env['product.product'].search([('product_tmpl_id', '=', product_id)], limit=1)
                if product:
                    _logger.info(f"Using manually selected product: {product.name}")
                    if partner:
                        supplier_info = self.env['product.supplierinfo'].search([
                            ('partner_id', '=', partner.id),
                            ('product_tmpl_id', '=', product_id)
                        ], limit=1)

                        if not supplier_info:
                            self.env['product.supplierinfo'].create({
                                'partner_id': partner.id,
                                'product_tmpl_id': product_id,
                                'product_code': bar_code,
                                'koef': koef,
                                'min_qty': 0,
                                'price': price,
                            })
                        else:
                             # Update product_code if missing
                            if not supplier_info.product_code:
                                supplier_info.write({'product_code': bar_code})
                            # Always update price if it's different and non-zero
                            if price > 0 and supplier_info.price != price:
                                supplier_info.write({'price': price})
                    return product

            # First check for existing product in product.product using barcode
            # Skip this check if strict_vendor_check is True
            product = None
            if not strict_vendor_check:
                product = self.env['product.product'].search([
                    '|',
                    ('barcode', '=', normalized_barcode),
                    ('default_code', '=', normalized_barcode)
                ], limit=1)

            if product:
                _logger.info(f"Found existing product by barcode: {product.name}")
                if partner:
                    # Check/Create supplier info (Vendor Pricelist)
                    supplier_info = self.env['product.supplierinfo'].search([
                        ('partner_id', '=', partner.id),
                        ('product_tmpl_id', '=', product.product_tmpl_id.id)
                    ], limit=1)

                    if not supplier_info:
                         self.env['product.supplierinfo'].create({
                            'partner_id': partner.id,
                            'product_tmpl_id': product.product_tmpl_id.id,
                            'product_code': bar_code,
                            'koef': koef,
                            'min_qty': 0,
                            'price': price,
                        })
                    else:
                        # Update product_code if missing
                        if not supplier_info.product_code:
                            supplier_info.write({'product_code': bar_code})
                        # Always update price if it's different and non-zero
                        if price > 0 and supplier_info.price != price:
                            supplier_info.write({'price': price})
                return product

            # Check supplier info (Vendor Pricelists) if no direct product found
            if partner:
                supplier_info = self.env['product.supplierinfo'].search([
                    ('partner_id', '=', partner.id),
                    ('product_code', '=', normalized_barcode)
                ], limit=1)

                if supplier_info and supplier_info.product_tmpl_id:
                    _logger.info(f"Found product through supplier info: {supplier_info.product_tmpl_id.name}")
                    product = self.env['product.product'].search([('product_tmpl_id', '=', supplier_info.product_tmpl_id.id)], limit=1)
                    if product:
                        return product



            # If we get here, we need to create a new product
            _logger.info("No existing product found, creating new one")

            # Validate product category
            if not product_category_id:
                raise UserError(f"მიუთითეთ პროდუქციის კატეგორია პროდუქტისთვის: {w_name}")

            category_id = product_category_id.id if hasattr(product_category_id, 'id') else product_category_id

            # Double check one last time before creating
            existing_templates = self.env['product.template'].search([
                '|',
                ('name', '=', w_name),
                '|',
                ('barcode', '=', normalized_barcode),
                ('default_code', '=', normalized_barcode)
            ], limit=1)

            if existing_templates:
                product = self.env['product.product'].search([('product_tmpl_id', '=', existing_templates[0].id)], limit=1)
                if product:
                    _logger.info(f"Found existing product in final check: {product.name}")
                    return product

            # Create new product template
            template_vals = {
                'name': w_name,
                'categ_id': category_id,
                'type': 'consu',
                'is_storable': True,
                'uom_id': uom.id,
                'uom_po_id': uom.id,
                'tracking': 'none',
                'purchase_ok': True,
                'sale_ok': True,
                'default_code': bar_code,
                'barcode': bar_code,
            }

            product_tmpl = self.env['product.template'].create(template_vals)
            _logger.info(f"Created new product template with ID: {product_tmpl.id}")

            # Get the automatically created variant
            product = self.env['product.product'].search([('product_tmpl_id', '=', product_tmpl.id)], limit=1)

            # Create supplier info
            if partner:
                self.env['product.supplierinfo'].create({
                    'partner_id': partner.id,
                    'product_tmpl_id': product_tmpl.id,
                    'product_code': bar_code,
                    'koef': koef,
                    'min_qty': 0,
                    'price': price,
                })

            _logger.info(f"Successfully created new product: {product.name}")
            return product

        except Exception as e:
            _logger.error(f"Error in product creation: {str(e)}")
            raise UserError(f"შეცდომა პროდუქტის შექმნისას {w_name}: {str(e)}")

    def _get_or_create_uom(self, unit_id, unit_txt=None):
        # RS.GE unit mapping to existing system UoMs
        rs_ge_to_odoo_uom = {
            '1': 'ცალი',
            '2': 'კგ',
            '3': 'გრ',
            '4': 'ლ',
            '5': 'ტ',
            '7': 'სმ',
            '8': 'მეტრი',
            '9': 'კმ',
            '10': 'მ²',
            '11': 'მ²',
            '12': 'მ³',
            '13': 'ლ',
        }

        # Category mapping
        uom_category_mapping = {
            '1': 1,    # Unit
            '2': 2,    # Weight
            '3': 2,    # Weight
            '4': 6,    # Volume
            '5': 2,    # Weight
            '7': 4,    # Length
            '8': 4,    # Length
            '9': 4,    # Length
            '10': 5,   # Area
            '11': 5,   # Area
            '12': 6,   # Volume
            '13': 6,   # Volume
        }

        # Known existing UoMs with their IDs
        existing_uoms = {
            'ცალი': 1,
            'გრ': 13,
            'სმ': 8,
            'მეტრი': 5,
            'კმ': 7,
            'მ²': 9,
            'ლ': 10,
            'მ³': 11,
            'კგ': 12,
            'ტ': 14,
        }

        # Handle custom unit case
        if unit_id == '99' and unit_txt:
            uom_name = unit_txt.strip()
            category_id = 1  # Default to Unit category
        else:
            uom_name = rs_ge_to_odoo_uom.get(unit_id)
            if not uom_name:
                raise UserError(f"Invalid or unsupported unit: {unit_id}")
            category_id = uom_category_mapping.get(unit_id, 1)

        # Try to find existing UoM
        uom = None
        if uom_name in existing_uoms:
            uom = self.env['uom.uom'].browse(existing_uoms[uom_name])
            if uom.exists():
                return uom

        # Search case-insensitive
        if not uom:
            uom = self.env['uom.uom'].search([
                '|',
                ('name', '=', uom_name),
                ('name', '=ilike', uom_name)
            ], limit=1)
            if uom:
                return uom

        # Create new UoM if doesn't exist
        category = self.env['uom.category'].browse(category_id)
        if not category.exists():
            raise UserError(f"Category not found for unit: {uom_name}")

        # Conversion factors
        conversion_factors = {
            'გრ': (1000.0, 0.001),
            'სმ': (100.0, 0.01),
            'კმ': (0.001, 1000.0),
            'მ³': (0.001, 1000.0),
            'ტ': (0.001, 1000.0),
        }

        factor, factor_inv = conversion_factors.get(uom_name, (1.0, 1.0))
        uom_type = 'reference' if factor == 1.0 else ('smaller' if factor > 1.0 else 'bigger')

        uom = self.env['uom.uom'].create({
            'name': uom_name,
            'category_id': category.id,
            'factor': factor,
            'factor_inv': factor_inv,
            'uom_type': uom_type,
            'rounding': 0.01
        })

        return uom



    
    mdgomareoba = fields.Selection([
        ('korektirebuli', 'კორექტირებული'),
        ('gadatanili', 'გატარებული'),
        ('araferi', 'გამოწერილი')
    ], string='Mdgomareoba', default='araferi')
    
    @api.depends('waybill_type')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.waybill_type == '1'
            
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')


    # Add Product Category field here
    product_category_id = fields.Many2one(
        'product.category',
        string='პროდუქციის კატეგორია',
        help='Select the product category for this waybill.'
    )
    @api.onchange('product_category_id')
    def _onchange_product_category_id(self):
        for line in self.line_ids:
            line.product_category_id = self.product_category_id

    def _get_field_visibility(self):
        for record in self:
            if record.waybill_type != 1:
                return False
        return True




    @api.onchange('xarjang')
    def _onchange_xarjang(self):
        if self.xarjang:
            for line in self.line_ids:
                line.xarjang = self.xarjang

    @api.onchange('xarjgat')
    def _onchange_xarjgat(self):
        if not self.xarjgat:
            # Clear xarjang for all lines if xarjgat is not checked
            for line in self.line_ids:
                line.xarjang = False
        else:
            # Set xarjang for all lines if xarjgat is checked and xarjang is selected
            if self.xarjang:
                for line in self.line_ids:
                    line.xarjang = self.xarjang


    

    def get_name_from_tin(self,rs_acc, rs_pass, tin):
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
          <tin>{tin}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""

        
        # Define the URL and headers
        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }

        # Send the request
        response = requests.post(url, data=soap_request, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Extract the content of the get_name_from_tinResult element from the response
            start_tag = "<get_name_from_tinResult>"
            end_tag = "</get_name_from_tinResult>"
            start_index = response.text.find(start_tag) + len(start_tag)
            end_index = response.text.find(end_tag)
            name = response.text[start_index:end_index]
            # Fill the name field with the response
            print(name)
            return name

    def action_open_fetch_waybills_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Waybills',
            'res_model': 'fetch.waybills.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('waybill_management_custom.view_fetch_waybills_wizard_form').id,
            'target': 'new',
        }

    def action_open_fetch_waybills_wizard1(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Waybills Wizard1',
            'res_model': 'fetch.waybills.wizard1',
            'view_mode': 'form',
            'view_id': self.env.ref('waybill_management_custom.view_fetch_waybills_wizard1_form').id,
            'target': 'new',
        }

    def action_open_fetch_waybills_wizard3(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Waybills Wizard3',
            'res_model': 'fetch.waybills.wizard3',
            'view_mode': 'form',
            'view_id': self.env.ref('waybill_management_custom.view_fetch_waybills_wizard3_form').id,
            'target': 'new',
        }
    def action_open_fetch_waybills_wizard4(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Waybills Wizard4',
            'res_model': 'fetch.waybills.wizard4',
            'view_mode': 'form',
            'view_id': self.env.ref('waybill_management_custom.view_fetch_waybills_wizard4_form').id,
            'target': 'new',
        }
    def action_open_fetch_waybills_wizard5(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Waybills Wizard5',
            'res_model': 'fetch.waybills.wizard5',
            'view_mode': 'form',
            'view_id': self.env.ref('waybill_management_custom.view_fetch_waybills_wizard5_form').id,
            'target': 'new',
        }

    def _get_tax_ids(self, vat_type, tax_type='sale'):
        """
        Fetch the appropriate tax based on vat_type and tax_type.
        
        Args:
            vat_type: '0' for 18%, '1' for 0%
            tax_type: 'sale' for sales taxes, 'purchase' for purchase taxes
        """
        # Fetch the tax based on the vat_type and tax_type
        if vat_type == '1':  # 0% tax
            tax = self.env['account.tax'].search([
                ('name', '=', '0%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        elif vat_type == '0':  # 18% tax
            tax = self.env['account.tax'].search([
                ('name', '=', '18%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        else:
            tax = self.env['account.tax']  # Default to no taxes if vat_type is unknown
    
        return tax.ids if tax else []


    def create_vendor_bill(self):
       for waybill in self:
           if waybill.mdgomareoba == 'gadatanili':
               raise UserError("ზედნადები უკვე გადატანილია!")
    
           # Find or create partner
           partner = self.env['res.partner'].search([('vat', '=', waybill.seller_tin)], limit=1)
           if not partner:
               seller_name = self.get_name_from_tin(waybill.rs_acc, waybill.rs_pass, waybill.seller_tin)
               partner = self.env['res.partner'].create({
                   'name': seller_name,
                   'vat': waybill.seller_tin,
               })
    
           invoice_lines = []
           purchase_order_lines = []
    
           for line in waybill.line_ids:
               try:
                   if line.xarjang:
                       quantity = float(line.quantity) * float(line.koef or 1)
                       account_id = line.xarjang.id if hasattr(line.xarjang, 'id') else line.xarjang
                       price = float(line.price)/float(line.koef or 1)
                       invoice_lines.append((0, 0, {
                           'quantity': quantity,
                           'price_unit': price,
                           'account_id': account_id,
                           'name': line.w_name,
                           'tax_ids': [(6, 0, self._get_tax_ids(line.vat_type, 'purchase'))],
                       }))
                   else:
                       # Check if product category is set
                       if not line.product_category_id:
                           raise UserError(f"პროდუქტს {line.w_name} არ აქვს მითითებული კატეგორია")
    
                       price = float(line.price)/float(line.koef or 1)
                       # Create/Find product with Strict Vendor Check
                       product = self._get_or_create_product(
                           line.bar_code, 
                           line.w_name, 
                           line.unit_id, 
                           product_id=line.product_id.id if line.product_id else None,
                           product_category_id=line.product_category_id,
                           koef=line.koef,
                           strict_vendor_check=True,
                           price=price
                       )


                       
                       if not product:
                           raise UserError(f"შეცდომა პროდუქტის შექმნისას: {line.w_name}")
    
                       quantity = float(line.quantity) * float(line.koef or 1)
                       price = float(line.price)/float(line.koef or 1)
                       purchase_order_lines.append((0, 0, {
                           'product_id': product.id,
                           'product_qty': quantity,
                           'price_unit': price,
                           'taxes_id': [(6, 0, self._get_tax_ids(line.vat_type, 'purchase'))],
                       }))
               except Exception as e:
                   raise UserError(f"შეცდომა ხაზზე {line.w_name}: {str(e)}")
    
           # Create Purchase Order if there are valid lines
           purchase_order = False
           if purchase_order_lines:
               purchase_order = self.env['purchase.order'].create({
                   'partner_id': partner.id,
                   'order_line': purchase_order_lines,
                   'date_order': fields.Date.today(),
                   'picking_type_id': self.env.ref('stock.picking_type_in').id,
                   'origin': waybill.waybill_number,
               })
    
           # Only create the vendor bill if there are invoice lines
           vendor_bill = False
           if invoice_lines:
               vendor_bill = self.env['account.move'].create({
                   'move_type': 'in_invoice',
                   'partner_id': partner.id,
                   'invoice_date': fields.Date.today(),
                   'car_number': waybill.car_number,
                   'start_location': waybill.start_address,
                   'editable_end_location': waybill.end_address,
                   'driver_id': waybill.driver_tin,
                   'invoice_line_ids': invoice_lines,
               })
    
           # Create Combined Invoice Model record
           combined_invoice = self.env['combined.invoice.model'].create({
               'invoice_number': waybill.waybill_number,
               'invoice_id': waybill.waybill_id_number,
           })
    
           # Link Combined Invoice record
           if vendor_bill:
               vendor_bill.write({'combined_invoice_id': combined_invoice.id})
           if purchase_order:
               purchase_order.write({'combined_invoice_id': combined_invoice.id})
               waybill.write({'purchase_order_id': purchase_order.id})
    
           # Update waybill with vendor bill ID if it exists
           if vendor_bill:
               waybill.write({
                   'invoice_id': vendor_bill.id,
                   'vendor_bill_id': vendor_bill.id
               })
    
           waybill.write({'mdgomareoba': 'gadatanili'})
    
           # Return action
           if vendor_bill:
               return {
                   'type': 'ir.actions.act_window',
                   'res_model': 'account.move',
                   'view_mode': 'form',
                   'res_id': vendor_bill.id,
                   'target': 'current',
               }
    
           if purchase_order:
               return {
                   'type': 'ir.actions.act_window',
                   'res_model': 'purchase.order',
                   'view_mode': 'form',
                   'res_id': purchase_order.id,
                   'target': 'current',
               }
    
           return True
    













    sale_order_id = fields.Many2one('sale.order', string='Sale Order')

    def create_sale_order(self):
        for waybill in self:
            if waybill.mdgomareoba == 'gadatanili':
                raise UserError("ზედნადები უკვე გადატანილია!")
            
            # Check if a customer already exists for the buyer
            partner = self.env['res.partner'].search([
                ('vat', '=', waybill.buyer_tin),
            ], limit=1)
            
            # If no customer exists, create one
            if not partner:
                # Call the get_name_from_tin method to retrieve the vendor's name
                seller_name = self.get_name_from_tin(waybill.rs_acc, waybill.rs_pass, waybill.buyer_tin)
        
                # Create the vendor partner using the name from TIN
                partner = self.env['res.partner'].create({
                    'name': seller_name,  # Use the name fetched from the TIN
                    'vat': waybill.buyer_tin,
                })
            
            # Create sale order lines based on waybill line data
            order_lines = []
            for line in waybill.line_ids:
                if not line.xarjang:  # Exclude if xarjang is present
                    price = float(line.price)/float(line.koef or 1)
                    product = self._get_or_create_product(
                        line.bar_code, 
                        line.w_name, 
                        line.unit_id, 
                        product_id=line.product_id.id if line.product_id else None, 
                        product_category_id=line.product_category_id,
                        koef=line.koef,
                        price=price
                    )
    
                    quantity = float(line.quantity) * float(line.koef or 1)
                    order_line_vals = {
                        'product_id': product.id,
                        'product_uom_qty': quantity,
                        'price_unit': float(line.price),
                        'tax_id': [(6, 0, self._get_tax_ids(line.vat_type, 'sale'))],
                    }
                    order_lines.append((0, 0, order_line_vals))
            
            # Create the sale order
            sale_order = self.env['sale.order'].create({
                'partner_id': partner.id,
                'date_order': fields.Date.today(),
                'car_number': waybill.car_number,  # Add car number
                'start_location': waybill.start_address,  # Add start location
                'editable_end_location': waybill.end_address,  # Add end location
                'driver_id': waybill.driver_tin,  # Add driver ID
                'order_line': order_lines,
            })
            
            # Create Combined Invoice Model record
            combined_invoice = self.env['combined.invoice.model'].create({
                'invoice_number': waybill.waybill_number,  # waybill number as invoice number
                'invoice_id': waybill.waybill_id_number,   # waybill ID as invoice ID
            })
            
            # Link the Combined Invoice record to the newly created sale order
            sale_order.write({'combined_invoice_id': combined_invoice.id})
            
            # Update waybill with the created sale order ID (if needed)
            waybill.write({'sale_order_id': sale_order.id, 'mdgomareoba': 'gadatanili'})
            
            # Return action to open the newly created sale order
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_order.id,
                'target': 'current',
            }
        
        return True





    # Other fields...
    xarjang = fields.Many2one('account.account', string='დებეტ/კრედიტის ანგარიში', help="Account to use for invoicing")
    customer_invoice_id = fields.Many2one(
        'account.move',
        string='Customer Invoice',
        help="The customer invoice created from this waybill."
    )




    def create_customer_invoice(self):
        for waybill in self:
            if waybill.mdgomareoba == 'gadatanili':
                raise UserError("ზედნადები უკვე გადატანილია!")
            _logger.info('Processing Waybill: %s', waybill.waybill_number)
            _logger.info('Customer Name: %s', waybill.buyer_name)
            _logger.info('Customer TIN: %s', waybill.buyer_tin)
    
            # Create Combined Invoice Model record
            combined_invoice = self.env['combined.invoice.model'].create({
                'invoice_number': waybill.waybill_number,
                'invoice_id': waybill.waybill_id_number,
            })
    
            # Find or create the partner (customer) based on the waybill's buyer info
            partner = self.env['res.partner'].search([
                ('vat', '=', waybill.buyer_tin),
            ], limit=1)
    
            if not partner:
                # Call the get_name_from_tin method to retrieve the vendor's name
                seller_name = self.get_name_from_tin(waybill.rs_acc, waybill.rs_pass, waybill.buyer_tin)
        
                # Create the vendor partner using the name from TIN
                partner = self.env['res.partner'].create({
                    'name': seller_name,  # Use the name fetched from the TIN
                    'vat': waybill.buyer_tin,
                })
    
            # Prepare invoice lines from waybill lines
            invoice_lines = []
            for line in waybill.line_ids:
                if line.xarjang:
                    # For lines with xarjang, create invoice line directly
                    quantity = float(line.quantity) * float(line.koef or 1)
                    account_id = waybill.xarjang.id if waybill.xarjang else self.env['account.account'].search([], limit=1).id
                    price = float(line.price)/float(line.koef or 1)
    
                    invoice_lines.append((0, 0, {
                        'name': line.w_name,
                        'quantity': quantity,
                        'price_unit': price,
                        'account_id': account_id,
                        'tax_ids': [(6, 0, self._get_tax_ids(line.vat_type, 'sale'))],
                    }))
    
            # Set payment term (replace 'your_payment_term_id' with actual ID)
            # Create customer invoice
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'combined_invoice_id': combined_invoice.id,
                'invoice_payment_term_id': False,  # Set payment term
                'invoice_date_due': fields.Date.today(),  # Set due date to today's date
            })
    
            # Update the waybill with the created customer invoice ID
            waybill.write({'customer_invoice_id': invoice.id})
            waybill.write({'mdgomareoba': 'gadatanili'})
    
            # Return action to open the newly created customer invoice
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
                'target': 'current',
            }
    
        return True

        
        


    def _get_tax_id(self, vat_type):
        """Helper method to get or create a tax based on vat_type."""
        if vat_type == 0:
            return False  # No tax
        elif vat_type == 1:
            tax = self.env['account.tax'].search([('name', '=', '18% VAT')], limit=1)
            if not tax:
                tax = self.env['account.tax'].create({
                    'name': '18% VAT',
                    'amount': 18.0,
                    'amount_type': 'percent',
                    'type_tax_use': 'sale',
                })
            return tax.id

    def _get_single_tax_id(self, vat_type, tax_type='sale'):
        """
        Fetch a single tax ID based on vat_type and tax_type.
        
        Args:
            vat_type: '0' for 18%, '1' for 0%
            tax_type: 'sale' for sales taxes, 'purchase' for purchase taxes
        """
        # Fetch the tax based on the vat_type and tax_type
        if vat_type == '0':  # 0% tax
            tax = self.env['account.tax'].search([
                ('name', '=', '0%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        elif vat_type == '1':  # 18% tax
            tax = self.env['account.tax'].search([
                ('name', '=', '18%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        else:
            tax = False  # No tax if vat_type is unknown
    
        return tax.id if tax else False



    def create_internal_delivery(self):
        for waybill in self:
            if waybill.mdgomareoba == 'gadatanili':
                raise UserError("ზედნადები უკვე გადატანილია!")
            source_location = waybill.stockId1
            dest_location = waybill.stockId2
    
            # Ensure both source and destination locations are provided
            if not source_location:
                raise UserError("საწყობის მონიშვნის გარეშე ვერ შექმნით შიდა გადაცემას")
            
            if not dest_location:
                raise UserError("საწყობის მონიშვნის გარეშე ვერ შექმნით შიდა გადაცემას")
    
            # Ensure source and destination locations exist in the system
            source_location = self.env['stock.location'].browse(source_location.id)
            if not source_location.exists():
                raise UserError(f"Source location '{waybill.stockId1.name}' not found in the system.")
    
            dest_location = self.env['stock.location'].browse(dest_location.id)
            if not dest_location.exists():
                raise UserError(f"Destination location '{waybill.stockId2.name}' not found in the system.")
            
            # Find or create the partner (customer) based on the waybill's buyer info
            partner = self.env['res.partner'].search([
                ('vat', '=', waybill.buyer_tin),
            ], limit=1)
    
            if not partner:
                # Call the get_name_from_tin method to retrieve the vendor's name
                seller_name = self.get_name_from_tin(waybill.rs_acc, waybill.rs_pass, waybill.buyer_tin)
    
                # Create the vendor partner using the name from TIN
                partner = self.env['res.partner'].create({
                    'name': seller_name,  # Use the name fetched from the TIN
                    'vat': waybill.buyer_tin,
                })
    
            # Create a new internal delivery
            internal_delivery = self.env['stock.picking'].create({
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Ensure this reference is correct
                'partner_id': partner.id,  # No partner for internal transfers
                'location_id': source_location.id,  # Set source location
                'location_dest_id': dest_location.id,  # Set destination location
            })
    
            # Create Combined Invoice Model record
            combined_invoice = self.env['combined.invoice.model'].create({
                'invoice_number': waybill.waybill_number,  # waybill number as invoice number
                'invoice_id': waybill.waybill_id_number,   # waybill ID as invoice ID
            })
    
            # Link the Combined Invoice record to the newly created internal delivery
            internal_delivery.write({'combined_invoice_id': combined_invoice.id})
    
            # Update waybill with the created internal delivery ID (if needed)
            waybill.write({'invoice_id': internal_delivery.id})
    
            # Create stock moves and move lines
            move_lines = []
            for line in waybill.line_ids:  # Assuming `line_ids` is the field containing the lines
                # Get or create the product based on w_name
                price = float(line.price)/float(line.koef or 1)
                product = self._get_or_create_product(
                    line.bar_code, 
                    line.w_name, 
                    line.unit_id, 
                    product_id=line.product_id.id if line.product_id else None, 
                    product_category_id=line.product_category_id,
                    koef=line.koef,
                    price=price
                )
                quantity = float(line.quantity) * float(line.koef or 1)
                
                # Create stock move
                stock_move = self.env['stock.move'].create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'picking_id': internal_delivery.id,
                    'location_id': internal_delivery.location_id.id,  # Source location
                    'location_dest_id': internal_delivery.location_dest_id.id,  # Destination location
                    'state': 'draft',  # Set to 'draft' initially
                    'tax_id': self._get_single_tax_id(line.vat_type, 'sale'),  # Set tax_id as an integer, not a list


                })
    
                # Create stock move lines for the stock move
                move_lines.append({
                    'move_id': stock_move.id,
                    'product_id': product.id, # Ensure UoM is provided
                    'location_id': internal_delivery.location_id.id,  # Source location
                    'location_dest_id': internal_delivery.location_dest_id.id,  # Destination location
                    'result_package_id': False,
                    
                })
    
            # Update the internal delivery with move lines
            if move_lines:
                self.env['stock.move.line'].create(move_lines)
            waybill.write({'mdgomareoba': 'gadatanili'})
    
            # Return action to open the newly created internal delivery
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': internal_delivery.id,
                'target': 'current',
            }


    
            # Create Combined Invoice



    def action_create_internal_delivery(self):
        return self.create_internal_delivery()



    def create_purchase_return(self):
        for waybill in self:
            if waybill.mdgomareoba == 'gadatanili':
                raise UserError("ზედნადები უკვე გადატანილია!")

            # Check if a vendor already exists for the seller
            vendor = self.env['res.partner'].search([
                ('vat', '=', waybill.seller_tin),
            ], limit=1)
            
            # If no vendor exists, create one
            if not vendor:
                if waybill.seller_name:
                    vendor = self.env['res.partner'].create({
                        'name': waybill.seller_name,
                        'vat': waybill.seller_tin,
                    })
                else:
                    _logger.warning('Vendor name is empty for Seller TIN: %s', waybill.seller_tin)
                    raise UserError('Vendor name is empty for Seller TIN: %s' % waybill.seller_tin)

            # Create purchase order based on waybill data
            order_lines = []
            for line in waybill.line_ids:
                # Create product if not exists
                price = float(line.price)/float(line.koef or 1)
                product = self._get_or_create_product(
                    line.bar_code,  # Pass barcode to the method
                    line.w_name,    # Pass product name
                    line.unit_id,   # Pass unit_id
                    product_id=line.product_id.id if line.product_id else None,  # Pass existing product ID if provided
                    product_category_id=line.product_category_id,
                    koef=line.koef if line.koef else 1,
                    price=price
                )
                
                # Add to order lines
                price = float(line.price)/float(line.koef or 1)
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_qty': float(line.quantity) * float(line.koef or 1),
                    'price_unit': price,
                }))

            # Create purchase order
            purchase_order = self.env['purchase.order'].create({
                'partner_id': vendor.id,
                'date_order': fields.Date.today(),
                'order_line': order_lines,
            })

            # Create vendor bill based on the purchase order
            bill_lines = []
            for line in purchase_order.order_line:
                bill_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_qty,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, self._get_tax_ids(line.vat_type) if hasattr(line, 'vat_type') else [])],
                }))

            vendor_bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': vendor.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': bill_lines,
            })

            # Create a combined invoice record
            combined_invoice = self.env['combined.invoice.model'].create({
                'invoice_number': waybill.waybill_number,
                'invoice_id': waybill.waybill_id_number,
            })

            # Create a purchase return from the vendor bill
            return_lines = []
            for line in vendor_bill.invoice_line_ids:
                return_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'tax_ids': line.tax_ids.ids,
                }))

            purchase_return = self.env['account.move'].create({
                'move_type': 'in_refund',
                'partner_id': vendor.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': return_lines,
                'combined_invoice_id': combined_invoice.id,
            })

            # Create delivery to client (Return to Vendor)
            picking_type_out = self.env.ref('stock.picking_type_out')
            customer_location = self.env.ref('stock.stock_location_customers')
            
            # Use vendor's location if available, otherwise default customer location
            partner_loc = vendor.property_stock_customer or customer_location
            
            delivery_picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type_out.id,
                'partner_id': vendor.id,
                'location_id': self.env.ref('stock.stock_location_stock').id, # From Stock
                'location_dest_id': partner_loc.id, # To Vendor/Customer
                'origin': waybill.waybill_number,
            })

            for line in waybill.line_ids:
                 price = float(line.price)/float(line.koef or 1)
                 product = self._get_or_create_product(
                     line.bar_code, 
                     line.w_name, 
                     line.unit_id, 
                     product_id=line.product_id.id if line.product_id else None, 
                     product_category_id=line.product_category_id,
                     koef=line.koef if line.koef else 1,
                     price=price
                 )
                 
                 quantity = float(line.quantity) * float(line.koef or 1)
                 
                 self.env['stock.move'].create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'product_uom': product.uom_id.id,
                    'picking_id': delivery_picking.id,
                    'location_id': delivery_picking.location_id.id,
                    'location_dest_id': delivery_picking.location_dest_id.id,
                 })

            delivery_picking.action_confirm()
            delivery_picking.action_assign()
            # Auto-validate if needed, or leave it for manual validation:
            # delivery_picking.button_validate()

            # Update waybill status
            waybill.write({
                'mdgomareoba': 'gadatanili',
                'vendor_bill_id': vendor_bill.id,
                'refund_id': purchase_return.id,
                'invoice_id': purchase_return.id,
                'purchase_order_id': purchase_order.id,
                'delivery_picking_id': delivery_picking.id
            })

            # Return action to open the newly created purchase return
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': purchase_return.id,
                'target': 'current',
            }

        return True



    def create_inventory_receipt(self):
        for waybill in self:
            if waybill.mdgomareoba == 'gadatanili':
                raise UserError("ზედნადები უკვე გადატანილია!")
            dest_location = waybill.stockId1
                        # Ensure both source and destination locations are provided
            if not dest_location:
                raise UserError("საწყობის მონიშვნის გარეშე ვერ შექმნით შიდა გადაცემას")
            
    
            # Find or create the partner (customer/vendor) based on the waybill's buyer info
            partner = self.env['res.partner'].search([('vat', '=', waybill.buyer_tin)], limit=1)
            
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': waybill.buyer_name,
                    'vat': waybill.buyer_tin,
                })
            
            # Use the partner's 'property_stock_supplier' as the source location
            source_location = partner.property_stock_supplier
    
            if not source_location:
                raise ValidationError("Source location not found for the supplier (partner). Please ensure the supplier has a default stock location.")
    
            # Create a new inventory receipt
            inventory_receipt = self.env['stock.picking'].create({
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'location_id': source_location.id,  # Partner's stock location
                'location_dest_id': dest_location.id,  # Destination location
                'partner_id': partner.id,  # Set partner as the vendor for incoming receipts
            })
    
            # Create Combined Invoice Model record
            combined_invoice = self.env['combined.invoice.model'].create({
                'invoice_number': waybill.waybill_number,
                'invoice_id': waybill.waybill_id_number,
            })
    
            # Link the Combined Invoice record to the newly created inventory receipt
            inventory_receipt.write({'combined_invoice_id': combined_invoice.id})
    
            # Update waybill with the created inventory receipt ID (if needed)
            waybill.write({'invoice_id': inventory_receipt.id})
    
            # Create stock moves and move lines
            move_lines = []
            for line in waybill.line_ids:
                price = float(line.price)/float(line.koef or 1)
                product = self._get_or_create_product(
                    line.bar_code, 
                    line.w_name, 
                    line.unit_id, 
                    product_id=line.product_id.id if line.product_id else None, 
                    product_category_id=line.product_category_id,
                    koef=line.koef,
                    price=price
                )
                quantity = float(line.quantity) * float(line.koef or 1)
                stock_move = self.env['stock.move'].create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'picking_id': inventory_receipt.id,
                    'location_id': source_location.id,  # Partner's stock location
                    'location_dest_id': dest_location.id,  # Destination location
                    'state': 'draft',
                    'tax_id': self._get_single_tax_id(line.vat_type, 'purchase'),
                })
                move_lines.append({
                    'move_id': stock_move.id,
                    'product_id': product.id,
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                    'result_package_id': False,
                })
    
            if move_lines:
                self.env['stock.move.line'].create(move_lines)
    
            inventory_receipt.action_confirm()
            waybill.write({'mdgomareoba': 'gadatanili'})
    
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': inventory_receipt.id,
                'target': 'current',
            }
    
























    def action_view_linked_document(self):
        self.ensure_one()
        
        domain = []
        if self.vendor_bill_id:
            domain.append(('id', '=', self.vendor_bill_id.id))
        if self.refund_id:
            domain.append(('id', '=', self.refund_id.id))
        if self.customer_invoice_id:
            domain.append(('id', '=', self.customer_invoice_id.id))
            
        # Collect IDs for account.move
        move_ids = []
        if self.vendor_bill_id:
            move_ids.append(self.vendor_bill_id.id)
        if self.refund_id:
            move_ids.append(self.refund_id.id)
        if self.customer_invoice_id:
            move_ids.append(self.customer_invoice_id.id)
            
        # If we have account moves (Bills, Invoices, Refunds)
        if move_ids:
            return {
                'name': 'Linked Documents',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'domain': [('id', 'in', move_ids)],
                'target': 'current',
            }

        # Check for Purchase Order
        if self.purchase_order_id:
            return {
                'name': 'Purchase Order',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': self.purchase_order_id.id,
                'target': 'current',
            }

        # Check for Sale Order
        if self.sale_order_id:
            return {
                'name': 'Sale Order',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.sale_order_id.id,
                'target': 'current',
            }

        # Fallback for generic Invoice ID link
        if self.invoice_id:
            try:
                potential_id = int(self.invoice_id)
                # Check for Stock Picking (Inventory Receipt / Internal Transfer)
                if self.env['stock.picking'].browse(potential_id).exists():
                     return {
                        'name': 'Inventory Transfer',
                        'type': 'ir.actions.act_window',
                        'res_model': 'stock.picking',
                        'view_mode': 'form',
                        'res_id': potential_id,
                        'target': 'current',
                    }
                # Check for Account Move (Legacy fallback)
                if self.env['account.move'].browse(potential_id).exists():
                     return {
                        'name': 'Document',
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.move',
                        'view_mode': 'form',
                        'res_id': potential_id,
                        'target': 'current',
                    }
            except ValueError:
                pass

        # If nothing found
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Warning'),
                'message': _('No linked document found.'),
                'type': 'warning',
                'sticky': False,
            }
        }

class WaybillLine(models.Model):
    _name = 'waybill.line'
    _description = 'Waybill Line'

    waybill_id = fields.Many2one('waybill', string='Waybill', ondelete='cascade')
    product_id = fields.Many2one('product.template', string='Product', ondelete='set null')
    w_name = fields.Char(string='სახელი')
    quantity = fields.Char(string='რაოდენობა')
    price = fields.Char(string='ფასი')
    amount = fields.Char(string='სრული ფასი')
    bar_code = fields.Char(string='ბარ კოდი')
    a_id = fields.Char(string='ID')
    vat_type= fields.Char(string='დაბეგვრის ტიპი')
    status = fields.Char(string='Status')
    quantity_fact = fields.Char(string='Quantity F')
    koef = fields.Float(string='კოეფიციენტი', default=1)
    xarjang = fields.Many2one('account.account', string='დებეტი|დებეტის ანგარიში')
    product_category_id = fields.Many2one('product.category', string='Product Category', help='Product category for this line')
    # Reuse the selection field from ProductTemplate
    unit_id = fields.Selection(selection=[
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
    ], string='ერთეული rs.ge', default='')

    unit_txt = fields.Char(string='სხვა ერთეული')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_id = self.product_id.unit_id
            self.unit_txt = self.product_id.unit_txt
            self.product_category_id = self.product_id.categ_id
            

    










class WaybillLineHistory(models.Model):
    _name = 'waybill.line.history'
    _description = 'Waybill Line History'

    waybill_id = fields.Many2one('waybill', string='Waybill', ondelete='cascade')
    product_id = fields.Many2one('product.template', string='პროდუქტი სისტემაში', ondelete='set null')
    w_name = fields.Char(string='სახელი')
    quantity = fields.Char(string='რაოდენობა')
    price = fields.Char(string='ფასი')
    amount = fields.Char(string='სრული ფასი')
    bar_code = fields.Char(string='ბარ კოდი')
    a_id = fields.Char(string='ID')
    vat_type = fields.Char(string='დაბეგვრის ტიპი')
    status = fields.Char(string='Status')
    quantity_fact = fields.Char(string='Quantity F')
    xarjang = fields.Many2one('account.account', string='დებეტი|დებეტის ანგარიში')
    product_category_id = fields.Many2one('product.category', string='პროდუქციის კატეგორია', help='Product category for this line')

    @api.model
    def create(self, vals):
        record = super(WaybillLineHistory, self).create(vals)
        if record.waybill_id:
            # Update the mdgomareoba field in the related waybill
            if self.env['waybill.line.history'].search_count([('waybill_id', '=', record.waybill_id.id)]) > 0:
                record.waybill_id.write({'mdgomareoba': 'korektirebuli'})
                _logger.info(f"Waybill ID {record.waybill_id.id}: mdgomareoba set to korektirebuli due to new history record creation.")
        return record
        
    @api.model
    def write(self, vals):
        res = super(WaybillLineHistory, self).write(vals)
        # If the write affects the waybill_id, update the mdgomareoba field
        for record in self:
            if record.waybill_id:
                if self.env['waybill.line.history'].search_count([('waybill_id', '=', record.waybill_id.id)]) > 0:
                    record.waybill_id.write({'mdgomareoba': 'korektirebuli'})
                    _logger.info(f"Waybill ID {record.waybill_id.id}: mdgomareoba updated to korektirebuli due to history record modification.")
        return res
