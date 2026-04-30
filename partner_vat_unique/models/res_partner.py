from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains("vat")
    def _check_unique_vat(self):
        for partner in self:
            if not partner.vat:
                continue

            vat = partner.vat.strip().lower()

            duplicate = self.search([
                ("id", "!=", partner.id),
                ("vat", "!=", False),
            ])

            for other in duplicate:
                if other.vat.strip().lower() == vat:
                    raise ValidationError(
                        _("A contact with this VAT / Personal ID already exists:\n%s")
                        % other.display_name
                    )
