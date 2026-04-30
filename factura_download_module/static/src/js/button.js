/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class Button_cont_1_fac extends ListController {
    setup() {
        super.setup();
    }

  button_1_click_fac() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'faqturis.gadmowera.realizacia.buyer',  // замените на вашу модель
            name: 'შესყიდვა',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_1_list_fac", {
    ...listView,
    Controller: Button_cont_1_fac,
    buttonTemplate: "button_1_fac.ListView.Buttons",
});

export class Button_cont_2_fac extends ListController {
    setup() {
        super.setup();
    }

  button_2_click_fac() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'faqturis.gadmowera.realizacia',  // замените на вашу модель
            name: 'რეალიზაცია',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_2_list_fac", {
    ...listView,
    Controller: Button_cont_2_fac,
    buttonTemplate: "button_2_fac.ListView.Buttons",
});


