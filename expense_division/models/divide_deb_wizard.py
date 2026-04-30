from odoo import models, fields, api
from odoo.exceptions import UserError


class DivideDebPreset(models.Model):
    _name = 'divide.deb.preset'
    _description = 'შენახული შაბლონი'
    _order = 'name'

    name = fields.Char(string="შაბლონის სახელი", required=True)

    debit_account_ids = fields.Many2many(
        'account.account',
        'preset_debit_account_rel',
        'preset_id',
        'account_id',
        domain="[('code', '=like', '2199%')]",
        string="სადებეტო ანგარიშები",
    )
    credit_account_ids = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="საკრედიტო ანგარიში",
    )
    credit_account_id_1 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჯის ანგარიში",
    )
    credit_account_id_2 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჯის ანგარიში 2",
    )
    credit_account_id_4 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="საკრედიტო ანგარიში 2",
    )
    credit_account_id_5 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჯის ანგარიში 3",
    )
    credit_account_id_6 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჯის ანგარიში 4",
    )


class DivideDebWizard(models.TransientModel):
    _name = 'divide.deb.wizard'
    _description = 'Wizard for Creating Debit and Credit Journal Entries'

    preset_id = fields.Many2one(
        'divide.deb.preset',
        string="შენახული შაბლონი",
        help="აირჩიეთ შენახული შაბლონი ველების ავტომატურად შესავსებად.",
    )

    debit_account_ids = fields.Many2many(
        'account.account',
        domain="[('code', '=like', '2199%')]",
        string="Debit Journals",
        help="Choose accounts that will be used for debit side."
    )

    credit_account_ids = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="Credit Journal",
        help="Choose accounts that will be used for credit side."
    )
    credit_account_id_1 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჯის ანგარიში",
        help="Choose accounts that will be used for credit side."
    )
    credit_account_id_2 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჟის ანგარიში 2",
        help="Choose accounts that will be used for credit side."
    )

    amount = fields.Float(
        string="Amount",
        required=True
    )
    amount_for_one = fields.Float(
        string="Amount for One",
        required=True
    )
    amount_for_two = fields.Float(
        string="Amount for Two",
        required=True
    )

    credit_account_id_4 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="Credit Journal",
        help="Choose accounts that will be used for credit side."
    )
    credit_account_id_5 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჯის ანგარიში",
        help="Choose accounts that will be used for credit side."
    )
    credit_account_id_6 = fields.Many2one(
        'account.account',
        domain="[('code', '=like', '74%')]",
        string="ხარჟის ანგარიში 2",
        help="Choose accounts that will be used for credit side."
    )

    amount_4 = fields.Float(
        string="Amount",
        required=True
    )
    amount_5 = fields.Float(
        string="Amount for One",
        required=True
    )
    amount_6 = fields.Float(
        string="Amount for Two",
        required=True
    )

    @api.onchange('preset_id')
    def _onchange_preset_id(self):
        if self.preset_id:
            preset = self.preset_id
            self.debit_account_ids = preset.debit_account_ids
            self.credit_account_ids = preset.credit_account_ids
            self.credit_account_id_1 = preset.credit_account_id_1
            self.credit_account_id_2 = preset.credit_account_id_2
            self.credit_account_id_4 = preset.credit_account_id_4
            self.credit_account_id_5 = preset.credit_account_id_5
            self.credit_account_id_6 = preset.credit_account_id_6

    def action_save_preset(self):
        self.ensure_one()
        return {
            'name': 'შაბლონის შენახვა',
            'type': 'ir.actions.act_window',
            'res_model': 'divide.deb.preset.save',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,
            },
        }

    def confirm(self):
        self.ensure_one()
        num_debits = len(self.debit_account_ids)
        if num_debits == 0:
            raise UserError("Please select at least one Debit Account.")

        operations = [
            (self.amount, self.credit_account_ids),
            (self.amount_for_one, self.credit_account_id_1),
            (self.amount_for_two, self.credit_account_id_2),
            (self.amount_4, self.credit_account_id_4),
            (self.amount_5, self.credit_account_id_5),
            (self.amount_6, self.credit_account_id_6),
        ]

        line_vals = []

        prec = self.env.company.currency_id.rounding or 0.01

        for amt, acc in operations:
            if not acc or amt == 0:
                continue

            from odoo.tools import float_round

            debit_per_acc = float_round(amt / num_debits, precision_rounding=prec)
            total_allocated_debit = 0.0

            for i, debit_acc in enumerate(self.debit_account_ids):
                if i == num_debits - 1:
                    actual_debit = amt - total_allocated_debit
                else:
                    actual_debit = debit_per_acc
                    total_allocated_debit += actual_debit

                line_vals.append((0, 0, {
                    'name': f'Split Debit: {acc.display_name}',
                    'account_id': debit_acc.id,
                    'debit': actual_debit,
                    'credit': 0.0,
                }))

            line_vals.append((0, 0, {
                'name': f'Split Credit: {acc.display_name}',
                'account_id': acc.id,
                'debit': 0.0,
                'credit': amt,
            }))

        if not line_vals:
            raise UserError("No valid accounts and amounts provided.")

        move = self.env['account.move'].create({
            'journal_id': 25,
            'move_type': 'entry',
            'line_ids': line_vals,
        })

        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }


class DivideDebPresetSave(models.TransientModel):
    _name = 'divide.deb.preset.save'
    _description = 'შაბლონის სახელის შეყვანა'

    name = fields.Char(string="შაბლონის სახელი", required=True)
    wizard_id = fields.Many2one('divide.deb.wizard', string="Wizard")

    def action_confirm_save(self):
        self.ensure_one()
        wizard = self.wizard_id
        if not wizard.exists():
            raise UserError("ვიზარდი ვერ მოიძებნა. სცადეთ თავიდან.")

        self.env['divide.deb.preset'].create({
            'name': self.name,
            'debit_account_ids': [(6, 0, wizard.debit_account_ids.ids)],
            'credit_account_ids': wizard.credit_account_ids.id,
            'credit_account_id_1': wizard.credit_account_id_1.id,
            'credit_account_id_2': wizard.credit_account_id_2.id,
            'credit_account_id_4': wizard.credit_account_id_4.id,
            'credit_account_id_5': wizard.credit_account_id_5.id,
            'credit_account_id_6': wizard.credit_account_id_6.id,
        })

        return {'type': 'ir.actions.act_window_close'}