from odoo import models, fields, api
import logging as _logger
from odoo.exceptions import UserError, ValidationError

class WaybillCustom(models.Model):
    _inherit = 'waybill'

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
    
           # Determine correct picking_type_id based on waybill.stockId1 (Source)
           picking_type_id = self.env.ref('stock.picking_type_in').id
           warehouse = False
           if waybill.stockId1:
               warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', waybill.stockId1.id)], limit=1)
               if warehouse and warehouse.in_type_id:
                   picking_type_id = warehouse.in_type_id.id
               else:
                   incoming_type = self.env['stock.picking.type'].search([
                       ('code', '=', 'incoming'),
                       ('default_location_dest_id', '=', waybill.stockId1.id)
                   ], limit=1)
                   if incoming_type:
                       picking_type_id = incoming_type.id

           # Create Purchase Order if there are valid lines
           purchase_order = False
           if purchase_order_lines:
               po_vals = {
                   'partner_id': partner.id,
                   'order_line': purchase_order_lines,
                   'date_order': fields.Date.today(),
                   'picking_type_id': picking_type_id,
                   'origin': waybill.waybill_number,
               }
               if warehouse:
                   po_vals['warehouse_id'] = warehouse.id
               
               purchase_order = self.env['purchase.order'].create(po_vals)
    
           # Only create the vendor bill if there are invoice lines
           vendor_bill = False
           if invoice_lines:
               bill_vals = {
                   'move_type': 'in_invoice',
                   'partner_id': partner.id,
                   'invoice_date': fields.Date.today(),
                   'car_number': waybill.car_number,
                   'start_location': waybill.start_address,
                   'editable_end_location': waybill.end_address,
                   'driver_id': waybill.driver_tin,
                   'invoice_line_ids': invoice_lines,
               }
               if warehouse:
                   bill_vals['warehouse_id'] = warehouse.id
               
               vendor_bill = self.env['account.move'].create(bill_vals)
    
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
                    'picked': True,
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

            # Create lines for the purchase return (refund) directly from waybill data
            return_lines = []
            for line in waybill.line_ids:
                # Get or create product if not exists
                price = float(line.price) / float(line.koef or 1)
                product = self._get_or_create_product(
                    line.bar_code,
                    line.w_name,
                    line.unit_id,
                    product_id=line.product_id.id if line.product_id else None,
                    product_category_id=line.product_category_id,
                    koef=line.koef if line.koef else 1,
                    price=price
                )
                
                # Add to refund lines
                quantity = float(line.quantity) * float(line.koef or 1)
                return_lines.append((0, 0, {
                    'product_id': product.id,
                    'quantity': quantity,
                    'price_unit': price,
                    'tax_ids': [(6, 0, self._get_tax_ids(line.vat_type, 'purchase') if hasattr(line, 'vat_type') else [])],
                }))

            # Create a combined invoice record
            combined_invoice = self.env['combined.invoice.model'].create({
                'invoice_number': waybill.waybill_number,
                'invoice_id': waybill.waybill_id_number,
            })

            # Create the purchase return (refund) document
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
                'refund_id': purchase_return.id,
                'invoice_id': purchase_return.id,
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
                    # 'picked': True,
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
