from odoo import models, api


class AssetMovementLog(models.Model):
    _inherit = "x_asset_movement_log"

    def write(self, vals):
        res = super().write(vals)

        # Only run when the specific m2m field changes
        if "x_studio_many2many_field_lk_1iujl28b9" in vals:
            self._update_reverse_relationship()

        return res

    def _update_reverse_relationship(self):
        """Update the reverse relationship field on linked records"""
        for record in self:
            # Get all currently linked records
            linked_records = record.x_studio_many2many_field_lk_1iujl28b9

            # Update their reverse relationship field to point to this record
            for linked_record in linked_records:
                if linked_record.x_studio_related_field_1ah_1j04buao9 != record:
                    linked_record.x_studio_related_field_1ah_1j04buao9 = record

