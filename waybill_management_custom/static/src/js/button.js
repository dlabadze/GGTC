/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class Button_cont_1 extends ListController {
    setup() {
        super.setup();
    }

  button_1_click() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'fetch.waybills.wizard1',  // замените на вашу модель
            name: 'შესყიდვის დაბრუნება',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_1_list", {
    ...listView,
    Controller: Button_cont_1,
    buttonTemplate: "button_1.ListView.Buttons",
});

export class Button_cont_2 extends ListController {
    setup() {
        super.setup();
    }

  button_2_click() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'fetch.waybills.wizard3',  // замените на вашу модель
            name: 'რეალიზაციის დაბრუნება',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_2_list", {
    ...listView,
    Controller: Button_cont_2,
    buttonTemplate: "button_2.ListView.Buttons",
});

export class Button_cont_3 extends ListController {
    setup() {
        super.setup();
    }

  button_3_click() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'fetch.waybills.wizard4',  // замените на вашу модель
            name: 'შესყიდვა',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_3_list", {
    ...listView,
    Controller: Button_cont_3,
    buttonTemplate: "button_3.ListView.Buttons",
});

export class Button_cont_4 extends ListController {
    setup() {
        super.setup();
    }

  button_4_click() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'fetch.waybills.wizard5',  // замените на вашу модель
            name: 'შიდა გადაზიდვა',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_4_list", {
    ...listView,
    Controller: Button_cont_4,
    buttonTemplate: "button_4.ListView.Buttons",
});

export class Button_cont_5 extends ListController {
    setup() {
        super.setup();
    }

  button_5_click() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'fetch.waybills.wizard',  // замените на вашу модель
            name: 'რეალიზაცია',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
        });
    }

}

registry.category("views").add("button_5_list", {
    ...listView,
    Controller: Button_cont_5,
    buttonTemplate: "button_5.ListView.Buttons",
});

