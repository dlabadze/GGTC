from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_fix_pension_accounts(self):

        applicable_moves = self.sudo().search([
            ('id', 'in', self.ids),
            ('date', '>=', '2026-04-01'),
            ('date', '<=', '2026-04-30'),
            ('journal_id', '=', 30)
        ])

        if not applicable_moves:
            raise UserError(_(
                "არჩეულ ჩანაწერებში ვერ მოიძებნა 2026 წლის აპრილის Salaries (Journal 30) ჩანაწერები."
            ))

        account_debit = self.env['account.account'].sudo().search([('code', '=', '3370')], limit=1)
        account_credit = self.env['account.account'].sudo().search([('code', '=', '3371')], limit=1)

        if not account_debit:
            raise UserError(_("ანგარიში კოდით 3370 ვერ მოიძებნა."))
        if not account_credit:
            raise UserError(_("ანგარიში კოდით 3371 ვერ მოიძებნა."))

        fixed_count = 0
        for move in applicable_moves:
            target_lines = move.line_ids.filtered(lambda l: l.name == 'საპენსიო 4%')
            
            if not target_lines:
                continue

            is_posted = move.state == 'posted'
            if is_posted:
                move.button_draft()

            for line in target_lines:
                if line.debit > 0:
                    line.account_id = account_debit
                elif line.credit > 0:
                    line.account_id = account_credit
                fixed_count += 1

            if is_posted:
                move.action_post()

        if fixed_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('წარმატება'),
                    'message': _('%d სტრიქონი გასწორდა.') % fixed_count,
                    'type': 'success',
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ინფორმაცია'),
                    'message': _('შესაბამისი სტრიქონები ვერ მოიძებნა.'),
                    'type': 'warning',
                },
            }

    def action_fix_pension_partner(self):

        applicable_moves = self.sudo().search([
            ('id', 'in', self.ids),
            ('journal_id', '=', 30)
        ])

        if not applicable_moves:
            raise UserError(_("არჩეულ ჩანაწერებში ვერ მოიძებნა Salaries (Journal 30) ჩანაწერები."))

        account_pension_code = '3370'
        account_ref_code = '3130'

        fixed_count = 0
        for move in applicable_moves:
            target_lines = move.line_ids.filtered(
                lambda l:  l.account_id.code == account_pension_code
            )
            
            if not target_lines:
                continue

            ref_line = move.line_ids.filtered(lambda l: l.account_id.code == account_ref_code)
            
            partners = ref_line.mapped('partner_id')
            if not partners:
                continue
            
            target_partner = partners[0]

            is_posted = move.state == 'posted'
            if is_posted:
                move.button_draft()

            for line in target_lines:
                if not line.partner_id:
                    line.partner_id = target_partner
                    fixed_count += 1

            if is_posted:
                move.action_post()

        if fixed_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('წარმატება'),
                    'message': _('%d სტრიქონზე პარტნიორი განახლდა.') % fixed_count,
                    'type': 'success',
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ინფორმაცია'),
                    'message': _('განსახლები სტრიქონები ან პარტნიორი ვერ მოიძებნა.'),
                    'type': 'warning',
                },
            }
