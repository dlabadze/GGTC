import base64
import io
import logging
import traceback
from datetime import datetime, timedelta

import pandas as pd

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockValuationImportWizard(models.TransientModel):
    _name = 'stock.valuation.import.wizard'
    _description = 'Import Product Costs and Fix Jan 1st Valuation'

    # ------------------------------------------------------------------ #
    #  Fields                                                              #
    # ------------------------------------------------------------------ #
    excel_file     = fields.Binary(string='Excel File (.xlsx)', required=True)
    excel_filename = fields.Char(string='Filename')
    target_date    = fields.Date(
        string='Backfill Date',
        required=True,
        default=lambda self: datetime(datetime.now().year, 1, 1).date(),
    )
    cleanup_today  = fields.Boolean(
        string="Remove Today's Accidental Revaluation Moves",
        default=True,
        help='Deletes any account moves dated today that are linked to stock '
             'valuation layers — the spurious entries Odoo fires when we update '
             'standard_price. Safe: invoices and manual JEs are NOT affected.',
    )
    state          = fields.Selection(
        [('draft', 'Ready'), ('done', 'Done')],
        default='draft',
    )
    result_message = fields.Text(string='Result', readonly=True)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #
    def _get_account(self, code):
        """Return account.account for *code* (int/float/str) or None."""
        if code is None:
            return None
        try:
            if pd.isna(code):
                return None
        except (TypeError, ValueError):
            pass
        try:
            clean = str(int(float(code)))
        except (ValueError, TypeError):
            return None
        account = self.env['account.account'].search([('code', '=', clean)], limit=1)
        if not account:
            _logger.warning("Account code '%s' not found in chart of accounts.", clean)
        return account or None

    def _resolve_accounts_from_category(self, product):
        """Walk the product category hierarchy to find valuation accounts."""
        debit_account = credit_account = None
        categ = product.categ_id
        while categ:
            if not debit_account and 'property_stock_valuation_account_id' in categ._fields:
                debit_account = categ.property_stock_valuation_account_id or None
            if not credit_account:
                for fname in ('property_stock_inventory_account_id',
                              'property_stock_account_input_categ_id'):
                    if fname in categ._fields:
                        val = getattr(categ, fname, None)
                        if val:
                            credit_account = val
                            break
            if debit_account and credit_account:
                break
            categ = categ.parent_id or None
        return debit_account, credit_account

    def _get_stock_valuation_journal(self):
        """
        Return the stock valuation journal.
        Tries the standard company field first, then falls back to search.
        """
        company = self.env.company
        journal = getattr(company, 'stock_journal_id', None)
        if journal:
            return journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('name', 'ilike', 'stock'),
        ], limit=1)
        if journal:
            return journal
        return self.env['account.journal'].search([('type', '=', 'general')], limit=1)

    def _backdate_move(self, move_id, target_datetime):
        """SQL-backdate a move and all its lines."""
        self.env.cr.execute(
            "UPDATE account_move SET date=%s, create_date=%s WHERE id=%s",
            (target_datetime.date(), target_datetime, move_id),
        )
        self.env.cr.execute(
            "UPDATE account_move_line SET date=%s, create_date=%s WHERE move_id=%s",
            (target_datetime.date(), target_datetime, move_id),
        )

    def _delete_move_for_layer(self, layer):
        """Hard-delete the journal entry linked to *layer* (if any)."""
        if not layer.account_move_id:
            return
        mid = layer.account_move_id.id
        _logger.info("  Deleting existing JE %s (ID %d) for Layer %d",
                     layer.account_move_id.name, mid, layer.id)
        self.env.cr.execute("DELETE FROM account_move_line WHERE move_id=%s", (mid,))
        self.env.cr.execute(
            "UPDATE stock_valuation_layer "
            "SET account_move_id=NULL, account_move_line_id=NULL WHERE id=%s",
            (layer.id,)
        )
        self.env.cr.execute("DELETE FROM account_move WHERE id=%s", (mid,))

    def _create_journal_entry(self, layer, target_datetime, debit_account, credit_account, journal):
        """
        Create and post an account.move for *layer* dated *target_datetime*.

        Positive qty (stock IN):
          DR  debit_account   (e.g. 1620 / 2197 / 1640)  amount = abs(layer.value)
          CR  credit_account  (e.g. 1612)                 amount = abs(layer.value)

        Negative qty (stock OUT): DR/CR are swapped.

        Returns the created move, or None on failure.
        """
        if not debit_account or not credit_account:
            _logger.warning("Layer %d: accounts not resolved — JE skipped.", layer.id)
            return None
        if not journal:
            _logger.warning("Layer %d: no journal found — JE skipped.", layer.id)
            return None

        product = layer.product_id
        qty     = layer.quantity
        value   = abs(layer.value)

        if value == 0:
            _logger.warning("Layer %d: value is 0 — JE skipped (no cost?).", layer.id)
            return None

        dr_account = debit_account  if qty >= 0 else credit_account
        cr_account = credit_account if qty >= 0 else debit_account

        ref = _('Opening inventory — %s') % (product.display_name or product.default_code or str(product.id))

        move_vals = {
            'journal_id':                journal.id,
            'date':                      target_datetime.date(),
            'ref':                       ref,
            'move_type':                 'entry',
            'stock_valuation_layer_ids': [(4, layer.id)],
            'line_ids': [
                (0, 0, {
                    'account_id':    dr_account.id,
                    'name':          ref,
                    'product_id':    product.id,
                    'quantity':      abs(qty),
                    'product_uom_id': product.uom_id.id,
                    'debit':         value,
                    'credit':        0.0,
                    'date':          target_datetime.date(),
                }),
                (0, 0, {
                    'account_id':    cr_account.id,
                    'name':          ref,
                    'product_id':    product.id,
                    'quantity':      abs(qty),
                    'product_uom_id': product.uom_id.id,
                    'debit':         0.0,
                    'credit':        value,
                    'date':          target_datetime.date(),
                }),
            ],
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        # action_post may reset the date to today — force it back via SQL
        self._backdate_move(move.id, target_datetime)

        # Link the new move to the layer
        self.env.cr.execute(
            "UPDATE stock_valuation_layer SET account_move_id=%s WHERE id=%s",
            (move.id, layer.id),
        )

        _logger.info(
            "  Created JE %s (ID %d) for Layer %d | %s | qty=%s value=%.2f | "
            "DR %s  CR %s",
            move.name, move.id, layer.id, product.display_name,
            qty, value, dr_account.code, cr_account.code,
        )
        return move

    # ------------------------------------------------------------------ #
    #  Cleanup                                                             #
    # ------------------------------------------------------------------ #
    def _cleanup_today_revaluation_moves(self):
        """
        Delete moves dated TODAY that are linked to stock valuation layers.
        These are the spurious revaluation entries Odoo fires on standard_price
        changes. Invoices, bills, and manual JEs are NOT touched.
        """
        today = fields.Date.today()
        moves = self.env['account.move'].search([
            ('date', '=', today),
            ('stock_valuation_layer_ids', '!=', False),
        ])
        _logger.info("Cleanup: removing %d today's revaluation move(s).", len(moves))
        for move in moves:
            mid = move.id
            _logger.info("  Deleting %s (ID %d)", move.name, mid)
            self.env.cr.execute("DELETE FROM account_move_line WHERE move_id=%s", (mid,))
            self.env.cr.execute(
                "UPDATE stock_valuation_layer SET account_move_id=NULL "
                "WHERE account_move_id=%s", (mid,)
            )
            self.env.cr.execute("DELETE FROM account_move WHERE id=%s", (mid,))
        self.env.cr.commit()

    # ------------------------------------------------------------------ #
    #  Main action                                                         #
    # ------------------------------------------------------------------ #
    def action_import_and_fix(self):
        """
        For every product row in the Excel file:
          1. Set standard_price via ORM.
          2. Find all target-date stock.valuation.layer records for its variants.
          3. Update layer unit_cost / value / remaining_value via SQL.
          4. Delete any existing journal entry for that layer.
          5. Create a fresh posted journal entry with the correct
             date, accounts (from Excel row), and amount.
          6. After all products are processed, delete today's accidental
             revaluation moves that step 1 triggered.
        """
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))

        excel_data  = base64.b64decode(self.excel_file)
        sheets_dict = pd.read_excel(io.BytesIO(excel_data), sheet_name=None)

        target_datetime = datetime.combine(self.target_date, datetime.min.time())
        jan_1_start = target_datetime.replace(hour=0,  minute=0,  second=0)
        jan_1_end   = target_datetime.replace(hour=23, minute=59, second=59)
        ctx = dict(self.env.context, force_period_date=target_datetime)

        # Pick the first sheet that has both required columns
        primary_df = None
        for sheet_name, df in sheets_dict.items():
            df.columns = df.columns.astype(str).str.strip()
            if 'id' in df.columns and 'standard_price' in df.columns:
                primary_df = df
                _logger.info("Primary sheet: '%s' (%d rows)", sheet_name, len(df))
                break

        if primary_df is None:
            raise UserError(
                _("No sheet found with both 'id' and 'standard_price' columns.")
            )

        df = primary_df
        debit_col  = next((c for c in df.columns if 'დებეტი'  in c or c.lower() == 'debit'),  None)
        credit_col = next((c for c in df.columns if 'კრედიტი' in c or c.lower() == 'credit'), None)

        journal = self._get_stock_valuation_journal()
        if not journal:
            raise UserError(
                _("No stock valuation journal found on this company. "
                  "Please create a General journal named 'Stock Valuation'.")
            )

        _logger.info(
            "Starting import: %d rows | target=%s | journal=%s | debit_col=%s | credit_col=%s",
            len(df), self.target_date, journal.name, debit_col, credit_col,
        )

        success_count = error_count = skipped_count = je_created = 0

        for index, row in df.iterrows():
            ext_id = str(row.get('id', '')).strip()
            if not ext_id or ext_id == 'nan':
                continue

            try:
                cost = float(row.get('standard_price', 0.0) or 0.0)

                record = self.env.ref(ext_id, raise_if_not_found=False)
                if not record or record._name not in ('product.product', 'product.template'):
                    _logger.warning("Row %s: '%s' not found as product.", index, ext_id)
                    error_count += 1
                    continue

                # Set cost (triggers spurious today-dated JE — cleaned up at end)
                record.with_context(ctx).write({'standard_price': cost})

                products = (
                    record.product_variant_ids
                    if record._name == 'product.template'
                    else record
                )

                # Resolve accounts once per row (same for all variants)
                debit_account  = self._get_account(row.get(debit_col))  if debit_col  else None
                credit_account = self._get_account(row.get(credit_col)) if credit_col else None

                for product in products:
                    layers = self.env['stock.valuation.layer'].search([
                        ('product_id', '=', product.id),
                        ('create_date', '>=', jan_1_start),
                        ('create_date', '<=', jan_1_end),
                    ])

                    if not layers:
                        skipped_count += 1
                        continue

                    # Category fallback if Excel accounts missing
                    prod_debit  = debit_account
                    prod_credit = credit_account
                    if not prod_debit or not prod_credit:
                        cat_d, cat_c = self._resolve_accounts_from_category(product)
                        prod_debit  = prod_debit  or cat_d
                        prod_credit = prod_credit or cat_c

                    for layer in layers:
                        qty       = layer.quantity
                        new_value = qty * cost
                        remaining_value = (
                            (layer.remaining_qty / qty) * new_value
                            if qty != 0 and layer.remaining_qty is not None
                            else 0.0
                        )

                        # Update layer
                        self.env.cr.execute("""
                            UPDATE stock_valuation_layer
                            SET    unit_cost       = %s,
                                   value           = %s,
                                   remaining_value = %s,
                                   create_date     = %s
                            WHERE  id = %s
                        """, (cost, new_value, remaining_value, target_datetime, layer.id))

                        # Flush ORM cache so layer.value reflects new_value
                        layer.invalidate_recordset()

                        # Delete old JE + create fresh one
                        self._delete_move_for_layer(layer)
                        move = self._create_journal_entry(
                            layer, target_datetime, prod_debit, prod_credit, journal
                        )
                        if move:
                            je_created += 1

                success_count += 1
                if success_count % 50 == 0:
                    self.env.cr.commit()
                    _logger.info("Committed %d products so far.", success_count)

            except Exception:
                _logger.error(
                    "Error on row %s (%s):\n%s", index, ext_id, traceback.format_exc()
                )
                error_count += 1

        # Clean up today's spurious moves AFTER the loop
        if self.cleanup_today:
            self._cleanup_today_revaluation_moves()

        self.env.cr.commit()

        msg = _(
            'Done. Products updated: %(p)d | Journal entries created: %(j)d | '
            'Variants with no Jan 1st layer: %(s)d | Errors: %(e)d.'
        ) % {'p': success_count, 'j': je_created, 's': skipped_count, 'e': error_count}

        _logger.info(msg)
        self.write({'state': 'done', 'result_message': msg})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Complete'),
                'message': msg,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True,
            },
        }

    def action_reset(self):
        self.write({'state': 'draft', 'result_message': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
