from odoo import models, _
from odoo.exceptions import ValidationError

class Request(models.Model):
    _inherit = 'inventory.request'

    def write(self, vals):
        if 'stage_id' in vals:
            stage_model = self._fields['stage_id'].comodel_name
            cpv_stage = self.env[stage_model].search([('name', '=', 'CPV კოდები')], limit=1)
            new_stage = self.env[stage_model].browse(vals['stage_id']) if vals.get('stage_id') else False

            for request in self:
                if not cpv_stage or not new_stage:
                    continue
                if request.stage_id.id != cpv_stage.id:
                    continue
                if new_stage.sequence <= cpv_stage.sequence:
                    continue

                invalid_lines = request.line_ids.filtered(
                    lambda line: (
                        getattr(line, 'x_studio_purchase', False)
                        and not getattr(line, 'x_studio_no_cpv_1', False)
                        and (
                            not getattr(line, 'x_studio_purchase_plan', False)
                            or not getattr(line, 'x_studio_purchase_plan_line', False)
                        )
                    )
                )
                if invalid_lines:
                    request_number = request.name or request.display_name or str(request.id)
                    raise ValidationError(
                        _(f"შეავსეთ შესყიდვის გეგმის ველები ლაინებში. მოთხოვნა: {request_number}")
                    )

        return super().write(vals)