# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    @api.model
    def _default_description(self):
        """Default description for salary attachment"""
        return 'Default'
    
    description = fields.Text(
        string='Description',
        required=True,
        default=_default_description,
        help='Description of the salary attachment'
    )

