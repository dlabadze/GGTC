from odoo import models

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_target_partner_for_setup(self, line, account_id):
        rules = self.env['hr.payslip.account.filter'].search([])
        employee_partner = (
                self.employee_id.work_contact_id or
                self.employee_id.user_id.partner_id or
                self.employee_id.user_partner_id
        )
        for rule in rules:
            if account_id in rule.account_ids.ids:
                if line.salary_rule_id.category_id.code in rule.category_ids.mapped('code'):
                    return rule.partner_id or employee_partner
                    
        # Fallback to standard Odoo logic
        if getattr(self, 'company_id', False) and not self.company_id.batch_payroll_move_lines and line.code == "NET":
            return self.employee_id.work_contact_id
        return line.partner_id

    def _prepare_line_values(self, line, account_id, date, debit, credit):
        res = super()._prepare_line_values(line, account_id, date, debit, credit)
        target_partner = self._get_target_partner_for_setup(line, account_id)
        target_partner_id = target_partner.id if target_partner else False
        if target_partner_id:
            res['partner_id'] = target_partner_id
        return res

    def _get_existing_lines(self, line_ids, line, account_id, debit, credit):
        existing_lines = super()._get_existing_lines(line_ids, line, account_id, debit, credit)
        target_partner = self._get_target_partner_for_setup(line, account_id)
        target_partner_id = target_partner.id if target_partner else False
        
        for existing_line in existing_lines:
            if existing_line.get('partner_id') == target_partner_id:
                yield existing_line