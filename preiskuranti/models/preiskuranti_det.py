from odoo import models, fields


class PreiskurantiDet(models.Model):
    _name = 'preiskuranti_det'
    _description = 'პრეისკურანტის დეტალიზაცია'

    preiskuranti_id = fields.Many2one(
        'preiskuranti',
        string='Parent პრეისკურანტი',
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='პროდუქტი',
        required=True
    )
    fasi = fields.Float(
        string="ფასი",
        required=True
    )

    garantia = fields.Integer(string = "საგარანტიო პერიოდი (დღე)")


class PreiskurantiCandidate(models.Model):
    _name = 'preiskuranti.candidate'
    _description = 'პრეისკურანტის კანდიდატები'

    preiskuranti_id = fields.Many2one(
        'preiskuranti',
        string='Parent პრეისკურანტი',
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='პროდუქტი',
        required=True
    )
    fasi = fields.Float(
        string="ფასი",
        required=True
    )
    garantia = fields.Integer(string="საგარანტიო პერიოდი (დღე)")
    is_validated = fields.Boolean(string="დადასტურებულია", default=False)

    def action_validate(self):
        """Moves the candidate to the main preiskuranti_det table."""
        for rec in self:
            # Check if product is already in preiskuranti_det for this preiskuranti
            existing_line = self.env['preiskuranti_det'].search([
                ('preiskuranti_id', '=', rec.preiskuranti_id.id),
                ('product_id', '=', rec.product_id.id)
            ], limit=1)

            if existing_line:
                # Update existing (optional behavior, but safer)
                existing_line.write({
                    'fasi': rec.fasi,
                    'garantia': rec.garantia,
                })
            else:
                # Create new
                self.env['preiskuranti_det'].create({
                    'preiskuranti_id': rec.preiskuranti_id.id,
                    'product_id': rec.product_id.id,
                    'fasi': rec.fasi,
                    'garantia': rec.garantia,
                })
            
            # Mark as validated
            rec.is_validated = True