/** @odoo-module **/

import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";
import { patch } from "@web/core/utils/patch";

patch(BankRecKanbanController.prototype, {
    async actionOpenBudgetPaymentWizard() {
        const state = this.state;
        const bankRecRecordData = state.bankRecRecordData;

        if (!bankRecRecordData || !bankRecRecordData.st_line_id) {
            this.notification.add(
                "No bank statement line found.",
                { type: "warning" }
            );
            return;
        }

        const stLineId = bankRecRecordData.st_line_id[0];

        const action = {
            type: 'ir.actions.act_window',
            name: 'ბიუჯეტის გადახდა',
            res_model: 'budget.payment.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_st_line_id: stLineId,
            }
        };

        await this.action.doAction(action);
    },

    /**
     * Open purchase requisition wizard
     */
    async actionOpenPurchaseRequisitionWizard() {
        const state = this.state;
        const bankRecRecordData = state.bankRecRecordData;

        if (!bankRecRecordData || !bankRecRecordData.st_line_id) {
            this.notification.add(
                "No bank statement line found.",
                { type: "warning" }
            );
            return;
        }

        // Get the statement line ID
        const stLineId = bankRecRecordData.st_line_id[0];

        console.log("Opening wizard for st_line_id:", stLineId);

        // Open wizard directly with st_line_id in context
        const action = {
            type: 'ir.actions.act_window',
            name: 'Select Purchase Requisition',
            res_model: 'purchase.requisition.payment.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_st_line_id: stLineId,
            }
        };

        await this.action.doAction(action);
    },
});
