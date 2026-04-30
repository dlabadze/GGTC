/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

/**
 * List view field widget that renders nothing in data rows.
 * Used with sum= on the column so the group row still shows the aggregate (e.g. sum).
 */
export class GroupSumOnlyField extends Component {
    static template = "salary_accrual_report.GroupSumOnlyField";
    static props = {
        ...standardFieldProps,
    };
    static supportedTypes = ["float", "integer"];
}

export const groupSumOnlyField = {
    component: GroupSumOnlyField,
    displayName: "Group sum only",
    supportedTypes: ["float", "integer"],
};

registry.category("fields").add("group_sum_only", groupSumOnlyField);
