from odoo import fields,models,api

class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    x_is_warning_state = fields.Boolean(compute='_compute_warning_state', store=False)
    remainder_summed = fields.Float(string ='ნაშთი', compute='_compute_remainder_summed', store=False)

    @api.depends('x_studio_purchase', 'x_studio_warehouse', 'x_studio_on_hand', 'request_id.stage_id')
    def _compute_warning_state(self):
        target_stages = ["ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი"]
        for record in self:
            is_warning = False
            if (record.request_id.stage_id.name in target_stages and
                    record.product_id and record.x_studio_warehouse and not record.x_studio_purchase):

                quants = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id', '=', record.x_studio_warehouse.id),
                    ('location_id.usage', '=', 'internal'),
                    ('on_hand', '=', True)
                ])
                if not quants:
                    is_warning = True
                else:
                    total_free_quants = sum(quants.mapped('free_quantity'))
                    if record.quantity > total_free_quants:
                        is_warning = True

            record.x_is_warning_state = is_warning

    @api.depends('x_studio_warehouse', 'x_studio_on_hand', 'product_id')
    def _compute_remainder_summed(self):
        for record in self:
            total_free_qty = 0.0
            if record.product_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', record.product_id.id),
                    ('location_id.usage', '=', 'internal'),
                    ('location_id.x_studio_request_location', '=', True),
                    ('on_hand', '=', True)
                ])

                total_free_qty = sum(quants.mapped('free_quantity'))
            record.remainder_summed = total_free_qty

    @api.onchange('x_studio_purchase', 'x_studio_warehouse', 'quantity', 'request_id.stage_id')
    def _check_custom_inventory_warning(self):
        target_stages = ["ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი"]

        for record in self:
            if record.request_id.stage_id.name in target_stages:
                if not record.x_studio_purchase and record.x_studio_warehouse and record.product_id:
                    quants = self.env['stock.quant'].search([
                        ('product_id', '=', record.product_id.id),
                        ('location_id', '=', record.x_studio_warehouse.id),
                        ('location_id.usage', '=', 'internal'),
                        ('on_hand', '=', True)
                    ])
                    is_warning = False
                    if not quants:
                        is_warning = True
                    else:
                        total_free_qty = sum(quants.mapped('free_quantity'))
                        if record.quantity > total_free_qty:
                            is_warning = True
                    if is_warning:
                        return {
                            'warning': {
                                'title': "ყურადღება!",
                                'message': "ამ საწყობში თავისუფალი ნაშთი არ არსებობს, მცირეა მოთხოვნილ რაოდენობაზე ან მთლიანად დარეზერვებულია.",
                                'type': 'notification',
                                'sticky': True,
                            }
                        }