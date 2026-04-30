/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class SeptemberLineListController extends ListController {
    setup() {
        super.setup();
    }

    onCreateBudgetingLinesClick() {

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "wizard.select.budget.request",
            view_mode: "form",
            view_type: 'form',
            views: [[false, 'form']],
            target: "new",
            res_id: false,
        });
    }
}

registry.category("views").add("september_line_list", {
    ...listView,
    Controller: SeptemberLineListController,
    buttonTemplate: "SeptemberLineListView.Buttons",
});
