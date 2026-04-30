# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)


class BankRecWidgetExtend(models.AbstractModel):
    """Extend bank reconciliation widget to expose TBC doc_comment"""
    _inherit = 'bank.rec.widget'

    st_line_doc_comment = fields.Char(
        string='Document Comment',
        compute='_compute_st_line_doc_comment',
        help='Document comment from TBC transaction details'
    )

    show_purchase_requisition_button = fields.Boolean(
        string='Show Purchase Requisition Button',
        compute='_compute_show_purchase_requisition_button',
        help='Show purchase requisition button when valid'
    )

    def _validation_lines_vals(self, line_ids_create_command_list, aml_to_exchange_diff_vals, to_reconcile):
        """Override to preserve the statement line's original partner on the liquidity line
        for TBC transactions.

        Standard Odoo takes the single counterpart partner and applies it to the liquidity
        line too (via partner_to_set). Then _synchronize_from_moves propagates it back to the
        statement line, so all lines end up with the counterpart's partner.

        For TBC transactions we want different partners on the liquidity vs counterpart line
        (e.g. sender on bank line, beneficiary on expense line), so after super() runs we
        restore the original statement line partner on the liquidity line.
        """
        st_line = self.st_line_id
        original_partner_id = st_line.partner_id.id if st_line.partner_id else False
        is_tbc = False
        if st_line.transaction_details and isinstance(st_line.transaction_details, dict):
            is_tbc = bool(
                st_line.transaction_details.get('tbc_transaction_id')
                or st_line.transaction_details.get('tbc_movement_id')
            )

        super()._validation_lines_vals(line_ids_create_command_list, aml_to_exchange_diff_vals, to_reconcile)

        if is_tbc and original_partner_id:
            bank_account_id = st_line.journal_id.default_account_id.id
            for command in line_ids_create_command_list:
                # Command.create is (0, 0, vals_dict)
                if command[0] == 0:
                    vals = command[2]
                    if vals.get('account_id') == bank_account_id:
                        vals['partner_id'] = original_partner_id
                        _logger.info(
                            "TBC: Restored liquidity line partner_id to %s (original statement line partner)",
                            original_partner_id,
                        )

    @api.depends('st_line_id')
    def _compute_st_line_doc_comment(self):
        """Extract doc_comment from transaction_details JSON"""
        for wizard in self:
            doc_comment = False
            if wizard.st_line_id and wizard.st_line_id.transaction_details:
                try:
                    details = wizard.st_line_id.transaction_details
                    if isinstance(details, str):
                        details = json.loads(details)
                    doc_comment = details.get('doc_comment', False)
                except Exception as e:
                    _logger.warning("Failed to parse transaction_details: %s", str(e))
            wizard.st_line_doc_comment = doc_comment

    @api.depends('state')
    def _compute_show_purchase_requisition_button(self):
        """Show button when state is valid"""
        for wizard in self:
            wizard.show_purchase_requisition_button = wizard.state == 'valid'

    def action_open_purchase_requisition_wizard(self):
        """Open wizard to select purchase requisition and update paid amount"""
        self.ensure_one()

        if not self.st_line_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Purchase Requisition',
            'res_model': 'purchase.requisition.payment.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_st_line_id': self.st_line_id.id,
            }
        }

