from odoo import models, fields, api

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    journal_entry_date = fields.Date(
        string='Journal Entry Date',
        help="If set, this date will be used as the Accounting Date for all payslips in this batch."
    )
    budget_mux = fields.Char(
        string='ბიუჯეტის მუხლი',
        default="[2/6/1] შრომის ანაზღაურება"
    )