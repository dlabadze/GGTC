from odoo import fields, models
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    effective_date_in_mrp = fields.Datetime(
        string="გატარების თარიღი",
        required=True,
        default=fields.Datetime.now,
        copy=False,
        help="Accounting and valuation effective datetime used when marking the MO as done.",
    )

    def _get_effective_date_context(self):
        self.ensure_one()
        effective_dt = self.effective_date_in_mrp
        if not effective_dt:
            raise UserError("Please set Effective Date before marking this Manufacturing Order as done.")
        local_dt = fields.Datetime.context_timestamp(self, effective_dt)
        return {
            "mrp_effective_datetime": effective_dt,
            "force_period_date": local_dt.date(),
        }

    def button_mark_done(self):
        for production in self:
            if not production.effective_date_in_mrp:
                raise UserError("Please set Effective Date before marking this Manufacturing Order as done.")
        res = super(
            MrpProduction,
            self.with_context(
                **self._merge_effective_date_context_for_multi()
            ),
        ).button_mark_done()
        for production in self.exists().filtered(lambda p: p.state == "done" and p.effective_date_in_mrp):
            production.with_context(mail_notrack=True).write({"date_finished": production.effective_date_in_mrp})
        return res

    def _merge_effective_date_context_for_multi(self):
        effective_map = {}
        force_map = {}
        for production in self:
            ctx_vals = production._get_effective_date_context()
            effective_map[production.id] = fields.Datetime.to_string(ctx_vals["mrp_effective_datetime"])
            force_map[production.id] = fields.Date.to_string(ctx_vals["force_period_date"])
        return {
            "mrp_effective_datetime_by_production": effective_map,
            "force_period_date_by_production": force_map,
        }

    def _post_inventory(self, cancel_backorder=False):
        res = super()._post_inventory(cancel_backorder=cancel_backorder)
        for production in self.exists():
            effective_dt = production.effective_date_in_mrp
            if not effective_dt:
                continue
            local_date = fields.Datetime.context_timestamp(production, effective_dt).date()
            moves = (
                production.move_raw_ids
                | production.move_finished_ids
                | production.move_byproduct_ids
                | production.all_move_raw_ids
                | production.all_move_ids
            ).filtered(lambda m: m.state == "done" and not m.scrapped)
            if not moves:
                continue
            self.env.cr.execute(
                "UPDATE stock_move SET date = %s WHERE id IN %s",
                (effective_dt, tuple(moves.ids)),
            )
            move_lines = moves.move_line_ids
            if move_lines:
                _logger.info(f"|----| Move lines: {move_lines}")
                move_lines.sudo().write({"date": effective_dt})
            svls = moves.mapped("stock_valuation_layer_ids")
            if svls:
                self.env.cr.execute(
                    "UPDATE stock_valuation_layer SET create_date = %s WHERE id IN %s",
                    (effective_dt, tuple(svls.ids)),
                )
            account_moves = (moves.account_move_ids | svls.mapped("account_move_id")).exists()
            if account_moves:
                account_moves.with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).write({"date": local_date})
                account_moves.line_ids.with_context(check_move_validity=False).write({"date": local_date})
        return res

