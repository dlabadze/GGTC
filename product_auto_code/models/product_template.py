from odoo import models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        # Step 1: Check manually entered code isn't duplicate
        if vals.get('default_code'):
            existing = self.env['product.template'].search([
                ('default_code', '=', vals['default_code'])
            ], limit=1)
            if existing:
                raise ValidationError(_("პროდუქტის კოდი '%s' უკვე არსებობს!") % vals['default_code'])

        # Step 2: Auto-generate code based on highest numeric code
        if not vals.get('default_code'):
            # Get all default codes
            all_codes = self.env['product.template'].search([
                ('default_code', '!=', False)
            ]).mapped('default_code')
            
            # Convert to integers and find the maximum
            numeric_codes = []
            for code in all_codes:
                if len(code) != 5:
                    continue
                try:
                    # Try to convert to integer
                    numeric_codes.append(int(code))
                except (ValueError, TypeError):
                    # Skip codes that can't be converted to int
                    continue
            # _logger.info(f"Numeric codes: {numeric_codes}")
            # Get the biggest number and add 1
            _logger.info(f"Max number: {max(numeric_codes)}")
            if numeric_codes:
                next_number = max(numeric_codes) + 1
            else:
                next_number = 1
            
            # Format with leading zeros (5 digits)
            vals['default_code'] = f"{next_number:05d}"

        return super().create(vals)

    def write(self, vals):
        # Step 3: Prevent setting a duplicate manually later
        if 'default_code' in vals and vals['default_code']:
            for rec in self:
                existing = self.env['product.template'].search([
                    ('id', '!=', rec.id),
                    ('default_code', '=', vals['default_code'])
                ], limit=1)
                if existing:
                    raise ValidationError(_("პროდუქტის კოდი '%s' უკვე არსებობს!") % vals['default_code'])

        return super().write(vals)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', ('default_code', operator, name), ('name', operator, name)]
            return self.search(domain + args, limit=limit).name_get()
        return self.search(args, limit=limit).name_get()

    def name_get(self):
        res = []
        for rec in self:
            if rec.default_code:
                name = f"[{rec.default_code}] {rec.name}"
            else:
                name = rec.name
            res.append((rec.id, name))
        return res