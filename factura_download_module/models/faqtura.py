from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
import requests

class FAQTURI(models.Model):
    _name = 'faqturi'
    _description = 'FAQTURI Model'

    invoice_id = fields.Char(string='ფაქტურის ID', default='N/A')
    series = fields.Char(string='სერია', default='N/A')
    number = fields.Char(string='ფაქტურის ნომერი', default='N/A')
    registration_date = fields.Date(string='რეგისტრაციის თარიღი', default=datetime.today())
    operation_date = fields.Date(string='ოპერაციის თარიღი', default=datetime.today())
    organization_name = fields.Char(string='ორგანიზაციის სახელი', default='N/A')
    sa_ident_no = fields.Char(string='საიდენტიფიკაციო ნომერი')
    tanxa = fields.Char(string='თანხა', default='N/A')
    vat = fields.Float(string='დღგ-ს თანხა', default=0.0)
    buyer_un_id = fields.Char(string='მყიდველსი საიდენტიფიკაციო', default='N/A')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    status = fields.Integer(string='Status', default=0)
    status_text = fields.Text(string='Status Text', compute='_compute_status_text')
    mdgomareoba = fields.Selection([
        ('korektirebuli', 'კორექტირებული'),
        ('gadatanili', 'გატარებული'),
        ('araferi', 'გამოწერილი')
    ], string='მდგომარეობა', default='araferi')
    waybill_type = fields.Selection([
        ('buyer', 'მყიდველის გზამკვლევი'),
        ('seller', 'გაყიდვის გზამკვლევი')
    ], string='გზამკვლევის ტიპი')
    xarjang = fields.Many2one('account.account', string='დებეტ/კრედიტის ანგარიში', help="Account to use for invoicing")
    document_ids = fields.One2many('faqtura.document', 'faqtura_line_id', string='Documents')
    line_ids = fields.One2many('faqtura.line', 'faqturi_id', string='Lines')

    def create_invoice_or_bill(self):
        """Creates either a vendor bill or customer invoice based on the waybill type."""
        for record in self:
            # Check if the invoice has already been processed
            if record.mdgomareoba == 'gadatanili':
                raise UserError("ფაქტურა უკვე გატარებულია!")

            # Determine the move type (out_invoice or in_invoice)
            move_type = 'out_invoice' if record.waybill_type == 'seller' else 'in_invoice'
    
            # Search or create the partner based on VAT
            partner = self.env['res.partner'].search([('vat', '=', record.sa_ident_no)], limit=1)
            if not partner:
                if not record.organization_name or record.organization_name == 'N/A':
                    raise UserError(f"ორგანიზაციის სახელი არ არის მითითებული. გთხოვთ, შეამოწმოთ ფაქტურის მონაცემები.")
                partner = self.env['res.partner'].create({
                    'name': record.organization_name,
                    'vat': record.sa_ident_no,
                })
    
            # Set default account based on move_type
            default_account = self._get_default_account(move_type)
    
            # Validate that there are lines to process
            if not record.line_ids:
                raise UserError("ფაქტურას არ აქვს ხაზები. გთხოვთ, დაამატოთ ხაზები გაგრძელებამდე.")
    
            # Create the account move (invoice or bill)
            move_vals = {
                'move_type': move_type,
                'partner_id': partner.id,
                'invoice_date': record.operation_date,
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': False,
                        'name': line.GOODS,
                        'quantity': line.G_NUMBER if line.G_NUMBER > 0 else 1,
                        'price_unit': (line.FULL_AMOUNT / line.G_NUMBER) if line.G_NUMBER else (line.FULL_AMOUNT / 1),
                        'tax_ids': [(6, 0, self._get_tax_ids(line.VAT_TYPE, move_type))],
                        'account_id': line.xarjang.id if line.xarjang else default_account.id,
                    }) for line in record.line_ids
                ]
            }

            try:
                move = self.env['account.move'].create(move_vals)
        
                # Create the combined invoice record and link to the account move
                combined_invoice = self.env['combined.invoice.model'].create({
                    'get_invoice_id': f"{record.series} {record.number}",
                    'account_move_id': move.id,
                })

                # Write the combined_invoice_id on the created account move
                move.write({'combined_invoice_id': combined_invoice.id})
                
                # Update the status to 'gadatanili' after successful processing
                record.write({'mdgomareoba': 'gadatanili'})
        
                # Return an action to open the created invoice/bill
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Invoice/Bill',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'res_id': move.id,
                    'target': 'current',
                }
            except Exception as e:
                # If any error occurs, raise it so the transaction rolls back
                # This ensures no partial invoice/bill is created
                raise UserError(f"შეცდომა ინვოისის/ანგარიშის შექმნისას: {str(e)}")

    

    @api.depends('status')
    def _compute_status_text(self):
        status_map = {
            '-1': "სტატუსი: წაშლილი",
            '0': "სტატუსი: შენახული",
            '1': "სტატუსი: გადაგზავნილი",
            '2': "სტატუსი: დადასტურებული",
            '3': "სტატუსი: კორექტირებული პირველადი",
            '4': "სტატუსი: მაკორექტირებელი",
            '5': "სტატუსი: მაკორექტირებელი გადაგზავნილი",
            '6': "სტატუსი: გადაგზავნილი გაუქმებული",
            '7': "სტატუსი: გაუქმების დადასტურება",
            '8': "სტატუსი: კორექტირებული დადასტურებული"
        }
        for record in self:
            record.status_text = status_map.get(str(record.status), "უცნობი სტატუსი")
    line_ids = fields.One2many('faqtura.line', 'faqturi_id', string='Lines')

    
    @api.depends()  # No need for dependency on user_id
    def _compute_rs_acc(self):
        for record in self:
            record.rs_acc = self.env.user.rs_acc  # Fetch rs_acc directly from the current user

    @api.depends()  # No need for dependency on user_id
    def _compute_rs_pass(self):
        for record in self:
            record.rs_pass = self.env.user.rs_pass

    @api.onchange('xarjang')
    def _onchange_xarjang(self):
        if self.xarjang:
            for line in self.line_ids:
                line.xarjang = self.xarjang

    def _get_tax_ids(self, vat_type, move_type='out_invoice'):
        """
        Fetch the appropriate tax based on vat_type and move_type.
        
        Args:
            vat_type: 0 for 18%, 1 for 0%
            move_type: 'out_invoice' for sales, 'in_invoice' for purchases
        """
        # Determine tax type based on move_type
        tax_type = 'sale' if move_type == 'out_invoice' else 'purchase'
        
        # Fetch the tax based on the vat_type and tax_type
        if vat_type == 1:  # 0% tax
            tax = self.env['account.tax'].search([
                ('name', '=', '0%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        elif vat_type == 0:  # 18% tax
            tax = self.env['account.tax'].search([
                ('name', '=', '18%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        else:
            tax = self.env['account.tax']  # Default to no taxes if vat_type is unknown
    
        return tax.ids if tax else []



    
    def _get_default_account(self, move_type):
        """Returns the default income or expense account based on the move type."""
        if move_type == 'out_invoice':
            # Get the default income account
            account = self.env['account.account'].search([('code', '=', '6110')], limit=1)  # Replace with your income account code
        else:
            # Get the default expense account
            account = self.env['account.account'].search([('code', '=', '7000')], limit=1)  # Replace with your expense account code
    
        if not account:
            raise UserError(f"Default account not found for move type {move_type}. Please configure the accounts.")
        return account





    def get_name_from_tin(self, rs_acc, rs_pass, tin):
        """Fetches the vendor name using a TIN via SOAP request."""
        # SOAP request template
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                       xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <get_name_from_tin xmlns="http://tempuri.org/">
              <su>{rs_acc}</su>
              <sp>{rs_pass}</sp>
              <tin>{tin}</tin>
            </get_name_from_tin>
          </soap:Body>
        </soap:Envelope>"""
    
        # Define the service URL and headers
        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }
    
        try:
            # Send the SOAP request
            response = requests.post(url, data=soap_request, headers=headers)
    
            # Check if the request was successful
            response.raise_for_status()
    
            # Parse the response to extract the result
            start_tag = "<get_name_from_tinResult>"
            end_tag = "</get_name_from_tinResult>"
            start_index = response.text.find(start_tag) + len(start_tag)
            end_index = response.text.find(end_tag)
    
            if start_index != -1 and end_index != -1:
                name = response.text[start_index:end_index].strip()
                print(f"Vendor name: {name}")  # Optional: Debug print
                return name
            else:
                print("Unable to parse vendor name from response.")
                return ""
    
        except requests.exceptions.RequestException as e:
            print(f"Error during SOAP request: {e}")
            return ""





class FAQTURALine(models.Model):
    _name = 'faqtura.line'
    _description = 'FAQTURI Line Model'

    faqturi_id = fields.Many2one('faqturi', string='FaQTURI', required=True, ondelete='cascade')
    GOODS = fields.Char(string='პროდუქტი')
    G_UNIT = fields.Char(string='ერთეული')
    G_NUMBER = fields.Float(string='რაოდენობა')
    FULL_AMOUNT = fields.Float(string='ჯამური ღირებულება')
    DRG_AMOUNT = fields.Float(string='დღგ-ს თანხა')
    AKCIS_ID = fields.Integer(string='AKCIS ID')
    VAT_TYPE = fields.Integer(string='VAT Type')
    SDRG_AMOUNT = fields.Float(string='SDRG Amount')
    xarjang = fields.Many2one('account.account', string='დებეტი|დებეტის ანგარიში')




class FAQTURADocument(models.Model):
    _name = 'faqtura.document'
    _description = 'FAQTURI Document Model'

    faqtura_line_id = fields.Many2one('faqturi', string='FaQTURI Line', required=True, ondelete='cascade')
    document_number = fields.Char(string='ზედნადების ნომერი', required=True)
    date = fields.Date(string='თარიღი', required=True)




