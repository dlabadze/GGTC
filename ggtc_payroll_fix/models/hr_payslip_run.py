from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_validate(self):
        """
        Override to ensure only one payslip per employee exists in this batch.
        If duplicates exist (due to multiple contracts), keep only the one
        linked to the latest contract and delete the rest.
        """
        self._remove_duplicate_payslips()
        return super().action_validate()

    def _remove_duplicate_payslips(self):
        """
        For each batch, find employees with more than one payslip.
        Keep only the payslip linked to the latest (newest) contract.
        Delete all others.
        """
        for run in self:
            # Group payslips by employee
            employee_payslips = {}
            for slip in run.slip_ids:
                emp_id = slip.employee_id.id
                if emp_id not in employee_payslips:
                    employee_payslips[emp_id] = []
                employee_payslips[emp_id].append(slip)

            for emp_id, slips in employee_payslips.items():
                if len(slips) <= 1:
                    # No duplicate, nothing to do
                    continue

                _logger.info(
                    "Employee ID %s has %d payslips in batch %s - keeping only latest contract",
                    emp_id, len(slips), run.name
                )

                # Find the slip with the latest contract start date
                def get_contract_start(slip):
                    if slip.contract_id and slip.contract_id.date_start:
                        return slip.contract_id.date_start
                    # Fallback: use slip id (higher id = created later)
                    from datetime import date
                    return date.min

                slips_sorted = sorted(slips, key=get_contract_start, reverse=True)

                # Keep the first one (latest contract), delete the rest
                slip_to_keep = slips_sorted[0]
                slips_to_delete = slips_sorted[1:]

                for slip in slips_to_delete:
                    _logger.info(
                        "Deleting duplicate payslip ID %s (contract: %s, start: %s) for employee ID %s",
                        slip.id,
                        slip.contract_id.name if slip.contract_id else 'N/A',
                        slip.contract_id.date_start if slip.contract_id else 'N/A',
                        emp_id
                    )
                    slip.action_payslip_cancel()
                    slip.unlink()

                _logger.info(
                    "Kept payslip ID %s (contract: %s, start: %s) for employee ID %s",
                    slip_to_keep.id,
                    slip_to_keep.contract_id.name if slip_to_keep.contract_id else 'N/A',
                    slip_to_keep.contract_id.date_start if slip_to_keep.contract_id else 'N/A',
                    emp_id
                )


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        """
        Override the batch generation wizard to only create one payslip
        per employee using their latest active contract.
        """
        res = super().compute_sheet()

        # After generation, clean up duplicates in the current run
        run = self.env['hr.payslip.run'].browse(self._context.get('active_id'))
        if run:
            run._remove_duplicate_payslips()

        return res
