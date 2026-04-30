from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    x_unique_location_id = fields.Char(
        string="Location ID",
        copy=False,
        readonly=False,
        index=True,
        store=True,
    )

    @api.model
    def create(self, vals):
        if vals.get('x_unique_location_id'):
            existing = self.env['stock.location'].search([
                ('x_unique_location_id', '=', vals['x_unique_location_id'])
            ], limit=1)
            if existing:
                raise ValidationError(_("ლოკაციის ID '%s' უკვე არსებობს!") % vals['x_unique_location_id'])

        if not vals.get('x_unique_location_id'):
            existing_locations = self.env['stock.location'].search([
                ('x_unique_location_id', '!=', False)
            ])
            used_numbers = set()
            for loc in existing_locations:
                try:
                    used_numbers.add(int(loc.x_unique_location_id))
                except (ValueError, TypeError):
                    continue

            next_number = 1
            while next_number in used_numbers:
                next_number += 1

            vals['x_unique_location_id'] = f"{next_number:05d}"

        return super().create(vals)

    def write(self, vals):
        if 'x_unique_location_id' in vals and vals['x_unique_location_id']:
            for record in self:
                existing = self.env['stock.location'].search([
                    ('id', '!=', record.id),
                    ('x_unique_location_id', '=', vals['x_unique_location_id'])
                ], limit=1)
                if existing:
                    raise ValidationError(_("ლოკაციის ID '%s' უკვე არსებობს!") % vals['x_unique_location_id'])

        return super().write(vals)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', ('x_unique_location_id', operator, name), ('name', operator, name)]
            return self.search(domain + args, limit=limit).name_get()
        return self.search(args, limit=limit).name_get()

    def name_get(self):
        res = []
        for rec in self:
            if rec.x_unique_location_id:
                res.append((rec.id, f"[{rec.x_unique_location_id}] {rec.name}"))
            else:
                res.append((rec.id, rec.name or "Unnamed"))
        return res
