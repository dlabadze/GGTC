# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_account_ang = fields.Many2one(
        'account.account',
        string='Reconciliation Account',
        domain="[('deprecated', '=', False)]",
        help='Account to use for reconciliation of internal transfer accounting entries. '
             'This account will be used if move_account_ang is not set on individual moves.',
        check_company=True,
    )

    def _check_internal_transfer(self):
        """Check if this picking is an internal transfer"""
        return self.picking_type_id.code == 'internal'

    @api.depends('picking_type_id.code')
    def _compute_is_internal(self):
        """Compute if picking is internal transfer"""
        for picking in self:
            picking.is_internal_transfer = picking._check_internal_transfer()

    is_internal_transfer = fields.Boolean(
        string='Is Internal Transfer',
        compute='_compute_is_internal',
        store=True,
    )
    
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        compute='_compute_is_reconciled',
        store=True,
        help='Indicates if the accounting entries for this picking have been reconciled.',
    )
    
    reconciliation_move_id = fields.Many2one(
        'account.move',
        string='Reconciliation Journal Entry',
        readonly=True,
        copy=False,
        help='Journal entry created for reconciliation of this picking',
        check_company=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Reconciliation Journal',
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        check_company=True,
        help='Analytic account to set on reconciliation journal lines that use the Reconciliation Account (stock_account_ang).',
    )

    @api.depends('move_ids.account_move_ids.line_ids.reconciled', 'state')
    def _compute_is_reconciled(self):
        """Compute if picking accounting entries are reconciled"""
        for picking in self:
            if picking.state != 'done' or not picking._check_internal_transfer():
                picking.is_reconciled = False
                continue
            
            # Check if destination location is inventory loss
            if picking.location_dest_id.usage != 'inventory':
                picking.is_reconciled = False
                continue
            
            # Get all account move lines from stock moves
            all_account_move_lines = self.env['account.move.line']
            for move in picking.move_ids:
                all_account_move_lines |= move._get_all_related_aml()
            
            # Filter only posted moves
            account_move_lines = all_account_move_lines.filtered(
                lambda aml: aml.move_id.state == 'posted'
            )
            
            if not account_move_lines:
                picking.is_reconciled = False
                continue
            
            # Check if all relevant lines are reconciled
            reconciled = True
            for move in picking.move_ids:
                if not move.product_id:
                    continue
                
                product_category = move.product_id.categ_id
                if not product_category:
                    continue
                
                output_account = product_category.property_stock_account_output_categ_id
                if not output_account:
                    continue
                
                # Get account move lines for this move that belong to the output account
                move_aml = move._get_all_related_aml().filtered(
                    lambda aml: aml.move_id.state == 'posted' 
                    and aml.account_id == output_account
                )
                
                # Check if all lines are reconciled
                if move_aml and not all(move_aml.mapped('reconciled')):
                    reconciled = False
                    break
            
            picking.is_reconciled = reconciled

    def action_reconcile_account_entries(self):
        """
        Action to reconcile account move lines created from stock moves.
        Reconciliation logic:
        - Check if destination location is inventory loss (usage == 'inventory')
        - For each product in the operation, find its category
        - Get property_stock_account_output_categ_id from the category
        - Create a journal entry in Miscellaneous journal
        - Reconcile the new journal entry lines with existing account move lines
        """
        self.ensure_one()
        
        if not self._check_internal_transfer():
            raise UserError(_('This action is only available for Internal Transfers.'))
        
        if self.state != 'done':
            raise UserError(_('Picking must be in Done state to reconcile accounting entries.'))
        
        # Check if destination location is inventory loss
        if self.location_dest_id.usage != 'inventory':
            raise UserError(_(
                'Reconciliation is only available for operations where destination location is Inventory Loss. '
                'Current destination location: %s'
            ) % self.location_dest_id.display_name)

        # Get Miscellaneous journal (type='general'), preferring ones marked for stock reconciliation
        # journal = self.env['account.journal'].search([
        #     ('type', '=', 'general'),
        #     ('use_for_stock_reconcile', '=', True),
        #     ('company_id', '=', self.company_id.id),
        # ], limit=1)
        journal = self.journal_id

        # Fallback: if none explicitly marked, use any Miscellaneous journal for the company
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)

        if not journal:
            raise UserError(_('Miscellaneous journal not found. Please create a journal with type "General" and optionally mark it for stock reconciliation.'))
        
        # Get all account move lines from stock moves
        all_account_move_lines = self.env['account.move.line']
        for move in self.move_ids:
            all_account_move_lines |= move._get_all_related_aml()
        
        # Filter only posted moves
        account_move_lines = all_account_move_lines.filtered(
            lambda aml: aml.move_id.state == 'posted' and not aml.reconciled
        )
        
        # Check if already reconciled first
        if self.is_reconciled:
            raise UserError(_('This operation has already been reconciled.'))
        
        if not account_move_lines:
            # Check if there are any account move lines at all
            all_posted_lines = all_account_move_lines.filtered(
                lambda aml: aml.move_id.state == 'posted'
            )
            if all_posted_lines:
                raise UserError(_('All accounting entries for this picking are already reconciled.'))
            else:
                raise UserError(_('No accounting entries found for this picking. Please ensure the picking has been validated and accounting entries have been created.'))
        
        # Group lines by product and get reconciliation accounts
        reconciliation_data = []
        moves_without_account = []
        
        for move in self.move_ids:
            if not move.product_id:
                continue
            
            # Get product category
            product_category = move.product_id.categ_id
            if not product_category:
                continue
            
            # Get output account from category (this will be CREDIT)
            output_account = product_category.property_stock_account_output_categ_id
            if not output_account:
                continue
            
            # Get reconciliation account (this will be DEBIT)
            # Use move_account_ang if set, otherwise use stock_account_ang
            recon_account = move.move_account_ang or self.stock_account_ang
            
            # Validation: if both are empty, add to error list
            if not recon_account:
                moves_without_account.append(move)
                continue
            
            # Get account move lines for this move that belong to the output account
            move_aml = move._get_all_related_aml().filtered(
                lambda aml: aml.move_id.state == 'posted' 
                and aml.account_id == output_account
                and not aml.reconciled
            )
            
            if not move_aml:
                continue
            
            # Calculate total amount (absolute value of balance)
            total_amount = abs(sum(move_aml.mapped('balance')))
            
            if total_amount < 0.01:  # Skip if amount is zero
                continue
            
            reconciliation_data.append({
                'output_account': output_account,
                'recon_account': recon_account,
                'amount': total_amount,
                'lines': move_aml,
                'move': move,
            })
        
        # Validation: if any move doesn't have reconciliation account, show error
        if moves_without_account:
            move_names = '\n'.join([f"- {m.name} ({m.product_id.name})" for m in moves_without_account])
            raise UserError(_(
                'Please set reconciliation account for all moves.\n\n'
                'For each move, you must set either:\n'
                '- Move Account (move_account_ang) on the move, OR\n'
                '- Stock Account (stock_account_ang) on the picking\n\n'
                'Moves without account:\n%s'
            ) % move_names)
        
        if not reconciliation_data:
            raise UserError(_(
                'No account move lines found for reconciliation. '
                'Please check that products have stock output accounts configured in their categories.'
            ))
        
        # Create journal entry lines for reconciliation
        move_line_vals = []
        lines_to_reconcile_by_account = {}
        
        for data in reconciliation_data:
            output_account = data['output_account']
            recon_account = data['recon_account']
            amount = data['amount']
            lines = data['lines']
            
            # Generate matching number for this reconciliation
            matching_number = f"REC-{self.id}-{move.id}"
            
            # Analytic only on lines whose account is the picking's stock_account_ang
            debit_line_vals = {
                'name': _('Reconciliation for %s') % self.name,
                'account_id': recon_account.id,
                'debit': amount,
                'credit': 0.0,
                'partner_id': False,
                'matching_number': matching_number,
            }
            if recon_account == self.stock_account_ang and self.analytic_account_id:
                debit_line_vals['analytic_distribution'] = {str(self.analytic_account_id.id): 100.0}
            move_line_vals.append(debit_line_vals)
            
            # Credit: output_account (property_stock_account_output_categ_id)
            move_line_vals.append({
                'name': _('Reconciliation for %s') % self.name,
                'account_id': output_account.id,
                'debit': 0.0,
                'credit': amount,
                'partner_id': False,
                'matching_number': matching_number,
            })
            
            # Store lines for reconciliation
            if output_account not in lines_to_reconcile_by_account:
                lines_to_reconcile_by_account[output_account] = self.env['account.move.line']
            lines_to_reconcile_by_account[output_account] |= lines
        
        if not move_line_vals:
            raise UserError(_('No lines to reconcile.'))
        
        # Create the journal entry
        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': _('Reconciliation for %s') % self.name,
            'move_type': 'entry',
            'line_ids': [(0, 0, line_vals) for line_vals in move_line_vals],
        }
        
        reconciliation_move = self.env['account.move'].create(move_vals)
        reconciliation_move._post()
        
        # Store the reconciliation move on the picking
        self.write({'reconciliation_move_id': reconciliation_move.id})
        
        # Reconcile the new lines with existing lines
        reconciled_count = 0
        for idx, data in enumerate(reconciliation_data):
            output_account = data['output_account']
            recon_account = data['recon_account']
            lines = data['lines']
            matching_number = f"REC-{self.id}-{data['lines'][0].move_id.stock_move_id.id if data['lines'][0].move_id.stock_move_id else 'unknown'}"
            
            # Get the new credit line from reconciliation move (output_account)
            # IMPORTANT:
            # - We must NOT reuse lines that have already been reconciled in a previous
            #   iteration, otherwise Odoo will raise:
            #   "You are trying to reconcile some entries that are already reconciled."
            # - This typically happens when several products share the same interim
            #   account (e.g. 1613 / 110300 Stock Interim (Delivered)).
            new_credit_line = reconciliation_move.line_ids.filtered(
                lambda l: l.account_id == output_account
                and l.credit > 0
                and not l.reconciled
            )
            
            # If all credit lines on this account are already reconciled, skip
            if not new_credit_line:
                continue
            
            # In case there are multiple still-unreconciled credit lines on this
            # account, use only one line for this group to avoid mixing groups.
            new_credit_line = new_credit_line[:1]
            
            # Set matching_number on existing lines before reconciliation
            if output_account.reconcile:
                lines_to_reconcile = lines.filtered(lambda l: not l.reconciled)
                if lines_to_reconcile:
                    lines_to_reconcile.write({'matching_number': matching_number})
                    
                    # Combine existing lines with the specific new credit line
                    all_lines = lines_to_reconcile | new_credit_line
                    
                    try:
                        all_lines.reconcile()
                        reconciled_count += len(all_lines)
                    except Exception as e:
                        raise UserError(_(
                            'Error reconciling lines for account %s: %s'
                        ) % (output_account.display_name, str(e)))
        
        if reconciled_count > 0:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reconciliation Entry'),
                'res_model': 'account.move',
                'res_id': reconciliation_move.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError(_('No lines were reconciled.'))
    
    def action_view_reconciliation_entry(self):
        """Open the reconciliation journal entry"""
        self.ensure_one()
        if not self.reconciliation_move_id:
            raise UserError(_('No reconciliation journal entry found for this picking.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconciliation Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.reconciliation_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
