/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";
import { onPatched } from "@odoo/owl";

patch(BankRecKanbanController.prototype, {
    setup() {
        super.setup();
        
        onPatched(() => {
            this._saveManualAccountIfChanged();
        });
    },
    
    async _saveManualAccountIfChanged() {
        const state = this.state;
        if (!state?.bankRecRecordData?.line_ids?.records) {
            return;
        }
        
        const stLineId = state.bankRecRecordData.st_line_id?.[0];
        if (!stLineId) {
            return;
        }
        
        const lines = state.bankRecRecordData.line_ids.records;
        let accountToSave = null;
        
        // Priority 1: Save account from manual lines (always manually configured)
        for (const line of lines) {
            const lineData = line.data;
            if (lineData.flag === 'manual' && lineData.account_id?.[0]) {
                accountToSave = lineData.account_id[0];
                console.log('[Bank Actions] Found manual line with account:', accountToSave);
                break;
            }
        }
        
        // Priority 2: Check auto_balance lines - if account differs from partner, it was manually configured
        if (!accountToSave) {
            const partnerId = state.bankRecRecordData.partner_id?.[0];
            let partnerAccountId = null;
            
            if (partnerId) {
                const amount = state.bankRecRecordData.st_line_amount;
                if (amount > 0) {
                    partnerAccountId = state.bankRecRecordData.partner_receivable_account_id?.[0];
                } else {
                    partnerAccountId = state.bankRecRecordData.partner_payable_account_id?.[0];
                }
            }
            
            for (const line of lines) {
                const lineData = line.data;
                if (lineData.flag === 'auto_balance' && lineData.account_id?.[0]) {
                    const accountId = lineData.account_id[0];
                    // If account differs from partner account, it was manually configured
                    if (!partnerAccountId || accountId !== partnerAccountId) {
                        accountToSave = accountId;
                        console.log('[Bank Actions] Found manually configured account from auto_balance:', accountToSave, '(partner account:', partnerAccountId, ')');
                        break;
                    }
                }
            }
        }
        
        // Save the account if found
        if (accountToSave) {
            try {
                await this.orm.call(
                    'account.bank.statement.line',
                    'write',
                    [[stLineId], {'manual_account_id': accountToSave}]
                );
                console.log('[Bank Actions] ✓ Saved manual account:', accountToSave);
            } catch (error) {
                console.error('[Bank Actions] ✗ Failed to save manual account:', error);
            }
        }
    },

    async actionLineChanged(fieldName) {
        const result = await super.actionLineChanged(fieldName);
        
        if (fieldName === 'account_id') {
            // Save immediately when account changes
            setTimeout(() => this._saveManualAccountIfChanged(), 100);
        }
        
        return result;
    },
    
    async actionReset() {
        // Save account before resetting
        await this._saveManualAccountIfChanged();
        return super.actionReset();
    },
});
