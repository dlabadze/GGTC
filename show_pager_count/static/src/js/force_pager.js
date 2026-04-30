/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";

// Extend the existing ListController
export class AlwaysShowPagerListController extends ListController {
    get pager() {
        const pager = super.pager;
        if (pager && pager.limit >= pager.size) {
            // Force showing pager even when all records fit in one page
            pager.size = pager.limit + 1;  // ensures the pager renders
        }
        return pager;
    }
}

// Get the original list view definition
const listView = registry.category("views").get("list");

// Replace only the Controller
registry.category("views").category("list").add("always_show_pager_list", {
    ...listView,
    Controller: AlwaysShowPagerListController,
});

// OR (safer global override — doesn’t create a duplicate key)
registry.category("views").add("list", {
    ...listView,
    Controller: AlwaysShowPagerListController,
}, { force: true });
