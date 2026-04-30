/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class PurchaseCheckWidget extends BooleanToggleField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async onChange(newValue) {
        if (newValue === true && this.props.record.resId) {
            const result = await this.orm.call(
                "inventory.line",
                "action_set_purchase",
                [[this.props.record.resId]]
            );
            if (result && result.type) {
                await this.actionService.doAction(result);
            } else {
                // no wizard (stage mismatch or no matches) - just save the field normally
                await super.onChange(newValue);
            }
        } else {
            await super.onChange(newValue);
        }
    }
}

registry.category("fields").add("purchase_check_widget", {
    ...booleanToggleField,
    component: PurchaseCheckWidget,
});
