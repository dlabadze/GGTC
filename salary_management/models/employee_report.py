from odoo import models, fields, tools, api, _

class EmployeeReport(models.Model):
    _name = 'employee.report'
    _description = 'Employee Report'
    _auto = False  # it a SQL view, not a table ;))

    # Employee Info
    partner_id = fields.Many2one('res.partner', string='Employee', readonly=True)
    partner_name = fields.Char(string='Employee Name', readonly=True)
    partner_vat = fields.Char(string='ID Number', readonly=True)
    
    # Salary Info
    total_salary = fields.Float(string='Total Salary', readonly=True)
    base_salary = fields.Float(string='Base Salary', readonly=True)
    net_amount = fields.Float(string='Net Amount', readonly=True)
    pension = fields.Float(string='Pension', readonly=True)
    income_tax = fields.Float(string='Income Tax', readonly=True)
    company_tax = fields.Float(string='Company Tax', readonly=True)
    
    # Import Info
    import_date = fields.Date(string='Last Import Date', readonly=True)
    import_ref = fields.Char(string='Last Import Reference', readonly=True)
    import_state = fields.Selection([
        ('draft', 'Draft'),
        ('imported', 'Imported'),
        ('posted', 'Posted')
    ], string='Status', readonly=True)
    
    # Statistics
    salary_count = fields.Integer(string='Salary Records Count', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Create the SQL view for employee report"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    row_number() OVER () as id,
                    sl.partner_id,
                    rp.name as partner_name,
                    sl.partner_vat,
                    SUM(sl.total_salary) as total_salary,
                    SUM(sl.base_salary) as base_salary,
                    SUM(sl.net_amount) as net_amount,
                    SUM(sl.pension) as pension,
                    SUM(sl.income_tax) as income_tax,
                    SUM(sl.company_tax) as company_tax,
                    MAX(si.date) as import_date,
                    MAX(si.name) as import_ref,
                    MAX(si.state) as import_state,
                    COUNT(sl.id) as salary_count,
                    sl.company_id
                FROM salary_import_line sl
                LEFT JOIN salary_import si ON sl.import_id = si.id
                LEFT JOIN res_partner rp ON sl.partner_id = rp.id
                WHERE sl.partner_id IS NOT NULL
                GROUP BY sl.partner_id, rp.name, sl.partner_vat, sl.company_id
                ORDER BY rp.name
            )
        """ % self._table)
