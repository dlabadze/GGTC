from odoo import models, fields, api, _


class ProductCategory(models.Model):
    _inherit = 'product.category'



    def action_open_update_categories_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update Categories',
            'res_model': 'update.categories.wizard',
            'view_mode': 'form',
            'target': 'new',
        }