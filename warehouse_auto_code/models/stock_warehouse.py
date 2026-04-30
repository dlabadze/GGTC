from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    x_unique_warehouse_id = fields.Char(
        string="Warehouse ID",
        copy=False,
        readonly=False,
        index=True,
        store=True,
    )

    @api.model
    def create(self, vals):
        # Step 1: Check for duplicate manually entered ID
        if vals.get('x_unique_warehouse_id'):
            existing = self.env['stock.warehouse'].search([
                ('x_unique_warehouse_id', '=', vals['x_unique_warehouse_id'])
            ], limit=1)
            if existing:
                raise ValidationError(_("საწყობის ID '%s' უკვე არსებობს!") % vals['x_unique_warehouse_id'])

        # Step 2: Auto-generate a safe new ID
        if not vals.get('x_unique_warehouse_id'):
            all_ids = self.env['stock.warehouse'].search([
                ('x_unique_warehouse_id', '!=', False)
            ]).mapped('x_unique_warehouse_id')

            used_numbers = set()
            for val in all_ids:
                try:
                    used_numbers.add(int(val))
                except (ValueError, TypeError):
                    continue

            next_number = 1
            while next_number in used_numbers:
                next_number += 1

            vals['x_unique_warehouse_id'] = f"{next_number:05d}"

        return super().create(vals)

    def write(self, vals):
        # Prevent duplicate ID during update
        if 'x_unique_warehouse_id' in vals and vals['x_unique_warehouse_id']:
            for record in self:
                existing = self.env['stock.warehouse'].search([
                    ('id', '!=', record.id),
                    ('x_unique_warehouse_id', '=', vals['x_unique_warehouse_id'])
                ], limit=1)
                if existing:
                    raise ValidationError(_("საწყობის ID '%s' უკვე არსებობს!") % vals['x_unique_warehouse_id'])

        return super().write(vals)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', ('x_unique_warehouse_id', operator, name), ('name', operator, name)]
            return self.search(domain + args, limit=limit).name_get()
        return self.search(args, limit=limit).name_get()

    def name_get(self):
        res = []
        for rec in self:
            if rec.x_unique_warehouse_id:
                res.append((rec.id, f"[{rec.x_unique_warehouse_id}] {rec.name}"))
            else:
                res.append((rec.id, rec.name or "Unnamed"))
        return res

