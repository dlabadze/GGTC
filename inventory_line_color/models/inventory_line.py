from odoo import api, fields, models


class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    is_marked = fields.Boolean(string='Mark')
    marked_by = fields.Char(string='Marked By')

    def write(self, vals):
        if 'is_marked' in vals:
            if vals['is_marked']:
                vals['marked_by'] = self.env.user.name
            else:
                vals['marked_by'] = False
        return super().write(vals)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self.env.context.get('filter_marked_by_me'):
            domain = list(domain) + [('marked_by', '=', self.env.user.name)]
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def action_clear_marked(self):
        self.write({'is_marked': False, 'marked_by': False})
