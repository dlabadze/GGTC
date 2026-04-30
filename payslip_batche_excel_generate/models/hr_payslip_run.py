from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import xlsxwriter
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_generate_excel(self):
        """
        Generate Excel file with Reference and Employee columns for all payslips in the batch.
        """
        if not self.slip_ids:
            raise UserError(_('No payslips found in this batch.'))

        # Create an in-memory output file
        output = io.BytesIO()
        
        # Create workbook
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Payslips')
        
        # Define header format
        header_format = workbook.add_format({
            'font_color': 'black',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        # Define cell format
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
        })
        
        # Write headers
        worksheet.write(0, 0, 'მიმღების ანგარიშის ნომერი', header_format)
        worksheet.write(0, 1, 'მიმღები ბანკის კოდი(არასავალდებულო)', header_format)
        worksheet.write(0, 2, 'მიმღების დასახელება', header_format)
        worksheet.write(0, 3, 'დანიშნულება', header_format)
        worksheet.write(0, 4, 'გადასარიცხი თანხა', header_format)
        worksheet.write(0, 5, 'მიმღების საიდენტიფიკაციო კოდი(არასავალდებულო)', header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 30)
        
        # Group payslips by employee identification_id and sum amounts
        grouped_data = {}
        for slip in self.slip_ids:
            identification_id = slip.employee_id.identification_id if slip.employee_id.identification_id else ''
            
            # Skip if no identification_id
            if not identification_id:
                identification_id = f'NO_ID_{slip.employee_id.id}'  # Use employee ID as fallback
            
            if identification_id not in grouped_data:
                acc_number = slip.employee_id.bank_account_id.acc_number if slip.employee_id.bank_account_id else ''
                # Remove trailing 'GEL' (case-insensitive) from account number
                if acc_number and acc_number.strip().lower().endswith('gel'):
                    acc_number = acc_number.strip()[:-3].strip()
                grouped_data[identification_id] = {
                    'acc_number': acc_number,
                    'bank_code': slip.employee_id.bank_account_id.bank_id.bic if slip.employee_id.bank_account_id.bank_id else '',
                    'employee_name': slip.employee_id.name if slip.employee_id else '',
                    'line_net': 0.0,
                    'identification_id': slip.employee_id.identification_id if slip.employee_id.identification_id else '',
                }
            
            # Sum the line_net amounts for same identification_id
            line_net = slip.line_net if slip.line_net else 0.0
            grouped_data[identification_id]['line_net'] += line_net
        
        # Write data rows
        row = 1
        for identification_id, data in grouped_data.items():
            # Account number column: employee bank account number
            worksheet.write(row, 0, data['acc_number'], cell_format)

            # Bank code
            worksheet.write(row, 1, data['bank_code'], cell_format)

            # Employee column: employee_id name
            worksheet.write(row, 2, data['employee_name'], cell_format)

            # Description
            description = "2/6/1; ხელფასი"
            worksheet.write(row, 3, description, cell_format)

            # Summed line_net
            worksheet.write(row, 4, data['line_net'], cell_format)

            # Identification ID
            worksheet.write(row, 5, data['identification_id'], cell_format)
            
            row += 1
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'payslip_batch_{self.name or "batch"}_{self.id}.xlsx'
        
        # Encode to base64
        excel_file = base64.b64encode(output.read())
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': excel_file,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        _logger.info(f'Excel file generated for payslip batch {self.name}: {filename}')
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

