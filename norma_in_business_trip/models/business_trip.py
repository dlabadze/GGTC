from odoo import fields, api, models
import logging

_logger = logging.getLogger(__name__)

class BusinessTrip(models.Model):
    _inherit = 'x_business_trip'

    x_studio_norma = fields.Char(string="Norma", compute="_compute_norma", store=True)

    @api.depends("x_studio_vehicle", "x_studio_vehicle.x_studio_one2many_field_55n_1j0p4eqma")
    def _compute_norma(self):
        for rec in self:
            norma_value = 0.0
            try:
                if rec.x_studio_vehicle:
                    norms = rec.x_studio_vehicle.x_studio_one2many_field_55n_1j0p4eqma
                    if norms:
                        latest_norm = norms.sorted(
                            lambda n: n.x_studio_date or fields.Date.today(),
                            reverse=True
                        )[:1]
                        if latest_norm:
                            norma_value = latest_norm[0].x_name
            except Exception as e:
                _logger.error("Error computing norma for record %s: %s", rec.id, e)

            rec.x_studio_norma = norma_value
