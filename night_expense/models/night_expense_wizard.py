from odoo import models, fields, api
from odoo.exceptions import UserError


class NightExpenseWizard(models.TransientModel):
    _name = 'night.expense.wizard'
    _description = 'ღამის ხარჯების გადანაწილება'

    partner_id = fields.Many2one(
        'res.partner',
        string="პარტნიორი",
        required=True,
        help="აირჩიეთ პარტნიორი რომელზეც გადავა ღამის ხარჯი (3110.01 კრედიტი).",
    )
    move_id = fields.Many2one(
        'account.move',
        string="საბუღალტრო ჩანაწერი",
    )

    def action_confirm(self):
        self.ensure_one()
        move = self.move_id
        if not move:
            raise UserError("საბუღალტრო ჩანაწერი ვერ მოიძებნა.")

        night_lines = move.line_ids.filtered(
            lambda l: l.account_id.code
            and l.account_id.code.startswith('7451')
            and len(l.account_id.code.split('.')) >= 3
            and l.account_id.code.split('.')[-1] == '2'
        )

        if not night_lines:
            raise UserError("ღამის ხარჯის ანგარიშები (7451.XX.2) ვერ მოიძებნა ამ ჩანაწერში.")

        employee_line = move.line_ids.filtered(
            lambda l: l.account_id.code and l.account_id.code.startswith('1430')
        )
        employee_partner = employee_line[0].partner_id if employee_line else False

        total_night = sum(night_lines.mapped('debit'))
        if total_night == 0:
            raise UserError("ღამის ხარჯების თანხა 0-ია.")

        if move.state != 'draft':
            move.button_draft()

        account_1430 = self.env['account.account'].search(
            [('code', '=like', '1430%')], limit=1
        )
        account_3110 = self.env['account.account'].search(
            [('code', '=like', '3110.01%')], limit=1
        )

        if not account_1430:
            raise UserError("ანგარიში 1430 ვერ მოიძებნა.")
        if not account_3110:
            raise UserError("ანგარიში 3110.01 ვერ მოიძებნა.")

        new_lines = [
            (0, 0, {
                'name': 'ღამის ხარჯი — თანამშრომელი',
                'account_id': account_1430.id,
                'partner_id': employee_partner.id if employee_partner else False,
                'debit': total_night,
                'credit': 0.0,
            }),
            (0, 0, {
                'name': 'ღამის ხარჯი — პარტნიორი',
                'account_id': account_3110.id,
                'partner_id': self.partner_id.id,
                'debit': 0.0,
                'credit': total_night,
            }),
        ]

        move.write({'line_ids': new_lines})

        return {
            'name': 'საბუღალტრო ჩანაწერი',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }
