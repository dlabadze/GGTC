from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.model_create_multi
    def create(self, vals_list):
        # Logic before creation
        records = super(HrContract, self).create(vals_list)
        paid_leave_id = self.env['hr.leave.type'].sudo().search([('name', '=', 'ანაზღაურებადი შვებულება')], limit=1)
        bulletin_id = self.env['hr.leave.type'].sudo().search([('name', '=', 'ბიულეტენი')], limit=1)
        accrual_plan_id = self.env['hr.leave.accrual.plan'].sudo().search([('name', '=', 'ანაზღაურებადი შვებულება')], limit=1)
        bulletin_accrual_plan_id = self.env['hr.leave.accrual.plan'].sudo().search([('name', '=', 'ბიულეტენი')], limit=1)

        if paid_leave_id and bulletin_id:
            for record in records:
                if record.state == 'open':
                    employee = record.employee_id
                    date_start = record.date_start
                    existing_paid_leave = self.env['hr.leave.allocation'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', paid_leave_id.id),
                        ('date_to', '=', False),
                    ], limit=1)
                    if not existing_paid_leave:
                        rec1 = self.env['hr.leave.allocation'].sudo().create({
                            'employee_id': employee.id,
                            'date_from': date_start,
                            'date_to': False,
                            'state': 'confirm',
                            'number_of_days': 24,
                            'allocation_type': 'accrual',
                            'holiday_status_id': paid_leave_id.id,
                            'accrual_plan_id': accrual_plan_id.id,

                        })
                        rec1.action_approve()
                    existing_bulletin = self.env['hr.leave.allocation'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', bulletin_id.id),
                        ('date_to', '=', False),
                    ], limit=1)

                    # თუ არ არსებობს, ვქმნით
                    if not existing_bulletin:
                        rec2 = self.env['hr.leave.allocation'].sudo().create({
                            'employee_id': employee.id,
                            'date_from': date_start,
                            'date_to': False,
                            'state': 'confirm',
                            'number_of_days': 60,
                            'allocation_type': 'accrual',
                            'holiday_status_id': bulletin_id.id,
                            'accrual_plan_id': bulletin_accrual_plan_id.id,
                        })
                        rec2.action_approve()
        return records

    def write(self, vals):
        pre_state_by_id = {rec.id: rec.state for rec in self}
        result = super(HrContract, self).write(vals)

        paid_leave = self.env['hr.leave.type'].sudo().search([('name', '=', 'ანაზღაურებადი შვებულება')], limit=1)
        bulletin = self.env['hr.leave.type'].sudo().search([('name', '=', 'ბიულეტენი')], limit=1)
        accrual_plan_id = self.env['hr.leave.accrual.plan'].sudo().search([('name', '=', 'ანაზღაურებადი შვებულება')], limit=1)
        bulletin_accrual_plan_id = self.env['hr.leave.accrual.plan'].sudo().search([('name', '=', 'ბიულეტენი')], limit=1)
        if not (paid_leave and bulletin):
            return result

        for record in self:
            if record.state != 'open' or pre_state_by_id.get(record.id) == 'open':
                continue

            employee = record.employee_id
            if not employee:
                continue

            date_start = record.date_start

            # 1. ვამოწმებთ არსებობს თუ არა უკვე ანაზღაურებადი შვებულების აქტიური დარიცხვა
            existing_paid_leave = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', paid_leave.id),
                ('date_to', '=', False),
            ], limit=1)

            # თუ არ არსებობს, ვქმნით
            if not existing_paid_leave:
                rec1 = self.env['hr.leave.allocation'].sudo().create({
                    'employee_id': employee.id,
                    'date_from': date_start,
                    'date_to': False,
                    'state': 'confirm',
                    'number_of_days': 24,
                    'allocation_type': 'accrual',
                    'holiday_status_id': paid_leave.id,
                    'accrual_plan_id': accrual_plan_id.id,
                })
                rec1.action_approve()

            # 2. ვამოწმებთ არსებობს თუ არა უკვე ბიულეტენის აქტიური დარიცხვა
            existing_bulletin = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', bulletin.id),
                ('date_to', '=', False),
            ], limit=1)

            # თუ არ არსებობს, ვქმნით
            if not existing_bulletin:
                rec2 = self.env['hr.leave.allocation'].sudo().create({
                    'employee_id': employee.id,
                    'date_from': date_start,
                    'date_to': False,
                    'state': 'confirm',
                    'number_of_days': 60,
                    'allocation_type': 'accrual',
                    'holiday_status_id': bulletin.id,
                    'accrual_plan_id': bulletin_accrual_plan_id.id,
                })
                rec2.action_approve()
        return result