import base64
import io
import xlsxwriter
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CharicxvebiExcelWizard(models.TransientModel):
    _name = 'charicxvebi.excel.wizard'
    _description = 'Generate Excel from Accounting'

    excel_file = fields.Binary('Excel File')
    file_name = fields.Char('File Name')

    def generate_excel(self):
        active_ids = self.env.context.get('active_ids', [])
        moves = self.env['account.move'].browse(active_ids)

        if not moves:
            raise UserError(_("No Journal Entries selected."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Transfer List')

        # Formats
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        text_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        # Headers
        # Headers
        headers = [
            "გამგზავნის ანგარიშის ნომერი",
            "დოკუმენტის ნომერი",
            "მიმღები ბანკის კოდი(არასავალდებულო)",
            "მიმღების ანგარიშის ნომერი",
            "მიმღების დასახელება",
            "მიმღების საიდენტიფიკაციო კოდი",
            "დანიშნულება",
            "თანხა",
            "ხელფასი",
            "გადარიცხვის მეთოდი",
            "დამატებითი ინფორმაცია"
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Set column widths
        worksheet.set_column(0, 0, 25)  # Sender Account
        worksheet.set_column(1, 1, 15)  # Doc Num
        worksheet.set_column(2, 2, 15)  # Bank Code
        worksheet.set_column(3, 3, 25)  # Receiver Account
        worksheet.set_column(4, 4, 30)  # Receiver Name
        worksheet.set_column(5, 5, 25)  # Receiver ID
        worksheet.set_column(6, 6, 40)  # Purpose
        worksheet.set_column(7, 7, 15)  # Amount
        worksheet.set_column(8, 10, 20) # Other columns

        row = 1
        doc_number = 1
        
        # Try to get sender account from the current company
        sender_account = 'GE15BG0000000175520100'
        #if self.env.company.bank_ids:
           # sender_account = self.env.company.bank_ids[0].acc_number or ''

        for move in moves:
            # Filter lines for account 1430
            lines = move.line_ids.filtered(lambda l: l.account_id.code == '1430')
            
            for line in lines:
                partner = line.partner_id
                if not partner:
                    continue

                # Bank Account Logic: Get the first bank account
                bank_acc_number = ''
                bank_bic = ''
                if partner.bank_ids:
                    bank = partner.bank_ids[0]
                    bank_acc_number = bank.acc_number or ''
                    if bank_acc_number.endswith('GEL'):
                        bank_acc_number = bank_acc_number[:-3].strip()
                    if bank.bank_id:
                        bank_bic = bank.bank_id.bic or ''

                # Data mapping
                
                # 1. Sender Account Number (A)
                worksheet.write(row, 0, sender_account, text_format)
                
                # 2. Document Number (B) - Sequential
                worksheet.write(row, 1, doc_number, text_format)
                
                # 3. Receiver Bank Code (C)
                worksheet.write(row, 2, bank_bic, text_format)
                
                # 4. Receiver Account Number (D)
                worksheet.write(row, 3, bank_acc_number, text_format)
                
                # 5. Receiver Name (E)
                worksheet.write(row, 4, partner.name or '', text_format)
                
                # 6. Receiver ID Code (F)
                worksheet.write(row, 5, partner.vat or '', text_format)
                
                # 7. Purpose (G)
                # 7. Purpose (G)
                purpose = "მივლინება - "
                
                if getattr(move, 'x_studio_brdzaneba', False):
                    brdzaneba = move.x_studio_brdzaneba
                    # Use name or display_name
                    if hasattr(brdzaneba, 'name'):
                         purpose += (brdzaneba.name or '')
                    elif hasattr(brdzaneba, 'display_name'):
                         purpose += (brdzaneba.display_name or '')
                         
                    if brdzaneba.date_start and brdzaneba.date_end:
                        start_str = brdzaneba.date_start.strftime('%d.%m.%Y')
                        end_str = brdzaneba.date_end.strftime('%d.%m.%Y')
                        purpose += f" {start_str} - დან {end_str} - მდე"

                worksheet.write(row, 6, purpose, text_format)
                
                # 8. Amount (H)
                worksheet.write(row, 7, line.credit, number_format)
                
                # 9-11. Empty columns (I, J, K)
                worksheet.write(row, 8, '', text_format)
                worksheet.write(row, 9, '', text_format)
                worksheet.write(row, 10, '', text_format)

                row += 1
                doc_number += 1

        workbook.close()
        output.seek(0)
        
        self.excel_file = base64.b64encode(output.read())
        self.file_name = 'Transfers.xlsx'

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=charicxvebi.excel.wizard&id=%s&field=excel_file&download=true&filename=%s' % (self.id, self.file_name),
            'target': 'self',
        }
