from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError




class AccountAsset(models.Model):
    _inherit = 'account.asset'

    gadziritadeba_line_id = fields.Many2one(
        'gadziritadeba_det', 
        string='Gadziritadeba Line',
        help='Link to the gadziritadeba detail line that created this asset'
    )
    
    gadziritadeba_id = fields.Many2one(
        'gadziritadeba',
        string='Gadziritadeba',
        related='gadziritadeba_line_id.gadziritadeba_id',
        store=True,
        help='Link to the main gadziritadeba record'
    )


    mcirefasiani = fields.Boolean(string='მცირე ფასიანი', default=False)
    aqtnumbos = fields.Text(string="აქტის ნომერი")

    total_depreciated_value = fields.Float(
        string="Total Depreciated",
        compute="_compute_total_depreciated_value",
        store=True
    )

    @api.depends('depreciation_move_ids.line_ids.credit', 'depreciation_move_ids.state')
    def _compute_total_depreciated_value(self):
        for asset in self:
            total = 0.0
            for move in asset.depreciation_move_ids:
                if move.state == 'posted':  # only posted entries
                    # accumulate using credit lines of the accumulated depreciation account
                    lines = move.line_ids.filtered(
                        lambda l: l.account_id.id == asset.account_depreciation_id.id
                    )
                    total += sum(lines.mapped('credit'))
            asset.total_depreciated_value = total

class Gadziritadeba(models.Model):
    _name = 'gadziritadeba'
    _description = 'საწყობის მოდულიდან ექსპლუატაცია'
    _order = 'date desc, id desc'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('seen',  'Seen'),
        ('validated', 'Validated')
    ], default='draft', string='Status')

    picking_id = fields.Many2one(
        'stock.picking',
        string='აირჩიეთ ჩამოწერა',
        domain="[('picking_type_id.code', '=', 'internal'), ('state', '=', 'done')]",
        required=True
    )
    date = fields.Date(
        string="ექსპლუატაციაში გაშვების თარიღი", 
        default=fields.Date.context_today,
        required=True
    )
    gamcsaw = fields.Text(string="გამცემი საწყობი")
    mimpiri = fields.Text(string="მიმღები პირი")
    aqtnumb = fields.Text(string="აქტის ნომერი")
    comment = fields.Text(string="საფუძველი")
    requestnum = fields.Text(string = "მოთხოვნის ნომერი")
    dzkodandnam = fields.Text(string = "ძირითადი საშუალება")
    gadziritadeba_line_ids = fields.One2many(
        'gadziritadeba_det', 'gadziritadeba_id', string='Transferred Products'
    )

    @api.constrains('gadziritadeba_line_ids')
    def _check_lines_exist(self):
        """Ensure at least one line exists before validation"""
        for record in self:
            if record.state == 'validated' and not record.gadziritadeba_line_ids:
                raise ValidationError("At least one product line is required for validation.")

 #   @api.onchange('picking_id')
 #   def _onchange_picking_id(self):
 #       """Auto-populate product lines from selected stock picking"""
 #       if not self.picking_id:
 #           self.gadziritadeba_line_ids = [(5, 0, 0)]  # Clear existing lines
 #           return
            
        # Validate picking destination location
 #       if self.picking_id.location_dest_id.usage not in ['inventory', 'scrap']:
 #           return {
 #               'warning': {
 #                   'title': 'Invalid Picking',
 #                   'message': 'Selected picking must transfer to inventory or scrap location.'
 #               }
 #           }

        # Create lines from picking moves
 #       lines = []
 #       for move in self.picking_id.move_ids:
 #           if move.product_uom_qty > 0:  # Only include moves with positive quantity
 #               lines.append((0, 0, {
 #                   'product_id': move.product_id.id,
 #                   'quantity': move.product_uom_qty,
 #                   'price': move.product_id.standard_price,
 #                   'sumofdzs': move.product_id.standard_price * move.product_uom_qty, 
 #               }))
 #       
 #       self.gadziritadeba_line_ids = lines  return




    







    def assets(self):
         return {
            'name': 'Linked Assets',
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'list,form',
            'domain': [
                ('gadziritadeba_id', '=', self.id),
            ],
        }

    def action_validate(self):
        """Validate record and create assets with grouped dziritad logic and per-unit split"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError("Only draft records can be validated.")
        if not self.gadziritadeba_line_ids:
            raise UserError("Cannot validate without product lines.")

        Move = self.env['account.move']
        Asset = self.env['account.asset']
        Assetmovv = self.env['x_asset_movement_log']

        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if not journal:
            raise UserError("No general journal found. Please create a general journal first.")

        expense_account = self.env['account.account'].search([('code', '=', '7455')], limit=1)
        if not expense_account:
            raise UserError("Depreciation expense account (7455) not found.")

        # --- GROUPING ---
        grouped_lines = {}
        dziritad_lines = self.gadziritadeba_line_ids.filtered('dziritad')

        # Collect all dziritad groups first
        for dz_line in dziritad_lines:
            group_name = dz_line.group_asset_name.strip() if dz_line.group_asset_name else dz_line.product_id.name
            refkodd    = dz_line.product_id.default_code
            grouped_lines[group_name] = [dz_line]

        # Add extra lines belonging to those groups
        for line in self.gadziritadeba_line_ids.filtered(lambda l: not l.dziritad and l.group_asset_name):
            group_name = line.group_asset_name.strip()
            if group_name in grouped_lines:
                grouped_lines[group_name].append(line)

        # --- PROCESS GROUPED / DZIRITAD ASSETS ---
        for group_name, lines in grouped_lines.items():
            dziritad_line = next((l for l in lines if l.dziritad), None)
            if not dziritad_line:
                continue

            dz_qty = dziritad_line.quantity or 1
            total_value = sum(l.sumofdzs for l in lines)
            per_unit = dziritad_line.per_unit

            asset_account = dziritad_line.account_id.id
            source_account = dziritad_line.product_id.categ_id.property_stock_account_output_categ_id.id
            partner_id = self.env.company.partner_id.id or 1

            if not asset_account or not source_account:
                raise UserError(f"Missing account configuration for {group_name}")

            # --- Increase existing asset if set ---
            if dziritad_line.asset_idd:
                modify_wizard = self.env['asset.modify'].create({
                    'asset_id': dziritad_line.asset_idd.id,
                    'modify_action': 'modify',
                    'date': self.date,
                    'value_residual': total_value,
                    'salvage_value': 0.0,
                    'account_asset_id': dziritad_line.asset_idd.account_asset_id.id,
                    'account_asset_counterpart_id': source_account,
                    'account_depreciation_id': dziritad_line.asset_idd.account_depreciation_id.id,
                    'account_depreciation_expense_id': expense_account.id,
                    'name': f'Asset increase from gadziritadeba: {self.comment or ""}',
                })
                modify_wizard.modify()
                dziritad_line.asset_idd.write({'gadziritadeba_line_id': dziritad_line.id})
                continue

            # --- Otherwise create new asset(s) ---
            if per_unit:
                unit_value = total_value / dz_qty
                for i in range(int(dz_qty)):
                    move = Move.create({
                        'date': self.date,
                        'journal_id': journal.id,
                        'ref': f'ექსპლუატაცია {group_name} #{i + 1}',
                        'line_ids': [
                            (0, 0, {
                                'account_id': asset_account,
                                'debit': unit_value,
                                'credit': 0,
                                'name': f'{group_name} #{i + 1}',
                                'partner_id': partner_id
                            }),
                            (0, 0, {
                                'account_id': source_account,
                                'debit': 0,
                                'credit': unit_value,
                                'name': f'{group_name} #{i + 1}'
                            }),
                        ]
                    })
                    move.action_post()


                    valuation_move = dziritad_line.x_studio_dakavshirebuligat

                    if valuation_move and valuation_move.state == 'posted':
                    # Find the stock valuation line (1613 debit)
                      stock_line = valuation_move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.debit > 0
                         )[:1]

                     # Find your capitalization line (1613 credit)
                      gadziri_line = move.line_ids.filtered(
                         lambda l: l.account_id.code == '1613' and l.credit > 0
                          )[:1]

                      if stock_line and gadziri_line:
                       (stock_line + gadziri_line).reconcile()
                     

                    asset_line = move.line_ids.filtered(lambda l: l.debit > 0 and l.account_id.id == asset_account)
                    asset = Asset.create({
                        'name': group_name, #f'{group_name} #{i + 1}',
                        'original_value': unit_value,
                        'acquisition_date': self.date,
                        'account_asset_id': asset_account,
                        'account_depreciation_id': dziritad_line.account_depr_id.id,
                        'account_depreciation_expense_id': expense_account.id,
                        'original_move_line_ids': [(6, 0, asset_line.ids)],
                        'x_studio_lokacia_konk': self.x_studio_many2one_field_locationspec.id,
                        'x_studio_obieqti_lokacia': self.x_studio_many2one_field_locationspec.x_studio_object_location_rel.id,
                        'method_number': dziritad_line.depreciation_duration_months or 60,
                        'method_period': '1',
                        'gadziritadeba_line_id': dziritad_line.id,
                        'x_studio_motxovna': self.requestnum,
                        'x_studio_pasuxismgebeli_piri': self.x_studio_momtxovni.employee_id.id,
                        'x_studio_product_idk': refkodd,
                        'x_studio_shenishvna': self.comment,
                        'aqtnumbos' : self.aqtnumb,
                    })

                    if hasattr(asset, 'validate'):
                        asset.with_context(asset_validate=True).validate() #asset.validate()

                    Assetmovv.create({
                        'x_studio_sabechdi_veli': "პირადი სარგებლობა (განპიროვნება)",
                        'x_studio_sabechdi_veli_2': "(მ/გ და მასთან დაკავშირებული ინფრასტრუქტურის ექსლპატაცია)",
                        'x_name': f"{group_name} - {self.date}",
                        'x_studio_date': self.date,
                        'x_studio_many2many_field_lk_1iujl28b9': [asset.id],
                        'x_studio_object_location_1': self.x_studio_many2one_field_locationspec.x_studio_object_location_rel.id,
                        'x_studio_location_specific_1': self.x_studio_many2one_field_locationspec.id,
                        'x_studio_many2one_field_37d_1iulgqh70': self.x_studio_momtxovni.employee_id.id,
                        'x_studio_': f'[{self.requestnum}] {self.comment}'
                    })
            else:
                move = Move.create({
                    'date': self.date,
                    'journal_id': journal.id,
                    'ref': f'ექსპლუატაცია {group_name}',
                    'line_ids': [
                        (0, 0, {
                            'account_id': asset_account,
                            'debit': total_value,
                            'credit': 0,
                            'name': group_name,
                            'partner_id': partner_id
                        }),
                        (0, 0, {
                            'account_id': source_account,
                            'debit': 0,
                            'credit': total_value,
                            'name': group_name
                        }),
                    ]
                })
                move.action_post()

                valuation_move = dziritad_line.x_studio_dakavshirebuligat

                if valuation_move and valuation_move.state == 'posted':
                    # Find the stock valuation line (1613 debit)
                      stock_line = valuation_move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.debit > 0
                         )[:1]

                     # Find your capitalization line (1613 credit)
                      gadziri_line = move.line_ids.filtered(
                         lambda l: l.account_id.code == '1613' and l.credit > 0
                          )[:1]

                      if stock_line and gadziri_line and abs(stock_line.debit - gadziri_line.credit) < 0.01:
                       (stock_line + gadziri_line).reconcile()

                asset_line = move.line_ids.filtered(lambda l: l.debit > 0 and l.account_id.id == asset_account)
                asset = Asset.create({
                    'name': group_name,
                    'original_value': total_value,
                    'acquisition_date': self.date,
                    'account_asset_id': asset_account,
                    'account_depreciation_id': dziritad_line.account_depr_id.id,
                    'account_depreciation_expense_id': expense_account.id,
                    'x_studio_lokacia_konk': self.x_studio_many2one_field_locationspec.id,
                    'x_studio_obieqti_lokacia': self.x_studio_many2one_field_locationspec.x_studio_object_location_rel.id,
                    'original_move_line_ids': [(6, 0, asset_line.ids)],
                    'method_number': dziritad_line.depreciation_duration_months or 60,
                    'method_period': '1',
                    'gadziritadeba_line_id': dziritad_line.id,
                    'x_studio_motxovna': self.requestnum,
                    'x_studio_pasuxismgebeli_piri': self.x_studio_momtxovni.employee_id.id,
                    'x_studio_product_idk': refkodd,
                    'x_studio_shenishvna': self.comment,
                    'aqtnumbos' : self.aqtnumb,
                })

                if hasattr(asset, 'validate'):
                    asset.with_context(asset_validate=True).validate() #asset.validate()

                Assetmovv.create({
                    "x_studio_sabechdi_veli": "პირადი სარგებლობა (განპიროვნება)",
                    "x_studio_sabechdi_veli_2": "(მ/გ და მასთან დაკავშირებული ინფრასტრუქტურის ექსლპატაცია)",
                    'x_name': f"{group_name} - {self.date}",
                    'x_studio_date': self.date,
                    "x_studio_many2many_field_lk_1iujl28b9": [asset.id],
                    'x_studio_object_location_1': self.x_studio_many2one_field_locationspec.x_studio_object_location_rel.id,
                    'x_studio_location_specific_1': self.x_studio_many2one_field_locationspec.id,
                    'x_studio_many2one_field_37d_1iulgqh70': self.x_studio_momtxovni.employee_id.id,
                    'x_studio_': f'[{self.requestnum}] {self.comment}'
                })

        # --- მცირე ფასიანი (mcirefas) ---
        mcirefas_lines = self.gadziritadeba_line_ids.filtered(
            lambda l: not l.dziritad and not l.group_asset_name and l.mcirefas
        )

        if mcirefas_lines:
            Move = self.env['account.move']
            Asset = self.env['account.asset']

            journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
            expense_7460 = self.env['account.account'].search([('code', '=', '7460')], limit=1)
            stock_1613 = self.env['account.account'].search([('code', '=', '1613')], limit=1)

            if not expense_7460 or not stock_1613:
                raise UserError("Accounts 7460 or 1613 not found.")

            partner_id = self.env.company.partner_id.id or False

            for line in mcirefas_lines:
                amount = line.sumofdzs or 0.0

                # Create accounting move
                move = Move.create({
                    'date': self.date,
                    'journal_id': journal.id,
                    'ref': f'მცირე ფასიანი {line.product_id.display_name}',
                    'line_ids': [
                        (0, 0, {
                            'account_id': expense_7460.id,
                            'debit': amount,
                            'credit': 0.0,
                            'name': line.product_id.display_name,
                            'partner_id': partner_id,
                        }),
                        (0, 0, {
                            'account_id': stock_1613.id,
                            'debit': 0.0,
                            'credit': amount,
                            'name': line.product_id.display_name,
                        }),
                    ],
                })
                move.action_post()

                # Reconcile 1613 with valuation move if exists
                valuation_move = line.x_studio_dakavshirebuligat
                if valuation_move and valuation_move.state == 'posted':
                    stock_line = valuation_move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.debit > 0
                    )[:1]
                    gadziri_line = move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.credit > 0
                    )[:1]
                    if stock_line and gadziri_line and abs(stock_line.debit - gadziri_line.credit) < 0.01:
                        (stock_line + gadziri_line).reconcile()

                # Create zero-valued asset (mark as მცირე ფასიანი)
                asset = Asset.create({
                    'name': line.product_id.display_name,
                    'original_value': 0.0,
                    'acquisition_date': self.date,
                    'account_asset_id': expense_7460.id,
                    'account_depreciation_expense_id': expense_7460.id,
                    'account_depreciation_id': line.account_depr_id.id if getattr(line, 'account_depr_id', False) else False,
                    'x_studio_lokacia_konk': self.x_studio_many2one_field_locationspec.id,
                    'x_studio_obieqti_lokacia': self.x_studio_many2one_field_locationspec.x_studio_object_location_rel.id,
                    'method_number': 0,
                    'method_period': '1',
                    'gadziritadeba_line_id': line.id,
                    'x_studio_motxovna': self.requestnum,
                    'x_studio_pasuxismgebeli_piri': self.x_studio_momtxovni.employee_id.id,
                    'x_studio_product_idk': line.product_id.default_code,
                    'x_studio_shenishvna': self.comment,
                    'aqtnumbos': self.aqtnumb,
                    'mcirefasiani': True,
                })

                if hasattr(asset, 'validate'):
                    asset.with_context(asset_validate=True).validate() #asset.validate()

        self.write({'state': 'validated'})




    def action_reset_draft(self):
        """Reset record back to draft state"""
        self.ensure_one()
        
      #  if self.state != 'validated':
      #      raise UserError("Only validated records can be reset to draft.")
            
        self.write({'state': 'draft'})

    def action_seen_draft(self):
        """Record has been checked"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError("Only draft records can be checked.")
            
        self.write({'state': 'seen'})    