from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BudgetPaymentWizard(models.TransientModel):
    _name = 'budget.payment.wizard'
    _description = 'Budget Line Payment Wizard'

    st_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line',
        required=True,
        readonly=True,
    )
    transaction_amount = fields.Monetary(
        string='Transaction Amount',
        related='st_line_id.amount',
        currency_field='currency_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='st_line_id.currency_id',
        readonly=True,
    )

    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='ბიუჯეტი',
        required=True,
    )
    budget_line_id = fields.Many2one(
        'budget.line',
        string='ბიუჯეტის ხაზი',
        required=True,
        domain="[('budget_analytic_id', '=', budget_analytic_id)]",
    )

    current_paim_am = fields.Monetary(
        string='მიმდ. გადახდილი',
        compute='_compute_current_paim_am',
        currency_field='currency_id',
        readonly=True,
    )
    new_paim_am = fields.Monetary(
        string='ახ. გადახდილი',
        compute='_compute_new_paim_am',
        currency_field='currency_id',
        readonly=True,
    )

    @api.depends('budget_line_id', 'budget_line_id.paim_am')
    def _compute_current_paim_am(self):
        for w in self:
            w.current_paim_am = w.budget_line_id.paim_am or 0.0

    @api.depends('current_paim_am', 'transaction_amount')
    def _compute_new_paim_am(self):
        for w in self:
            w.new_paim_am = w.current_paim_am + abs(w.transaction_amount or 0.0)

    def action_confirm(self):
        self.ensure_one()
        if not self.budget_line_id:
            raise UserError('Please select a Budget Line.')
        self.budget_line_id.write({'paim_am': self.new_paim_am})
        _logger.info(
            'Updated budget.line %s: paim_am from %s to %s (transaction: %s)',
            self.budget_line_id.id,
            self.current_paim_am,
            self.new_paim_am,
            self.transaction_amount,
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
