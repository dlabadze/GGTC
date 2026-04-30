# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MobileDebtDetail(models.Model):
    _name = 'mobile.debt.detail'
    _description = 'Mobile Debt Detail'

    mobile_debt_id = fields.Many2one(
        'mobile.debt',
        string='Mobile Debt',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    identification_id = fields.Char(
        string='Identification ID',
        related='employee_id.identification_id',
        store=True,
        readonly=True
    )
    private_phone = fields.Char(related='employee_id.private_phone', store=True, readonly=True)
    private_phone_from_excel = fields.Char(string='Private Phone from Excel')
    debt = fields.Float(string='Debt', digits=(16, 2))

