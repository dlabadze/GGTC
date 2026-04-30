# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _dv_mrp_is_manufacturing_stock_valuation(self):
        """True if this move is for stock valuation from an MO (raw, finished, or byproduct)."""
        self.ensure_one()
        stock_moves = self.stock_move_id
        stock_moves |= self.stock_valuation_layer_ids.mapped("stock_move_id")
        return bool(
            stock_moves.filtered(
                lambda sm: sm.production_id or sm.raw_material_production_id
            )
        )

    def write(self, vals):
        if self.env.context.get("dv_skip_sequence_fix"):
            return super().write(vals)

        if "date" in vals and "name" not in vals:
            result = True
            for move in self:
                move_vals = dict(vals)
                if (
                    move.state == "posted"
                    and move.name
                    and move.name != "/"
                    and (move.stock_move_id or move.stock_valuation_layer_ids)
                    and move._dv_mrp_is_manufacturing_stock_valuation()
                ):
                    (move.line_ids.filtered("reconciled")).remove_move_reconcile()
                    move.with_context(dv_skip_sequence_fix=True).button_draft()
                    move.with_context(
                        dv_skip_sequence_fix=True,
                        check_move_validity=False,
                        skip_account_move_synchronization=True,
                        skip_readonly_check=True,
                    ).write({
                        **move_vals,
                        "name": "/",
                    })
                    move.with_context(dv_skip_sequence_fix=True).action_post()
                else:
                    result = super(AccountMove, move).write(move_vals) and result
            return result
        return super().write(vals)

    def _post(self, soft=True):
        for move in self.filtered(lambda m: m.state == "draft"):
            if not move.name or move.name == "/":
                continue
            if move._sequence_matches_date():
                continue
            if not (move.stock_move_id or move.stock_valuation_layer_ids):
                continue
            if not move._dv_mrp_is_manufacturing_stock_valuation():
                continue
            move.with_context(
                check_move_validity=False,
                skip_account_move_synchronization=True,
            ).write({"name": "/"})
        return super()._post(soft=soft)
