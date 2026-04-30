from odoo import models, fields, api


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    # Related field to access budget_type from budget.analytic
    budget_type = fields.Selection(
        related='budget_analytic_id.budget_type',
        string='Budget Type',
        store=True,
        readonly=True
    )

    # Revenue-specific fields
    approved_plan = fields.Monetary(
        string='დამტკიცებული გეგმა',
        currency_field='currency_id',
        help='Approved Plan Amount'
    )
    contract_amount_revenue = fields.Monetary(
        string='ხელშეკრულების თანხა',
        currency_field='currency_id',
        help='Contract Amount for Revenue'
    )
    diff_plan_contract = fields.Monetary(
        string='სხვაობა (გეგმა-ხელშეკრულების თანხა)',
        compute='_compute_revenue_differences',
        store=True,
        currency_field='currency_id',
        help='Difference: Approved Plan - Contract Amount'
    )
    paid_amount_revenue = fields.Monetary(
        string='გადახდილი თანხა',
        currency_field='currency_id',
        help='Paid Amount for Revenue'
    )
    diff_plan_paid = fields.Monetary(
        string='სხვაობა (გეგმა-გადახდილი თანხა)',
        compute='_compute_revenue_differences',
        store=True,
        currency_field='currency_id',
        help='Difference: Approved Plan - Paid Amount'
    )
    accrued_amount_revenue = fields.Monetary(
        string='დარიცხული თანხა',
        currency_field='currency_id',
        help='Accrued Amount for Revenue'
    )
    diff_plan_accrued = fields.Monetary(
        string='სხვაობა (გეგმა-დარიცხული თანხა)',
        compute='_compute_revenue_differences',
        store=True,
        currency_field='currency_id',
        help='Difference: Approved Plan - Accrued Amount'
    )
    revenue_note = fields.Text(
        string='შენიშვნა',
        help='Notes for Revenue Budget'
    )

    @api.depends('approved_plan', 'contract_amount_revenue', 'paid_amount_revenue', 'accrued_amount_revenue')
    def _compute_revenue_differences(self):
        """Compute differences for revenue budget fields"""
        for record in self:
            record.diff_plan_contract = record.approved_plan - record.contract_amount_revenue
            record.diff_plan_paid = record.approved_plan - record.paid_amount_revenue
            record.diff_plan_accrued = record.approved_plan - record.accrued_amount_revenue
