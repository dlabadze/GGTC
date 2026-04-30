import re
import logging
from collections import defaultdict
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class BudgetXStudioAnalyzer(models.TransientModel):
    _name = 'budget.x_studio.analyzer'
    _description = 'Budget x_studio_ Field Analyzer'

    result = fields.Text(string='Analysis Result', readonly=True)
    apply_result = fields.Text(string='Apply Result', readonly=True)
    has_result = fields.Boolean(default=False)
    has_apply_result = fields.Boolean(default=False)
    # Serialised calculated values so Apply doesn't need to recompute
    # Format: "bl_id:amount|bl_id:amount|..."
    _calculated_cache = fields.Char(string='Calculated Cache')

    # ── formatting helper ────────────────────────────────────────────────────

    def _fmt(self, amount):
        return f"{amount:,.2f}"

    def _fmt_diff(self, amount):
        """Format a diff value with a leading + or - sign."""
        sign = '+' if amount >= 0 else '-'
        return f"{sign}{abs(amount):,.2f}"

    # ── Path 1: vendor bills with service lines → PO → budget.line ──────────

    def _run_path1(self):
        lines = []
        totals = defaultdict(float)
        records = []

        posted_bills = self.env['account.move'].search([
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
        ])

        for move in posted_bills:
            service_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.type == 'service'
            )
            for inv_line in service_lines:
                po_line = inv_line.purchase_line_id
                if not po_line:
                    continue
                budget_line = po_line.budget_line_id
                if not budget_line:
                    continue
                amount = inv_line.price_subtotal
                totals[budget_line.id] += amount
                records.append({
                    'move': move.name,
                    'move_id': move.id,
                    'amount': amount,
                    'budget_line_id': budget_line.id,
                })

        grand = sum(totals.values())
        lines.append("=" * 65)
        lines.append("PATH 1 — Posted vendor bills → service lines → PO → budget.line")
        lines.append("=" * 65)
        lines.append(f"  Matching moves  : {len({r['move_id'] for r in records})}")
        lines.append(f"  Matching lines  : {len(records)}")
        lines.append(f"  Budget lines hit: {len(totals)}")
        lines.append(f"  GRAND TOTAL     : {self._fmt(grand)}")

        if totals:
            lines.append("")
            lines.append("  Per-budget-line contribution (this path only):")
            for bl_id, total in sorted(totals.items(), key=lambda x: -x[1]):
                bl = self.env['budget.line'].browse(bl_id)
                account_code = bl.account_id.code if bl.account_id else 'N/A'
                account_name = (bl.account_id.name or '')[:35]
                lines.append(
                    f"    [{account_code}] {account_name:<35}  contribution={self._fmt(total):>18}"
                )

        return lines, totals, grand

    # ── Path 2: x_studio_muxli_hr journal entries ────────────────────────────

    def _run_path2(self):
        lines = []
        totals = defaultdict(float)
        records = []

        # Check if budget.analytic model exists
        if 'budget.analytic' not in self.env.registry.models:
            lines.append("=" * 65)
            lines.append("PATH 2 — x_studio_muxli_hr [CODE] → budget.line")
            lines.append("=" * 65)
            lines.append("  SKIPPED: model 'budget.analytic' not found in registry.")
            lines.append(f"  Available budget models: {[m for m in self.env.registry.models if 'budget' in m]}")
            return lines, totals, 0.0

        try:
            all_posted = self.env['account.move'].search([('state', '=', 'posted')])
            moves_with_field = all_posted.filtered(
                lambda m: getattr(m, 'x_studio_muxli_hr', False)
            )
        except Exception as e:
            moves_with_field = []
            _logger.warning(f"Path2: could not filter x_studio_muxli_hr: {e}")

        for move in moves_with_field:
            # Mirror the real action_post logic: Path 2 is skipped when the move
            # was already handled by Path 1 (vendor bill with service product lines)
            if move.move_type in ('in_invoice', 'in_refund'):
                service_lines = move.invoice_line_ids.filtered(
                    lambda l: l.product_id and l.product_id.type == 'service'
                )
                if service_lines:
                    continue  # handled = True in real code → Path 2 is skipped
            muxli = getattr(move, 'x_studio_muxli_hr', False)
            if not muxli:
                continue
            match = re.search(r'\[([^\]]+)\]', muxli)
            if not match:
                continue
            budget_code = match.group(1).strip()
            move_date = move.date

            budget_analytic = self.env['budget.analytic'].search([
                ('budget_type', '=', 'expense'),
                ('date_from', '<=', move_date),
                ('date_to', '>=', move_date),
            ], limit=1)
            if not budget_analytic:
                continue

            budget_line = self.env['budget.line'].search([
                ('budget_analytic_id', '=', budget_analytic.id),
                ('account_id.code', '=', budget_code),
            ], limit=1)
            if not budget_line:
                continue

            amount = move.amount_untaxed or sum(
                move.line_ids.filtered(lambda l: l.debit > 0).mapped('debit')
            )
            totals[budget_line.id] += amount
            records.append({
                'move': move.name,
                'move_id': move.id,
                'budget_code': budget_code,
                'amount': amount,
                'budget_line_id': budget_line.id,
            })

        grand = sum(totals.values())
        lines.append("=" * 65)
        lines.append("PATH 2 — x_studio_muxli_hr [CODE] → budget.line")
        lines.append("=" * 65)
        lines.append(f"  Matching moves  : {len({r['move_id'] for r in records})}")
        lines.append(f"  Budget lines hit: {len(totals)}")
        lines.append(f"  GRAND TOTAL     : {self._fmt(grand)}")

        if totals:
            lines.append("")
            lines.append("  Per-budget-line contribution (this path only):")
            for bl_id, total in sorted(totals.items(), key=lambda x: -x[1]):
                bl = self.env['budget.line'].browse(bl_id)
                account_code = bl.account_id.code if bl.account_id else 'N/A'
                account_name = (bl.account_id.name or '')[:35]
                lines.append(
                    f"    [{account_code}] {account_name:<35}  contribution={self._fmt(total):>18}"
                )

        return lines, totals, grand

    # ── Path 3: scrap stock pickings → inventory.request → budget.line ───────

    def _run_path3(self):
        lines = []
        totals = defaultdict(float)
        records = []

        try:
            done_pickings = self.env['stock.picking'].search([('state', '=', 'done')])

            for picking in done_pickings:
                dest_name = picking.location_dest_id.complete_name or ''
                is_scrap = (
                    'scrap' in dest_name.lower() or
                    'ჩამოწერა' in dest_name
                )
                if not is_scrap:
                    continue

                related_field = getattr(picking, 'x_studio_related_field_2sg_1j7espk8g', False)
                if not related_field:
                    continue

                if 'inventory.request' not in self.env.registry.models:
                    continue

                inventory_request = self.env['inventory.request'].search([
                    ('x_studio_request_number', '=', related_field)
                ], limit=1)
                if not inventory_request:
                    continue

                if 'inventory.line' not in self.env.registry.models:
                    continue

                picking_products = picking.move_ids.mapped('product_id')
                inventory_lines = self.env['inventory.line'].search([
                    ('request_id', '=', inventory_request.name)
                ])
                request_products = inventory_lines.mapped('product_id')
                matching_products = picking_products & request_products
                if not matching_products:
                    continue

                matching_inv_lines = inventory_lines.filtered(
                    lambda l: l.product_id in matching_products
                )

                # Group by (budget_analytic_id, analytic_account_id)
                budget_groups = defaultdict(lambda: {'analytic': None, 'account': None, 'products': []})
                for inv_line in matching_inv_lines:
                    bm = inv_line.budget_main.id if inv_line.budget_main else False
                    bn = inv_line.budget_name_main.id if inv_line.budget_name_main else False
                    if not bm or not bn:
                        continue
                    key = (bm, bn)
                    budget_groups[key]['analytic'] = bm
                    budget_groups[key]['account'] = bn
                    budget_groups[key]['products'].append(inv_line.product_id)

                for key, info in budget_groups.items():
                    prods = info['products']
                    total_amount = sum(
                        m.product_uom_qty * m.product_id.standard_price
                        for m in picking.move_ids
                        if m.product_id in prods
                    )
                    budget_lines = self.env['budget.line'].search([
                        ('budget_analytic_id', '=', info['analytic']),
                        ('account_id', '=', info['account']),
                    ])
                    for bl in budget_lines:
                        totals[bl.id] += total_amount
                        records.append({
                            'picking': picking.name,
                            'picking_id': picking.id,
                            'amount': total_amount,
                            'budget_line_id': bl.id,
                        })

        except Exception as e:
            lines.append(f"  WARNING: error in Path 3 — {e}")
            _logger.exception("Path3 error")

        grand = sum(totals.values())
        lines.append("=" * 65)
        lines.append("PATH 3 — Validated scrap pickings → inventory.request → budget.line")
        lines.append("=" * 65)
        lines.append(f"  Matching pickings: {len({r['picking_id'] for r in records})}")
        lines.append(f"  Budget lines hit : {len(totals)}")
        lines.append(f"  GRAND TOTAL      : {self._fmt(grand)}")

        if totals:
            lines.append("")
            lines.append("  Per-budget-line contribution (this path only):")
            for bl_id, total in sorted(totals.items(), key=lambda x: -x[1]):
                bl = self.env['budget.line'].browse(bl_id)
                account_code = bl.account_id.code if bl.account_id else 'N/A'
                account_name = (bl.account_id.name or '')[:35]
                lines.append(
                    f"    [{account_code}] {account_name:<35}  contribution={self._fmt(total):>18}"
                )

        return lines, totals, grand

    # ── Main action ──────────────────────────────────────────────────────────

    def action_run_analysis(self):
        output = []
        output.append(f"Budget x_studio_ Field Analysis")
        output.append(f"Database: {self.env.cr.dbname}")
        output.append("")
        output.append("IMPORTANT NOTES:")
        output.append("  1. This script only reconstructs AUTOMATED writes to x_studio_:")
        output.append("       Path 1 — posted vendor bills (service lines via PO)")
        output.append("       Path 2 — posted moves with x_studio_muxli_hr [CODE] (only when Path 1 didn't apply)")
        output.append("       Path 3 — validated scrap stock pickings via inventory.request")
        output.append("  2. MANUAL changes made via the budget change dialog (budget.line.changes)")
        output.append("     cannot be reconstructed. If a user manually set x_studio_, a mismatch")
        output.append("     in the summary is EXPECTED and does NOT mean a bug.")
        output.append("  3. A 'diff = 0' line means the DB value matches what automation would produce.")
        output.append("")

        # Run all three paths
        p1_lines, p1_totals, p1_grand = self._run_path1()
        output.extend(p1_lines)
        output.append("")

        p2_lines, p2_totals, p2_grand = self._run_path2()
        output.extend(p2_lines)
        output.append("")

        p3_lines, p3_totals, p3_grand = self._run_path3()
        output.extend(p3_lines)
        output.append("")

        # Combined summary
        combined = defaultdict(float)
        for bl_id, amt in p1_totals.items():
            combined[bl_id] += amt
        for bl_id, amt in p2_totals.items():
            combined[bl_id] += amt
        for bl_id, amt in p3_totals.items():
            combined[bl_id] += amt

        grand_calc = sum(combined.values())

        all_bl_ids = list(combined.keys())
        db_total = 0.0
        if all_bl_ids:
            bls = self.env['budget.line'].browse(all_bl_ids)
            db_total = sum((bl.x_studio_ or 0) for bl in bls)

        output.append("=" * 75)
        output.append("COMBINED SUMMARY — all paths merged per budget.line")
        output.append("=" * 75)
        output.append(f"  {'account code':<12}  {'account name':<30}  {'calculated':>18}  {'db x_studio_':>18}  {'diff':>18}")
        output.append(f"  {'-'*12}  {'-'*30}  {'-'*18}  {'-'*18}  {'-'*18}")

        for bl_id, calc_total in sorted(combined.items(), key=lambda x: -x[1]):
            bl = self.env['budget.line'].browse(bl_id)
            db_val = bl.x_studio_ or 0
            diff = calc_total - db_val
            flag = "  ← MISMATCH" if abs(diff) > 0.01 else ""
            account_code = bl.account_id.code if bl.account_id else 'N/A'
            account_name = (bl.account_id.name or '')[:30]
            output.append(
                f"  {account_code:<12}  {account_name:<30}  {self._fmt(calc_total):>18}  "
                f"{self._fmt(db_val):>18}  {self._fmt_diff(diff):>18}{flag}"
            )

        output.append("")
        output.append(f"  Total calculated (all paths) : {self._fmt(grand_calc)}")
        output.append(f"  Total in DB (x_studio_)      : {self._fmt(db_total)}")
        output.append(f"  Overall difference           : {self._fmt_diff(grand_calc - db_total)}")
        output.append("=" * 65)

        result_text = "\n".join(output)

        # Serialise combined totals so Apply can use them without recomputing
        cache = '|'.join(f"{bl_id}:{amt}" for bl_id, amt in combined.items())

        self.write({
            'result': result_text,
            'has_result': True,
            '_calculated_cache': cache,
            'has_apply_result': False,
            'apply_result': False,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'budget.x_studio.analyzer',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Apply calculated values via ORM (no SQL) ─────────────────────────────

    def action_apply_calculated_values(self):
        """
        Write the calculated x_studio_ values back to budget.line records
        using the ORM (write method) — no raw SQL involved.
        Only updates records where the calculated value differs from the DB value.
        """
        if not self._calculated_cache:
            self.write({
                'apply_result': 'No calculated values found. Please run the analysis first.',
                'has_apply_result': True,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'budget.x_studio.analyzer',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        # Parse cache
        combined = {}
        for part in self._calculated_cache.split('|'):
            if ':' not in part:
                continue
            bl_id_str, amt_str = part.split(':', 1)
            try:
                combined[int(bl_id_str)] = float(amt_str)
            except ValueError:
                continue

        output = []
        output.append("Apply Calculated Values — ORM Write Log")
        output.append("=" * 65)

        updated = []
        skipped = []
        errors = []

        for bl_id, calc_value in sorted(combined.items()):
            bl = self.env['budget.line'].browse(bl_id)
            if not bl.exists():
                errors.append(f"  #{bl_id}: record no longer exists — skipped")
                continue

            current = bl.x_studio_ or 0.0
            diff = calc_value - current

            if abs(diff) <= 0.01:
                skipped.append(
                    f"  #{bl_id:<6}  no change needed  value={self._fmt(current):>18}  {bl.display_name or ''}"
                )
                continue

            try:
                bl.write({'x_studio_': calc_value})
                updated.append(
                    f"  #{bl_id:<6}  {self._fmt(current):>18}  →  {self._fmt(calc_value):>18}"
                    f"  (diff {self._fmt_diff(diff)})  {bl.display_name or ''}"
                )
                _logger.info(
                    f"[BudgetXStudioAnalyzer] budget.line #{bl_id} x_studio_ "
                    f"{current} → {calc_value} (diff {diff:+.2f})"
                )
            except Exception as e:
                errors.append(f"  #{bl_id}: ERROR — {e}")
                _logger.exception(f"[BudgetXStudioAnalyzer] failed to write budget.line #{bl_id}")

        output.append(f"\n✔  Updated : {len(updated)} record(s)")
        output.append(f"–  Skipped  : {len(skipped)} record(s) (no change needed)")
        output.append(f"✖  Errors   : {len(errors)} record(s)")

        if updated:
            output.append("\nUpdated records:")
            output.append(f"  {'#':>8}  {'old value':>18}     {'new value':>18}  diff")
            output.append(f"  {'-'*8}  {'-'*18}     {'-'*18}  {'-'*15}")
            output.extend(updated)

        if skipped:
            output.append("\nSkipped (already correct):")
            output.extend(skipped)

        if errors:
            output.append("\nErrors:")
            output.extend(errors)

        output.append("\n" + "=" * 65)

        self.write({
            'apply_result': "\n".join(output),
            'has_apply_result': True,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'budget.x_studio.analyzer',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
