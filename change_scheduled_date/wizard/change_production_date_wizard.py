from odoo import models, fields
from odoo.exceptions import UserError


class ChangeProductionDateWizard(models.TransientModel):
    _name = 'change.production.date.wizard'
    _description = 'Change Production Date Wizard'

    new_date_start = fields.Datetime(
        string="New Start Date",
        required=True,
        default=fields.Datetime.now
    )

    def action_update_date(self):
        production_ids = self.env.context.get('active_ids')
        if not production_ids:
            raise UserError("No manufacturing orders selected.")

        self.env.cr.execute(
            """
            UPDATE mrp_production
            SET date_start = %s
            WHERE id = ANY(%s)
            """,
            (self.new_date_start, production_ids)
        )
        self.env['mrp.production'].browse(production_ids).invalidate_recordset(['date_start'])

        return {'type': 'ir.actions.act_window_close'}