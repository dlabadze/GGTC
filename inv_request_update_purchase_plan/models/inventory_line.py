from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    def action_update_purchase_plan(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.update.purchase.plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_inventory_line_ids': self.ids,
            },
        }
    
    def cpv_dadastureba(self):
        stage = self.env['inventory.request.stage'].sudo().search([('name', '=', 'ფინანსური დირექტორი')], limit=1)
        if not stage:
            raise UserError(_('სტეიჯი ფინანსური დირექტორი არ არსებობს ბაზაში'))
        empty_cpv_lines = self.filtered(lambda x: not x.x_studio_purchase_plan_line)
        non_empty_cpv_lines = self.filtered(lambda x: x.x_studio_purchase_plan_line)
        requests = non_empty_cpv_lines.mapped('request_id')
        if requests:
            requests.write({'stage_id': stage.id})

        empty_count = len(empty_cpv_lines)
        updated_request_count = len(requests)
        with_cpv_line_count = len(non_empty_cpv_lines)

        if updated_request_count:
            notif_type = 'success'
            message = _(
                'განახლებულია %(req)d მოთხოვნა (%(lines)d ხაზს აქვს CPV). '
                'შერჩეულ ხაზებში CPV-ს გარეშე იყო %(empty)d ხაზი.'
            ) % {
                'req': updated_request_count,
                'lines': with_cpv_line_count,
                'empty': empty_count,
            }
        else:
            notif_type = 'warning'
            message = _(
                'მოთხოვნა არ განახლებულა — შერჩეულ ხაზებს არ აქვთ CPV. '
                'CPV-ს გარეშე იყო %(empty)d ხაზი (სულ შერჩეული: %(total)d).'
            ) % {'empty': empty_count, 'total': len(self)}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('CPV დადასტურება'),
                'message': message,
                'type': notif_type,
                'sticky': False,
            },
        }

