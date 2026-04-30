from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
from datetime import date

_logger = logging.getLogger(__name__)


class SalaryReport(models.Model):
    _name = 'salary.report'
    _description = 'Salary Report'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', 
        required=True, 
        copy=False, 
        default='New'
    )
    date = fields.Date(string='Date', default=fields.Date.today)
    date_from = fields.Date(
        string='Date From', 
        required=True, 
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Date To', 
        required=True, 
        default=lambda self: fields.Date.today()
    )
    partner_id = fields.Many2one('res.partner', string='Employee')
    include_all_employees = fields.Boolean(
        string='Include All Employees', 
        default=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated')
    ], string='Status', default='draft', copy=False)
    
    line_ids = fields.One2many(
        'salary.report.line', 
        'report_id', 
        string='Report Lines'
    )
    
    # Summary fields
    total_accrued = fields.Float(
        string='Total Accrued', 
        compute='_compute_totals'
    )
    total_paid = fields.Float(
        string='Total Paid', 
        compute='_compute_totals'
    )
    total_balance = fields.Float(
        string='Total Balance', 
        compute='_compute_totals'
    )
    
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company
    )
    
    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('name') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'salary.report') or 'New'
        return super(SalaryReport, self).create(vals)
    
    @api.onchange('include_all_employees')
    def _onchange_include_all_employees(self):
        if self.include_all_employees:
            self.partner_id = False
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.include_all_employees = False
    
    def _compute_totals(self):
        for record in self:
            record.total_accrued = sum(
                record.line_ids.mapped('accrued_amount'))
            record.total_paid = sum(record.line_ids.mapped('paid_amount'))
            record.total_balance = record.total_accrued - record.total_paid
    
    def action_generate_report(self):
        self.ensure_one()
        print('DEBUG: action_generate_report called')
        self.result_ids.unlink()
        partners = self.env['res.partner'].search([('vat', '!=', False)])
        print(f'DEBUG: Found {len(partners)} partners with vat')
        lines = []
        for partner in partners:
            accrued_lines = self.env['salary.import.line'].search([
                ('partner_id', '=', partner.id),
                ('import_id.date', '>=', self.date_from),
                ('import_id.date', '<=', self.date_to),
                ('import_id.state', '=', 'posted'),
            ])
            accrued_salary = sum(accrued_lines.mapped('net_amount'))
            paid_lines = self.env['salary.payment.import.line'].search([
                ('partner_id', '=', partner.id),
                ('import_id.date', '>=', self.date_from),
                ('import_id.date', '<=', self.date_to),
                ('import_id.state', '=', 'posted'),
            ])
            paid_salary = sum(paid_lines.mapped('net_amount'))
            print(f'DEBUG: Partner {partner.name} ({partner.vat}) - Accrued: {accrued_salary}, Paid: {paid_salary}')
            if accrued_salary or paid_salary:
                lines.append((0, 0, {
                    'partner_id': partner.id,
                    'id_number': partner.vat,
                    'accrued_salary': accrued_salary,
                    'paid_salary': paid_salary,
                }))
        print(f'DEBUG: Total lines to create: {len(lines)}')
        self.result_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.salary.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    
    def action_reset_to_draft(self):
        self.ensure_one()
        self.state = 'draft'
        self.line_ids.unlink()
        return True

    def action_import_latest_salaries(self):
        # Find the latest posted salary.import
        latest_import = self.env['salary.import'].search([
            ('state', '=', 'imported')
        ], order='date desc', limit=1)
        if not latest_import:
            raise UserError('ვერ მოიძებნა იმპორტირებული ხელფასები!')
        # Clear existing lines
        self.line_ids.unlink()
        # Add lines from latest import
        for line in latest_import.line_ids:
            self.env['salary.report.line'].create({
                'report_id': self.id,
                'partner_id': line.partner_id.id,
                'opening_balance': line.net_amount,
                'accrued_amount': line.net_amount,
                'paid_amount': 0,
                'closing_balance': line.net_amount
            })
        return True


class SalaryReportLine(models.Model):
    _name = 'salary.report.line'
    _description = 'Salary Report Line'
    
    report_id = fields.Many2one(
        'salary.report', 
        required=True, 
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='Employee', 
        required=True
    )
    partner_vat = fields.Char(
        string='ID Number',
        related='partner_id.vat',
        store=True
    )
    opening_balance = fields.Float(string='Opening Balance')
    accrued_amount = fields.Float(string='Accrued Amount')
    paid_amount = fields.Float(string='Paid Amount')
    closing_balance = fields.Float(string='Closing Balance')
    company_id = fields.Many2one(related='report_id.company_id', store=True)


class SalaryEmployeeReport(models.Model):
    _name = 'salary.employee.report'
    _description = 'Employee Salary Report'

    name = fields.Char(string='სახელი', required=True)
    date_from = fields.Date(string='საწყისი თარიღი', required=True)
    date_to = fields.Date(string='საბოლოო თარიღი', required=True)
    import_id = fields.Many2one('salary.import', string='ხელფასის იმპორტი')
    line_ids = fields.One2many(
        'salary.employee.report.line',
        'report_id',
        string='ხაზები'
    )
    total_accrued_salary = fields.Float(
        string='დარიცხული ხელფასი', 
        compute='_compute_total_salaries'
    )
    total_paid_salary = fields.Float(
        string='გაცემული ხელფასი', 
        compute='_compute_total_salaries'
    )

    @api.depends('line_ids.partner_id', 'date_from', 'date_to')
    def _compute_total_salaries(self):
        for report in self:
            accrued_total = 0.0
            paid_total = 0.0
            
            # Get accrued salary from salary imports
            accrued_imports = self.env['salary.import'].search([
                ('date', '>=', report.date_from),
                ('date', '<=', report.date_to)
            ])
            
            for line in report.line_ids:
                # Calculate accrued salary
                accrued_amount = sum(
                    accrued_imports.mapped('line_ids').filtered(
                        lambda line_item: line_item.partner_id == line.partner_id
                    ).mapped('net_amount')
                )
                accrued_total += accrued_amount
                
                # Calculate paid salary
                paid_imports = self.env['salary.import'].search([
                    ('date', '>=', report.date_from),
                    ('date', '<=', report.date_to)
                ])
                paid_amount = sum(
                    paid_imports.mapped('line_ids').filtered(
                        lambda line_item: line_item.partner_id == line.partner_id
                    ).mapped('net_amount')
                )
                paid_total += paid_amount
            
            report.total_accrued_salary = accrued_total
            report.total_paid_salary = paid_total


class SalaryEmployeeReportLine(models.Model):
    _name = 'salary.employee.report.line'
    _description = 'Employee Salary Report Line'

    report_id = fields.Many2one(
        'salary.employee.report',
        string='ანგარიში', 
        required=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='თანამშრომელი', 
        required=True
    )
    id_number = fields.Char(
        string='პირადი ნომერი', 
        related='partner_id.vat'
    )
    accrued_salary = fields.Float(
        string='დარიცხული ხელფასი', 
        compute='_compute_salaries'
    )
    paid_salary = fields.Float(
        string='გაცემული ხელფასი', 
        compute='_compute_salaries'
    )
    base_salary_sum = fields.Float(
        string='საბაზისო ხელფასი', 
        compute='_compute_import_line_sums'
    )
    income_tax_sum = fields.Float(
        string='საშემოსავლო', 
        compute='_compute_import_line_sums'
    )
    pension_sum = fields.Float(
        string='პენსია', 
        compute='_compute_import_line_sums'
    )
    net_amount_sum = fields.Float(
        string='ხელზე მისაცემი', 
        compute='_compute_import_line_sums'
    )

    @api.depends('partner_id', 'report_id.date_from', 'report_id.date_to')
    def _compute_salaries(self):
        for line in self:
            # Calculate total accrued salary for all months in range
            accrued_imports = self.env['salary.import'].search([
                ('date', '>=', line.report_id.date_from),
                ('date', '<=', line.report_id.date_to),
                ('state', 'in', ['imported', 'posted'])
            ])
            
            # Sum up all accrued amounts for this employee
            line.accrued_salary = sum(
                accrued_imports.mapped('line_ids').filtered(
                    lambda l: l.partner_id == line.partner_id
                ).mapped('net_amount')
            )

            # Calculate total paid salary for all months in range
            paid_imports = self.env['salary.payment.import'].search([
                ('date', '>=', line.report_id.date_from),
                ('date', '<=', line.report_id.date_to),
                ('state', 'in', ['imported', 'posted'])
            ])
            
            # Sum up all paid amounts for this employee
            line.paid_salary = sum(
                paid_imports.mapped('line_ids').filtered(
                    lambda l: l.partner_id == line.partner_id
                ).mapped('net_amount')
            )

    @api.depends('partner_id', 'report_id.date_from', 'report_id.date_to')
    def _compute_import_line_sums(self):
        for line in self:
            # Get all import lines for this employee in date range
            import_lines = self.env['salary.import.line'].search([
                ('partner_id', '=', line.partner_id.id),
                ('import_id.date', '>=', line.report_id.date_from),
                ('import_id.date', '<=', line.report_id.date_to),
                ('import_id.state', 'in', ['imported', 'posted'])
            ])
            
            # Sum up all amounts
            line.base_salary_sum = sum(import_lines.mapped('base_salary'))
            line.income_tax_sum = sum(import_lines.mapped('income_tax'))
            line.pension_sum = sum(import_lines.mapped('pension'))
            line.net_amount_sum = sum(import_lines.mapped('net_amount'))


class EmployeeSalaryReportLine(models.Model):
    _name = 'employee.salary.report.line'
    _description = 'Employee Salary Report Line'
    _order = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='თანამშრომელი', required=True)
    id_number = fields.Char(string='პირადი ნომერი', related='partner_id.vat', store=True)
    accrued_salary = fields.Float(string='დარიცხული ხელფასი', compute='_compute_salaries', store=True)
    paid_salary = fields.Float(string='გაცემული ხელფასი', compute='_compute_salaries', store=True)
    date_from = fields.Date(string='საწყისი თარიღი', required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='საბოლოო თარიღი', required=True, default=fields.Date.today)

    @api.depends('partner_id', 'date_from', 'date_to')
    def _compute_salaries(self):
        for record in self:
            # Get accrued salary from salary imports
            accrued_imports = self.env['salary.import'].search([
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
                ('state', '=', 'imported')
            ])
            record.accrued_salary = sum(
                accrued_imports.mapped('line_ids').filtered(
                    lambda line: line.partner_id == record.partner_id
                ).mapped('net_amount')
            )

            # Get paid salary from salary payment imports
            paid_imports = self.env['salary.payment.import'].search([
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
                ('state', '=', 'imported')
            ])
            record.paid_salary = sum(
                paid_imports.mapped('line_ids').filtered(
                    lambda line: line.partner_id == record.partner_id
                ).mapped('net_amount')
            )

    @api.model
    def _cron_update_salary_report(self):
        """Cron job to update salary report lines"""
        today = fields.Date.today()
        date_from = today.replace(day=1)
        date_to = today

        # Get all employees with VAT numbers
        employees = self.env['res.partner'].search([('vat', '!=', False)])

        # Create or update report lines for each employee
        for employee in employees:
            existing_line = self.search([
                ('partner_id', '=', employee.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to)
            ], limit=1)

            if not existing_line:
                self.create({
                    'partner_id': employee.id,
                    'date_from': date_from,
                    'date_to': date_to
                })

def post_init_hook(cr, registry):
    from odoo.api import Environment
    env = Environment(cr, SUPERUSER_ID, {})
    today = date.today()
    date_from = today.replace(day=1)
    date_to = today
    EmployeeSalaryReportLine = env['employee.salary.report.line']
    partners = env['res.partner'].search([
        ('vat', '!=', False)
    ])
    for partner in partners:
        EmployeeSalaryReportLine.create({
            'partner_id': partner.id,
            'date_from': date_from,
            'date_to': date_to,
        })

class EmployeeSalaryReportWizard(models.TransientModel):
    _name = 'employee.salary.report.wizard'
    _description = 'Employee Salary Report Wizard'

    date_from = fields.Date(string='საწყისი თარიღი', required=True, default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(string='საბოლოო თარიღი', required=True, default=date.today)
    result_ids = fields.One2many('employee.salary.report.wizard.line', 'wizard_id', string='ანგარიში')

    def action_generate_report(self):
        self.ensure_one()
        self.result_ids.unlink()
        partners = self.env['res.partner'].search([('vat', '!=', False)])
        lines = []
        for partner in partners:
            accrued_lines = self.env['salary.import.line'].search([
                ('partner_id', '=', partner.id),
                ('import_id.date', '>=', self.date_from),
                ('import_id.date', '<=', self.date_to),
                ('import_id.state', '=', 'posted'),
            ])
            accrued_salary = sum(accrued_lines.mapped('net_amount'))
            paid_lines = self.env['salary.payment.import.line'].search([
                ('partner_id', '=', partner.id),
                ('import_id.date', '>=', self.date_from),
                ('import_id.date', '<=', self.date_to),
                ('import_id.state', '=', 'posted'),
            ])
            paid_salary = sum(paid_lines.mapped('net_amount'))
            if accrued_salary or paid_salary:
                lines.append((0, 0, {
                    'partner_id': partner.id,
                    'id_number': partner.vat,
                    'accrued_salary': accrued_salary,
                    'paid_salary': paid_salary,
                }))
        self.result_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.salary.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

class EmployeeSalaryReportWizardLine(models.TransientModel):
    _name = 'employee.salary.report.wizard.line'
    _description = 'Employee Salary Report Wizard Line'

    wizard_id = fields.Many2one('employee.salary.report.wizard', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='თანამშრომელი', required=True)
    id_number = fields.Char(string='პირადი ნომერი')
    accrued_salary = fields.Float(string='დარიცხული ხელფასი')
    paid_salary = fields.Float(string='გაცემული ხელფასი') 