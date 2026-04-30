from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
import logging

_logger = logging.getLogger(__name__)


class PurchassePlanPreliminary(models.Model):
    _name = 'purchase.plan.preliminary'
    _description = 'Purchase Plan Preliminary'
    _rec_name = 'cpv_name'

    plan_id = fields.Many2one('purchase.plan', string='Purchase Plan', required=True)
    plan_line_id = fields.Many2one(
        'purchase.plan.line',
        string='Purchase Plan Line',
        domain="[('plan_id', '=', plan_id)]"
    )
    new_cpv = fields.Boolean(
        string='ახალი CPV',
    )

    new_cpv_code = fields.Many2one(
        'cpv.code',
        string='CPV Code',
    )

    cpv_name = fields.Char(string='CPV დასახელება', store=True)
    cpv_code = fields.Char(string='CPV კოდი', store=True)
    amount = fields.Monetary(string='სხვაობა', currency_field='currency_id')
    comment = fields.Text(string='კომენტარი')
    currency_id = fields.Many2one('res.currency', string='ვალუტა', required=True)
    line_ids = fields.One2many('purchase.plan.preliminary.line', 'change_id', string='ცვლილებების ხაზები')
    total_changes = fields.Monetary(
        string='ცვლილებების ჯამი',
        compute='_compute_total_changes',
        store=True,
        currency_field='currency_id'
    )
    code_name = fields.Char(
        string='CPV Code',
        compute='_compute_code_name',
        store=True
    )

    @api.depends('plan_line_id', 'new_cpv_code')
    def _compute_code_name(self):
        for record in self:
            if record.plan_line_id:
                record.code_name = record.plan_line_id.display_name
            elif record.new_cpv_code:
                code = record.new_cpv_code.code or ''
                name = record.new_cpv_code.name or ''
                record.code_name = f"{code} {name}".strip()
            else:
                record.code_name = False

    purchase_method_id = fields.Many2one(
        'purchase.method',
        string='შესყიდვის საშუალებები',
        store=True
    )
    purchase_reason_id = fields.Many2one(
        'purchase.reason',
        string='შესყიდვის საფუძველი',
        store=True
    )

    change_amount = fields.Monetary(string='თანხა', currency_field='currency_id')
    change_date = fields.Date(string='თარიღი', required=True, default=fields.Date.context_today)
    change_comment = fields.Text(string='კომენტარი')
    pu_ac_am = fields.Monetary(
        string='არსებული სავარაუდო ღირებულება',
        related='plan_line_id.pu_ac_am',
        store=True,
        currency_field='currency_id',
        readonly=True
    )

    pc_re_am = fields.Monetary(
        string='რესურსი',
        related='plan_line_id.pc_re_am',
        store=True,
        currency_field='currency_id',
        readonly=True
    )

    new_poss_amount = fields.Monetary(
        string='ახალი სავარაუდო ღირებულება',
        compute='_compute_new_amounts',
        store=True,
        currency_field='currency_id'
    )

    new_res = fields.Monetary(
        string='ახალი რესურსი',
        store=True,
        currency_field='currency_id'
    )
    first_line_date = fields.Date(string='Date of First Line', readonly=True)
    first_line_amount = fields.Integer(string='Date of First Line', readonly=True)
    first_line_comment = fields.Char(string='Date of First Line', readonly=True)


    @api.depends('change_amount', 'pu_ac_am', 'pc_re_am')
    def _compute_new_amounts(self):
        for rec in self:
            rec.new_poss_amount = rec.pu_ac_am + rec.change_amount

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        if self.plan_id:
            self.plan_line_id = False
        return {'domain': {'plan_line_id': [('plan_id', '=', self.plan_id.id)]}}

    @api.onchange('plan_line_id')
    def _onchange_plan_line_id(self):
        if self.plan_line_id:

            self.cpv_name = self.plan_line_id.cpv_name
            self.purchase_reason_id = self.plan_line_id.purchase_reason_id if self.plan_line_id.purchase_reason_id else False
            self.currency_id = self.plan_line_id.currency_id if self.plan_line_id.currency_id else False
            self.purchase_method_id = self.plan_line_id.purchase_method_id if self.plan_line_id.purchase_method_id else False

            if hasattr(self.plan_line_id, 'pu_ac_am'):
                self.amount = self.plan_line_id.pu_ac_am
            elif hasattr(self.plan_line_id, 'amount'):
                self.amount = self.plan_line_id.amount

    @api.onchange('change_amount','pc_re_am')
    def _onchange_change_amount(self):
        if self.change_amount and self.pc_re_am:
            if self.pc_re_am < self.change_amount:
                raise UserError('ცვლილების თანხა აღემატება რესურსს')

class PurchassePlanPreliminaryLine(models.Model):
    _name = 'purchase.plan.preliminary.line'
    _description = 'Purchase Plan Changes Line'
    _order = 'date desc, id desc'

    change_id = fields.Many2one('purchase.plan.preliminary', string='ცვლილება', required=True, ondelete='cascade')
    date = fields.Date(string='თარიღი', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='თანხა', currency_field='currency_id')
    comment = fields.Text(string='კომენტარი')
    currency_id = fields.Many2one(related='change_id.currency_id', store=True)