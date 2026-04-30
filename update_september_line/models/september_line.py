# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SeptemberLine(models.Model):
    _inherit = "september.line"

    def action_update_budget(self):
        """Update budget_name_main for selected records where it's empty"""
        for record in self:
            if record.product_id:
                # Get the budget from product category
                budget_id = record.product_id.categ_id.x_studio_many2one_field_2o6_1j1dfj1v3
                if budget_id:
                    record.budget_name_main = budget_id.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'წარმატება',
                'message': 'ბიუჯეტი განახლდა',
                'type': 'success',
                'sticky': False,
            }
        }
