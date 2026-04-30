from odoo import models, Command, fields
import logging

_logger = logging.getLogger(__name__)

DEBUG_MODE = False


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    
    manual_account_id = fields.Many2one(
        'account.account',
        string='Manual Account',
        help='Account manually configured in Manual Operations. Updated by JavaScript when user changes account.',
    )

    def action_validate_batch(self):
        """ Batch validation method for server action. """
        success_count = 0
        error_count = 0
        errors = []
        
        for st_line in self:
            if st_line.is_reconciled:
                continue
            
            try:
                result = st_line.action_validate_preserve_accounts()
                if result.get('success'):
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"Line {st_line.id}: {result.get('message', 'Unknown error')}")
            except Exception as e:
                error_count += 1
                errors.append(f"Line {st_line.id}: {str(e)}")
                _logger.exception("Error validating statement line %s", st_line.id)
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:50],
        }

    def action_validate_preserve_accounts(self):
        self.ensure_one()
        
        if 'bank.rec.widget' not in self.env:
            return {'success': False, 'message': 'Bank reconciliation widget not available'}
        
        return self._validate_single_preserve_accounts(self.env['bank.rec.widget'])

    def _validate_single_preserve_accounts(self, BankRecWidget):
        if self.is_reconciled:
            return {'success': False, 'message': 'Already reconciled'}
        
        if not self.move_id:
            return {'success': False, 'message': 'No move found'}
        
        # 1. Initialize widget
        widget = BankRecWidget.with_context(default_st_line_id=self.id).new({})
        
        # 2. Trigger matching rules (like Odoo does when you open or validate)
        widget._action_trigger_matching_rules()
        
        # 3. Preserve account logic
        preserve_account_id = self.manual_account_id.id if self.manual_account_id else None
        
        # If no manual account, try to find one from existing move lines (excluding liquidity/suspense/partner)
        if not preserve_account_id:
            journal = self.journal_id
            partner = self.partner_id
            amount = self.amount
            
            liquidity_account_id = journal.default_account_id.id if journal.default_account_id else None
            suspense_account_id = journal.suspense_account_id.id if journal.suspense_account_id else None
            
            partner_account_id = None
            if partner:
                if amount > 0:
                    partner_account_id = partner.property_account_receivable_id.id
                else:
                    partner_account_id = partner.property_account_payable_id.id
            
            exclude_accounts = {liquidity_account_id, suspense_account_id, partner_account_id}
            exclude_accounts.discard(None)
            
            for aml in self.move_id.line_ids:
                aml_account_id = aml.account_id.id
                if aml_account_id and aml_account_id not in exclude_accounts:
                    preserve_account_id = aml_account_id
                    break

        # 4. Apply the preserved account to the widget lines if they are manual or auto-balance
        if preserve_account_id:
            widget._ensure_loaded_lines()
            for wline in widget.line_ids:
                if wline.flag in ('auto_balance', 'manual') and wline.account_id:
                    if wline.account_id.id != preserve_account_id:
                        wline.account_id = preserve_account_id

        # 5. Validate if state is valid
        state = widget.state
        if state == 'valid':
            try:
                widget._action_validate()
                if DEBUG_MODE:
                    _logger.info("Validated statement line %s successfully", self.id)
                return {'success': True, 'message': 'Validated successfully'}
            except Exception as e:
                return {'success': False, 'message': str(e)}
        elif state == 'reconciled':
            return {'success': False, 'message': 'Already reconciled'}
        elif state == 'invalid':
            return {'success': False, 'message': 'Cannot validate - suspense account still involved or unbalanced'}
        else:
            return {'success': False, 'message': f'Cannot validate - state is {state}'}
