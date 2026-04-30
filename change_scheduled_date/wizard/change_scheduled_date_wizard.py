from odoo import models, fields, api
from odoo.exceptions import UserError


class ChangeScheduleDateWizard(models.TransientModel):
    _name = 'change.scheduled.date.wizard'
    _description = 'Change Scheduled Date Wizard'

    new_scheduled_date = fields.Datetime(string="New Scheduled Date", required=True, default=fields.Datetime.now)

    def action_update_date(self):
        picking_ids = self.env.context.get('active_ids')
        if not picking_ids:
            raise UserError("No transfers selected.")

        self.env.cr.execute(
            """
            UPDATE stock_picking
            SET scheduled_date = %s
            WHERE id = ANY(%s)
            """,
            (self.new_scheduled_date, picking_ids)
        )

        self.env['stock.picking'].browse(picking_ids).invalidate_recordset(['scheduled_date'])

        return {'type': 'ir.actions.act_window_close'}