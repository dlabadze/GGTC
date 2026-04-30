from odoo import models, fields, api


class Operations(models.Model):
    _inherit = 'x_operations'

    # Global sequence
    command_seq = fields.Char(string="ბრძანება", readonly=True, copy=False)

    # Per-operation-type sequence
    operation_type_seq = fields.Integer(string="ოპერაციის ტიპის ID", readonly=True, copy=False)

    @api.model
    def create(self, vals):
        # Assign global command sequence
        if not vals.get('command_seq'):
            seq = self.env['ir.sequence'].next_by_code('x.operations.command.seq')
            vals['command_seq'] = seq or str(self.search([], order='id desc', limit=1).id + 1)

        # Assign per-operation-type sequence
        op_type = vals.get('x_studio_operationtype')
        if op_type:
            max_seq = self.search([('x_studio_operationtype', '=', op_type)],
                                  order='operation_type_seq desc',
                                  limit=1).operation_type_seq
            vals['operation_type_seq'] = (max_seq or 0) + 1
        else:
            vals['operation_type_seq'] = 1

        return super().create(vals)
