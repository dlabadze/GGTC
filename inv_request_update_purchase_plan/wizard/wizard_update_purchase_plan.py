from odoo import models, fields, api, _


class WizardUpdatePurchasePlan(models.TransientModel):
    _name = 'wizard.update.purchase.plan'
    _description = 'Wizard Update Purchase Plan'

    purchase_plan_id = fields.Many2one('purchase.plan', string='Purchase Plan')
    purchase_plan_line_id = fields.Many2one(
        'purchase.plan.line',
        string='CPV Code',
        domain="[('plan_id', '=', purchase_plan_id)]",
    )
    inventory_line_ids = fields.Many2many('inventory.line', string='Inventory Lines')


    def action_update_purchase_plan(self):
        plan_updated = 0
        cpv_updated = 0
        if self.purchase_plan_id:
            not_purchase_plan_lines = self.inventory_line_ids.filtered(lambda x: not x.x_studio_purchase_plan and x.x_studio_purchase)
            plan_updated = len(not_purchase_plan_lines)
            if plan_updated:
                not_purchase_plan_lines.sudo().write({
                    'x_studio_purchase_plan': self.purchase_plan_id.id,
                })
        if self.purchase_plan_line_id:
            not_purchase_plan_line_lines = self.inventory_line_ids.filtered(lambda x: not x.x_studio_purchase_plan_line and x.x_studio_purchase)
            cpv_updated = len(not_purchase_plan_line_lines)
            if cpv_updated:
                not_purchase_plan_line_lines.sudo().write({
                    'x_studio_purchase_plan_line': self.purchase_plan_line_id.id,
                })

        parts = []
        if self.purchase_plan_id:
            parts.append(_("Purchase plan: %s line(s) updated.") % plan_updated)
        if self.purchase_plan_line_id:
            parts.append(_("CPV code: %s line(s) updated.") % cpv_updated)
        if not parts:
            message = _("Select a purchase plan and/or CPV code.")
            notif_type = 'warning'
        elif plan_updated == 0 and cpv_updated == 0:
            message = _("No lines were updated (values were already set).")
            notif_type = 'info'
        else:
            message = "\n".join(parts)
            notif_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Update purchase plan'),
                'message': message,
                'type': notif_type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }