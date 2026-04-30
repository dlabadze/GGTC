from email.policy import default

from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    journal_entry_date = fields.Date(
        string='Journal Entry Date',
        help="Force a specific date for the Journal Entry of this payslip."
    )
    budget_mux = fields.Char(
        string='ბიუჯეტის მუხლი',
        default="[2/6/1] შრომის ანაზღაურება",
        compute='_compute_budget_mux',
        store=True,
        readonly=False,
        precompute=True
    )

    @api.depends('payslip_run_id.budget_mux')
    def _compute_budget_mux(self):
        for slip in self:
            if slip.payslip_run_id and slip.payslip_run_id.budget_mux:
                slip.budget_mux = slip.payslip_run_id.budget_mux

    def _action_create_account_move(self):
        res = super(HrPayslip, self)._action_create_account_move()
        for slip in self:
            target_date = slip.journal_entry_date or (
                    slip.payslip_run_id and slip.payslip_run_id.journal_entry_date)
            target_mux = slip.budget_mux or (
                    slip.payslip_run_id and slip.payslip_run_id.budget_mux)
            move = slip.move_id
            if target_date:
                if move and move.date != target_date:
                    if move.state == 'draft':
                        move.write({'date': target_date})

                    elif move.state == 'posted':
                        move.button_draft()
                        move.write({'date': target_date})
            
            if target_mux:
                if move and move.x_studio_muxli_hr != target_mux:
                    move.write({'x_studio_muxli_hr': target_mux})

        return res