from odoo import models, fields, api

class GadziritadebaDet(models.Model):
    _name = 'gadziritadeba_det'
    _description = 'ექსპლუატაციაში გაშვების დეტალიზაცია'

    gadziritadeba_id = fields.Many2one('gadziritadeba', string='Parent Gadziritadeba')
    product_id = fields.Many2one('product.product', string='პროდუქტი')
    asset_idd = fields.Many2one('account.asset', string='ძირითადი საშუალება')
    quantity = fields.Float(string='რაოდენობა')
    price = fields.Float(string='ფასი')
    sumofdzs = fields.Float(string='თანხა', store=True)
    per_unit = fields.Boolean(string='დაიშალოს')
    dziritad = fields.Boolean(string='ძ/ს')
    mcirefas = fields.Boolean(string='მ/ფ')
    quantity_of_per = fields.Float(string='რამდენი დაიშალოს')
    account_id = fields.Many2one(
        'account.account',
        string='ძირითადის ანგარიში',
        domain="[('deprecated', '=', False)]",
        required=True
    )
    account_depr_id = fields.Many2one(
        'account.account',
        string='ცვეთის ანგარიში',
        domain="[('deprecated', '=', False)]",
        required=True
    )
    depreciation_duration_months = fields.Integer(
        string='ცვეთის ხანგრძლივობა (თვე)',
        default=60
    )


    group_asset_name = fields.Char(
    string='Asset Group Name',
    help='If set, lines with the same name will be combined into a single asset.'
)

