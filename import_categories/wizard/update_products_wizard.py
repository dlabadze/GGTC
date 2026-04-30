from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import openpyxl


class UpdateProductsWizard(models.TransientModel):
    _name = 'update.products.wizard'
    _description = 'Update Products Wizard'
    
    product_type = fields.Selection(
        selection=[
            ('1', 'Product Variant (product.product)'),
            ('2', 'Product Template (product.template)'),
        ],
        string='Product Type',
        required=True,
        default='1',
    )
    
    excel_file = fields.Binary(
        string='Excel File',
        required=True,
        help='Upload an Excel file (.xlsx or .xls)',
    )
    
    file_name = fields.Char(
        string='File Name',
    )
    
    def action_update_products(self):
        """Process the uploaded Excel file and update products
        Column A: default_code (to search product)
        Column B: x_studio_cpv (if not empty)
        Column E, F, G: category hierarchy
        Column H: name
        """
        self.ensure_one()
        
        if not self.excel_file:
            raise UserError(_('Please upload an Excel file.'))
        
        # Determine which model to use
        if self.product_type == '1':
            product_model = 'product.product'
        else:
            product_model = 'product.template'
        
        try:
            # Decode the Excel file
            file_data = base64.b64decode(self.excel_file)
            workbook = openpyxl.load_workbook(io.BytesIO(file_data))
            sheet = workbook.active
            
            updated_count = 0
            not_found_count = 0
            
            # Iterate through rows (starting from row 2 to skip header)
            for row in sheet.iter_rows(min_row=2, values_only=True):
                # Column A is index 0 - default_code
                column_a = row[0] if len(row) > 0 else None
                # Column B is index 1 - x_studio_cpv
                column_b = row[1] if len(row) > 1 else None
                # Column E is index 4 - category level 1
                column_e = row[4] if len(row) > 4 else None
                # Column F is index 5 - category level 2
                column_f = row[5] if len(row) > 5 else None
                # Column G is index 6 - category level 3
                column_g = row[6] if len(row) > 6 else None
                # Column H is index 7 - product name
                column_h = row[7] if len(row) > 7 else None
                
                # Skip if column A is empty (need default_code to search)
                if not column_a:
                    continue
                
                # Search for product by default_code
                product = self.env[product_model].search([
                    ('default_code', '=', column_a)
                ], limit=1)
                
                if not product:
                    not_found_count += 1
                    continue
                
                # Prepare update values
                update_vals = {}
                
                # Update name if column H exists
                if column_h:
                    update_vals['name'] = column_h
                
                # Update x_studio_cpv if column B exists and is not empty
                if column_b:
                    # Search for cpv_code record
                    cpv_code = self.env['cpv.code'].search([
                        ('code', '=', str(column_b))
                    ], limit=1)
                    if cpv_code:
                        update_vals['x_studio_cpv'] = cpv_code.id
                
                # Find category based on E, F, G hierarchy
                category = None
                if column_g:
                    # Try to find category G with parent F and grandparent E
                    if column_f and column_e:
                        # Find grandparent E
                        grandparent = self.env['product.category'].search([
                            ('name', '=', column_e)
                        ], limit=1)
                        if grandparent:
                            # Find parent F with grandparent E
                            parent = self.env['product.category'].search([
                                ('name', '=', column_f),
                                ('parent_id', '=', grandparent.id),
                            ], limit=1)
                            if parent:
                                # Find category G with parent F
                                category = self.env['product.category'].search([
                                    ('name', '=', column_g),
                                    ('parent_id', '=', parent.id),
                                ], limit=1)
                    elif column_f:
                        # Find parent F
                        parent = self.env['product.category'].search([
                            ('name', '=', column_f)
                        ], limit=1)
                        if parent:
                            # Find category G with parent F
                            category = self.env['product.category'].search([
                                ('name', '=', column_g),
                                ('parent_id', '=', parent.id),
                            ], limit=1)
                    else:
                        # Find category G without parent
                        category = self.env['product.category'].search([
                            ('name', '=', column_g)
                        ], limit=1)
                elif column_f:
                    # If no G, use F as category
                    if column_e:
                        grandparent = self.env['product.category'].search([
                            ('name', '=', column_e)
                        ], limit=1)
                        if grandparent:
                            category = self.env['product.category'].search([
                                ('name', '=', column_f),
                                ('parent_id', '=', grandparent.id),
                            ], limit=1)
                    else:
                        category = self.env['product.category'].search([
                            ('name', '=', column_f)
                        ], limit=1)
                elif column_e:
                    # If no G or F, use E as category
                    category = self.env['product.category'].search([
                        ('name', '=', column_e)
                    ], limit=1)
                
                if category:
                    update_vals['categ_id'] = category.id
                
                # Update product if there are values to update
                if update_vals:
                    product.write(update_vals)
                    updated_count += 1
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Updated %s products, %s not found') % (updated_count, not_found_count),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_('Error processing Excel file: %s') % str(e))
