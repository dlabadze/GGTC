# -*- coding: utf-8 -*-

from odoo import models, fields, _

# Partner boolean for "apply 98%": use getattr(partner, 'x_studio_apply_98_percent', False)
# When True: var1 = total_credits * 0.98; when False: var1 = total_credits
APPLY_98_FIELD = 'x_studio_apply_98_percent'


class ShegavatiEmployeeReportWizard(models.TransientModel):
    _name = 'shegavati.employee.report.wizard'
    _description = 'Shegavati Employee Report Wizard'

    end_date = fields.Date(string='End Date', required=True)

    def action_confirm(self):
        self.ensure_one()
        end_date = self.end_date
        Report = self.env['shegavati.employee.report']
        # Delete previous report lines for this run (optional: we create fresh each time)
        # Report.search([]).unlink()  # or scope by end_date if you want to keep history

        partners = self.env['res.partner'].search([
            ('x_studio_start_date_1', '!=', False),
        ])
        account_3130 = self.env['account.account'].search([('code', '=', '3130')], limit=1)
        if not account_3130:
            return self._open_report([])

        vals_list = []
        for partner in partners:
            start_date = partner.x_studio_start_date_1
            if not start_date or start_date > end_date:
                continue
            # Moves in range; then lines with account 3130 and this partner, credits only
            self.env.cr.execute("""
                SELECT COALESCE(SUM(aml.credit), 0)
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE am.date >= %s AND am.date <= %s
                  AND am.state = 'posted'
                  AND aml.account_id = %s
                  AND aml.partner_id = %s
            """, (start_date, end_date, account_3130.id, partner.id))
            total_credits = self.env.cr.fetchone()[0]

            partner_shegavati = getattr(partner, 'x_studio_shegavati', 0) or 0
            apply_98 = partner.x_studio_
            if apply_98:
                var1 = total_credits * 0.98
            else:
                var1 = total_credits
            var2 = partner_shegavati - var1
            shegavati = var2 if var2 > 0 else 0.0

            vals_list.append({
                'start_date': start_date,
                'end_date': end_date,
                'partner_id': partner.id,
                'total_credits': total_credits,
                'shegavati': shegavati,
                'partner_shegavati': partner_shegavati,
                'total_credits_2': var1,
                
            })

        created = Report.create(vals_list)
        return self._open_report(created.ids)

    def _open_report(self, ids):
        return {
            'type': 'ir.actions.act_window',
            'name': _('შეღავათის რეპორტი'),
            'res_model': 'shegavati.employee.report',
            'view_mode': 'list',
            'domain': [('id', 'in', ids)],
            'target': 'current',
        }
