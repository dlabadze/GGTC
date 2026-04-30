from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BudgetingLine(models.Model):
    _inherit = 'budgeting.line'

    x_studio_code = fields.Char(
        string="Code",
        related="product_id.default_code",
        store=True,
        readonly=False,
    )

    x_studio_float_field_4i8_1j1fvmk7v = fields.Float(
        string="სულ საწყობი დღგ-ს გარეშე",
        compute='_compute_fields',
        store=True
    )
    
    x_studio_float_field_4i3_1j1fu7p5g = fields.Float(
        string="სულ შესაძენი დღგ-ს ჩათვლით",
        compute='_compute_fields',
        store=True
    )

    x_studio_float_field_tg_1j1fvkhrg = fields.Float(
        string="სულ შესაძენი დღგ-ს გარეშე",
        compute='_compute_fields',
        store=True
    )
    
    x_studio_float_field_4nk_1j1fvng8q = fields.Float(
        string="სულ საწყობი + შესაძენი NOT VAT",
        compute='_compute_fields',
        store=True
    )

    @api.depends(
        'x_studio_float_field_8ss_1j1ftvflr',
        'x_studio_float_field_5n2_1j1fu0r0p',
        'x_studio_float_field_gr_1j1fu1rj7',
        'x_studio_float_field_38e_1j1ftullr',
        'x_studio_float_field_7bi_1j1fu738v'
    )
    def _compute_fields(self):
        for record in self:
            record.x_studio_float_field_4i8_1j1fvmk7v = (
                record.x_studio_float_field_8ss_1j1ftvflr * 
                record.x_studio_float_field_5n2_1j1fu0r0p
            )
            
            record.x_studio_float_field_4i3_1j1fu7p5g = (
                record.x_studio_float_field_gr_1j1fu1rj7 * 
                record.x_studio_float_field_38e_1j1ftullr
            )
            
            record.x_studio_float_field_tg_1j1fvkhrg = (
                (record.x_studio_float_field_7bi_1j1fu738v or 0.0) * 
                (record.x_studio_float_field_38e_1j1ftullr or 0.0)
            )
            
            record.x_studio_float_field_4nk_1j1fvng8q = (
                record.x_studio_float_field_4i8_1j1fvmk7v + 
                record.x_studio_float_field_tg_1j1fvkhrg
            )
            
    @api.depends('product_id')
    def _compute_on_hand(self):
        for record in self:
            record.x_studio_related_field_2ca_1j1ftoic4 = record.product_id.qty_available or 0.0

    @api.onchange('quantity', 'product_id')
    def _onchange_quantity_product(self):
        # Don't auto-fill to_give and to_buy, leave them as 0
        pass

    @api.onchange('x_studio_float_field_8ss_1j1ftvflr')
    def _onchange_to_give(self):
        """When 'To Give' changes, adjust 'To Buy' to maintain total = quantity"""
        for record in self:
            if record.quantity:
                to_give = record.x_studio_float_field_8ss_1j1ftvflr or 0.0
                record.x_studio_float_field_38e_1j1ftullr = max(record.quantity - to_give, 0.0)

    @api.onchange('x_studio_float_field_38e_1j1ftullr')
    def _onchange_to_buy(self):
        """When 'To Buy' changes, adjust 'To Give' to maintain total = quantity"""
        for record in self:
            if record.quantity:
                to_buy = record.x_studio_float_field_38e_1j1ftullr or 0.0
                record.x_studio_float_field_8ss_1j1ftvflr = max(record.quantity - to_buy, 0.0)
                
    VAT_PERCENT = 18.0

    @api.onchange('x_studio_float_field_gr_1j1fu1rj7')
    def _onchange_price_with_vat(self):
        for record in self:
            if record.x_studio_float_field_gr_1j1fu1rj7:
                # Calculate without VAT
                record.x_studio_float_field_7bi_1j1fu738v = round(
                    record.x_studio_float_field_gr_1j1fu1rj7 / (1 + self.VAT_PERCENT / 100), 2
                )
            else:
                record.x_studio_float_field_7bi_1j1fu738v = 0.0

    @api.onchange('x_studio_float_field_7bi_1j1fu738v')
    def _onchange_price_without_vat(self):
        for record in self:
            if record.x_studio_float_field_7bi_1j1fu738v:
                # Calculate with VAT
                record.x_studio_float_field_gr_1j1fu1rj7 = round(
                    record.x_studio_float_field_7bi_1j1fu738v * (1 + self.VAT_PERCENT / 100), 2
                )
            else:
                record.x_studio_float_field_gr_1j1fu1rj7 = 0.0

