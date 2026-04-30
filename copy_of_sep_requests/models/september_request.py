from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SeptemberRequest(models.Model):
    _inherit = "september.request"

    def copy_to_inventory(self):
        _logger.info("=== STARTING COPY TO INVENTORY ===")

        for rec in self:
            _logger.info(f"Processing September Request: {rec.name} (ID: {rec.id})")

            # Create the inventory request header
            inventory_request = self.env["inventory.request"].create({
                "name": rec.name,
                "request_date": rec.request_date,
                "x_studio_request_number": rec.x_studio_request_number,
                "priority": rec.priority,
                "description": rec.description,
                "requested_by": rec.requested_by.id if rec.requested_by else False,
                "department_id": rec.x_studio_department.id if rec.x_studio_department else False,
                "september_request_id": rec.id,
                "status":rec.state,
                "dep_head":rec.x_studio_dep_head.id or False,
                "head":rec.x_studio_head_1.id or False,
                "finance_1":rec.x_studio_finance_1.id or False,
                "x_studio_many2one_field_es_1j76qfa82":rec.x_studio_.id or False,
                "location_object":rec.x_studio_related_field_2ki_1j4n18s40.id or False,
                "x_studio_selection_field_291_1j76pqq6p":rec.x_studio_selection_field_26n_1j3va76me or False, #ღონისძიება
                "x_studio_selection_field_6ca_1j76p9boc" : rec.x_studio_selection_field_74f_1j3r2r4dv or False, #მოთხოვნის კატეგორია
                "x_studio_many2one_field_212_1j76qnto4" : rec.budget_request_id.id or False, # budget
                "x_studio_char_field_8rb_1j76q19m8":rec.x_studio_char_field_8l3_1j3va9frb or False, #საფუძველი(სხვა)


            })
            _logger.info(f"✓ Created Inventory Request: {inventory_request.name} (ID: {inventory_request.id})")

            # Process each line
            _logger.info(f"Processing {len(rec.line_ids)} lines...")

            for line_num, sep_line in enumerate(rec.line_ids, 1):
                _logger.info(f"\n--- LINE {line_num}: {sep_line.name} ---")

                # Step 1: Map budget_main (budget.analytic) - DIRECT COPY
                budget_analytic_id = sep_line.budget_main.id if sep_line.budget_main else False
                _logger.info(f"budget_main (budget.analytic): {budget_analytic_id}")

                # Step 2: Find budget.line where account_id = budget_name_main AND within same budget.analytic
                budget_analytic_line_id = False
                if sep_line.budget_name_main and sep_line.budget_main:
                    _logger.info(f"Looking for budget.line where:")
                    _logger.info(f"  - account_id = {sep_line.budget_name_main.id} ({sep_line.budget_name_main.name})")
                    _logger.info(
                        f"  - within budget.analytic = {sep_line.budget_main.id} ({sep_line.budget_main.name})")

                    # Let's first check what field names exist in budget.line model
                    budget_line_fields = self.env["budget.line"]._fields.keys()
                    _logger.info(f"Available budget.line fields: {list(budget_line_fields)}")

                    # Try different possible field names for the budget relation
                    possible_budget_fields = ['budget_analytic_id', 'budget_id', 'analytic_budget_id', 'budget_main_id']
                    budget_field_name = None

                    for field_name in possible_budget_fields:
                        if field_name in budget_line_fields:
                            budget_field_name = field_name
                            _logger.info(f"Found budget relation field: {field_name}")
                            break

                    if budget_field_name:
                        budget_line = self.env["budget.line"].search([
                            ("account_id", "=", sep_line.budget_name_main.id),
                            (budget_field_name, "=", sep_line.budget_main.id)
                        ], limit=1)

                        if budget_line:
                            budget_analytic_line_id = budget_line.id
                            _logger.info(f"✓ Found budget.line: {budget_line.id} in budget {sep_line.budget_main.name}")
                        else:
                            _logger.warning(
                                f"✗ No budget.line found for account_id {sep_line.budget_name_main.id} in budget {sep_line.budget_main.id}")
                    else:
                        _logger.error(f"Could not find budget relation field in budget.line model")
                        # Fallback: search without budget constraint
                        budget_line = self.env["budget.line"].search([
                            ("account_id", "=", sep_line.budget_name_main.id)
                        ], limit=1)

                        if budget_line:
                            budget_analytic_line_id = budget_line.id
                            _logger.info(f"✓ Found budget.line (fallback): {budget_line.id}")
                        else:
                            _logger.warning(f"✗ No budget.line found even with fallback search")
                else:
                    _logger.info("Missing budget_name_main or budget_main - cannot search for budget.line")

                inventory_line_vals = {
                    "request_id": inventory_request.id,
                    "product_id": sep_line.product_id.id,
                    "name": sep_line.name,
                    "x_studio_code": sep_line.product_id.barcode,
                    "quantity": sep_line.quantity,
                    "unit_price": sep_line.unit_price,
                    "amount": sep_line.amount,
                    "notes": sep_line.notes,
                    "uom_id": sep_line.uom_id.id if sep_line.uom_id else False,
                    "expected_date": sep_line.expected_date,
                    "x_studio_requset_number": rec.x_studio_request_number,
                    "tag_ids": [(6, 0, sep_line.tag_ids.ids)] if sep_line.tag_ids else [],

                    "budget_analytic": budget_analytic_id,  # Direct copy from budget_main
                    "budget_analytic_line": budget_analytic_line_id,  # Found budget.line
                }

                # Handle stage mapping
                if sep_line.stage_id:
                    inv_stage = self.env["inventory.line.stage"].search([
                        ("name", "=", sep_line.stage_id.name)
                    ], limit=1)
                    inventory_line_vals["stage_id"] = inv_stage.id if inv_stage else False

                _logger.info(
                    f"Creating inventory line with budget_analytic={budget_analytic_id}, budget_analytic_line={budget_analytic_line_id}")

                # Create with context to prevent auto-computation
                inventory_line = self.env["inventory.line"].with_context(
                    keep_budget_from_september=True,
                    skip_budget_auto_fill=True
                ).create(inventory_line_vals)

                _logger.info(f"✓ Created inventory line {inventory_line.id}")

                # Verify the budget fields are correct
                _logger.info(f"VERIFICATION:")
                _logger.info(
                    f"  budget_analytic: {inventory_line.budget_analytic.id if inventory_line.budget_analytic else 'None'}")
                _logger.info(
                    f"  budget_analytic_line: {inventory_line.budget_analytic_line.id if inventory_line.budget_analytic_line else 'None'}")

        _logger.info("=== COPY TO INVENTORY COMPLETED ===")
        return True