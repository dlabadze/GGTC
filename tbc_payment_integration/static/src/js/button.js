/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class CustomListController extends ListController {
    setup() {
        super.setup();
    }

  onCustomButtonClick() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'tbc.movements.wizard',  // замените на вашу модель
            name: 'Open Custom Wizard',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

  TbcPdf() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'tbc.account.statement.wizard',  // замените на вашу модель
            name: 'Open Custom Wizard',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }
}

registry.category("views").add("custom_button_in_tree", {
    ...listView,
    Controller: CustomListController,
    buttonTemplate: "button_custom.ListView.Buttons",
});

export class PaymentIntegrationListController extends ListController {
    setup() {
        super.setup();
    }

    onOpenPaymentWizardClick() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'bog.payment.wizard',  // BOG Bank wizard
            name: 'Open BOG Payment Wizard',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

      BogPdf() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'bog.statement.pdf.wizard',  // замените на вашу модель
            name: 'Open Custom Wizard',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }
}

registry.category("views").add("payment_integration_list", {
    ...listView,
    Controller: PaymentIntegrationListController,
    buttonTemplate: "button_payment_integration.ListView.Buttons", // укажите имя вашего нового шаблона
});
