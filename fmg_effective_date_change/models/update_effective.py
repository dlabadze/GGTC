from odoo import models, fields
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import date
from datetime import datetime

from odoo.release import product_name


class UpdateEffective(models.Model):
    _inherit = "stock.picking"

    date_of_transfer = fields.Datetime(string="Effective Date", default=fields.Datetime.now)

    def wiz_open(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'change.effective.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def button_validate(self):
        products = {}

        for picking in self:
            if not picking.date_of_transfer:
                raise ValidationError('The Effective Date is empty')

            if picking.picking_type_id.code == 'outgoing':
                for line in picking.move_ids_without_package:
                    if line.product_id.product_tmpl_id.categ_id.property_cost_method == 'average':
                        valuation_layers = self.env['stock.valuation.layer'].search([
                            ('product_id', '=', line.product_id.id),
                            ('reference', 'not like', str(picking.name + "%"))
                        ])

                        total_remaining_qty = 0
                        total_value = 0

                        for valuation_layer in valuation_layers:
                            total_value += valuation_layer.value
                            total_remaining_qty += valuation_layer.remaining_qty

                        # Get me product, total_value and total_remaining_qty and put it inside products dict
                        product_id = line.product_id.id
                        products[product_id] = {
                            'product': line.product_id,
                            'total_value': total_value,
                            'total_remaining_qty': total_remaining_qty
                        }

        res = super(UpdateEffective, self).button_validate()

        for picking in self:
            # Jika tanggal transfer kosong, maka skip kode perhitungan di bawah
            # dan gunakan perhitungan normal default milik Odoo.
            if picking.date_of_transfer:

                # Mengganti date_done (Effective Date)
                if picking.date_of_transfer != False:
                    selected_date = picking.date_of_transfer
                else:
                    selected_date = datetime.now()

                picking.date_done = selected_date

                # Mengganti tanggal stock.valuation.layer
                self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = (%s) WHERE description LIKE (%s)", [selected_date, str(picking.name + "%")])

                # Mengganti tanggal stock.move.line
                for stock_move_line in self.env['stock.move.line'].search([('reference', 'ilike', str(picking.name + "%"))]):
                    stock_move_line.date = selected_date

                # Mengganti tanggal stock.move
                for stock_move in self.env['stock.move'].search([('reference', 'ilike', str(picking.name + "%"))]):
                    stock_move.date = selected_date

                # Mengganti tanggal account.move.line
                self.env.cr.execute("UPDATE account_move_line SET date = (%s) WHERE ref SIMILAR TO %s", [selected_date, str(picking.name + "%")])

                # Mengganti tanggal account.move
                self.env.cr.execute("UPDATE account_move set date = (%s) WHERE ref SIMILAR TO %s", [selected_date, str(picking.name + "%")])

                # Mengambil Currency System ID
                system_default_currency = picking.company_id.currency_id.id
                purchase_order = picking.purchase_id

                # Jika PO picking merupakan incoming transfer serta Purchase Order menggunakan currency asing
                # Maka lakukan perhitungan ulang valuasi
                # Untuk internal process, kita tidak hitung ulang
                if picking.picking_type_id.code == 'internal':
                    pass

                elif picking.picking_type_id.code == 'outgoing':
                    # Check if its a return process:
                    if not self.return_id:
                        # We don't do recalculate the FIFO because the system are counting correctly
                        # However for AVCO, its unfortunately wrong so we re-computing it
                        if line.product_id.product_tmpl_id.categ_id.property_cost_method == 'average':

                            journal_entry_ids = []

                            for line in picking.move_ids_without_package:
                                product_id = line.product_id.id
                                if product_id in products:
                                    total_value = products[product_id]['total_value']
                                    total_remaining_qty = products[product_id]['total_remaining_qty']

                                    # Skip if no remaining quantity to avoid division by zero
                                    if total_remaining_qty == 0:
                                        continue

                                    average_product_value = total_value / total_remaining_qty

                                    current_valuation_layers = self.env['stock.valuation.layer'].search([
                                        ('product_id', '=', line.product_id.id),
                                        ('reference', 'ilike', str(picking.name + "%"))
                                    ])

                                    for val in current_valuation_layers:
                                        unit_value = average_product_value
                                        val.unit_cost = unit_value
                                        val.value = unit_value * val.quantity
                                        val.remaining_value = 0

                                    journal_entry = current_valuation_layers.account_move_id

                                    if journal_entry:
                                        for journal in journal_entry:
                                            for move_line in journal.line_ids:
                                                with self.env.cr.savepoint():
                                                    move_line.with_context(check_move_validity=False).write({
                                                        'debit': average_product_value * line.quantity if move_line.debit > 0 else move_line.debit,
                                                        'credit': average_product_value * line.quantity if move_line.credit > 0 else move_line.credit,
                                                    })

                                            journal_entry_ids.append(journal.id)

                                            # Ganti nama journal entry mengikuti tanggal
                                            # Pertama direset dulu nama dan prefixnya dan commit ke DB
                                            self.env.cr.execute("""
                                                                UPDATE account_move
                                                                SET name = '/',
                                                                    date = %s,
                                                                    sequence_prefix = '/'
                                                                WHERE id = %s
                                                            """, (selected_date, journal.id))

                                            self.env.cr.commit()

                            # Change journal entry name by re-posting it again
                            if journal_entry_ids:
                                for journal_entry_id in journal_entry_ids:
                                    account_move = self.env['account.move'].search([('id', '=', journal_entry_id)])

                                    # Repost the move to get a new sequence number based on the new date
                                    account_move.sudo().button_draft()
                                    account_move.sudo().action_post()
                                    account_move.made_sequence_gap = False
                    else:
                        pass

                elif picking.picking_type_id.code == 'incoming':
                    if not self.return_id:
                        if picking.picking_type_id.code == 'incoming' and purchase_order and int(purchase_order.currency_id.id) != system_default_currency:

                            stock_move_id = None

                            # Attempt to find the rate for the specified date
                            rate_record = self.env['res.currency.rate'].search([
                                ('currency_id', '=', int(purchase_order.currency_id)),
                                ('name', '=', selected_date.strftime('%Y-%m-%d'))
                            ], limit=1)

                            # If no rate is found for the specified date, get the latest rate BEFORE the selected date
                            if not rate_record:
                                rate_record = self.env['res.currency.rate'].search([
                                    ('currency_id', '=', int(purchase_order.currency_id)),
                                    ('name', '<', selected_date.strftime('%Y-%m-%d'))
                                ], order='name desc', limit=1)

                            # Extract the rate
                            rate = rate_record.inverse_company_rate if rate_record else 0.0

                            if rate == 0.0:
                                raise UserError('You have selected the currency rate of ' + str(purchase_order.currency_id.name) + ' which is currently not available based on your selected date. Make sure to fill it under Accounting > Settings > Currencies > ' + str(purchase_order.currency_id.name) + '!')
                            else:
                                duplicate_product = []
                                seen_product_ids = []

                                for product in purchase_order.order_line:
                                    product_id = product.product_id.id

                                    if product_id in seen_product_ids and product_id not in duplicate_product:
                                        duplicate_product.append(product_id)
                                    else:
                                        seen_product_ids.append(product_id)

                                # Initialize a dictionary to store PO details
                                po_details = {}
                                po_details_duplicate_product = []

                                # Populate PO details
                                for product in purchase_order.order_line:
                                    product_id = product.product_id.id
                                    if product_id not in po_details and product_id not in duplicate_product:
                                        po_details[product_id] = {
                                            'quantity': product.product_qty,
                                            'price_subtotal': product.price_subtotal,
                                        }
                                    elif product_id in duplicate_product:
                                        po_details_duplicate_product.append({
                                            'product_id': product_id,
                                            'quantity': product.product_qty,
                                            'price_subtotal': product.price_subtotal,
                                        })

                                # Match PO Detail dengan Picking karena bisa saja barang yang mau diterima hanya sebagian
                                price_unit = {}

                                journal_entry_ids = []
                                for line in picking.move_ids_without_package:

                                    if stock_move_id == None:
                                        stock_move_id = line.id

                                    product_id = line.product_id.id
                                    line_qty = line.quantity if line.quantity > 0 else line.product_uom_qty

                                    if product_id in po_details:
                                        po_product = po_details[product_id]
                                        po_qty = po_product['quantity']
                                        po_price_subtotal = po_product['price_subtotal']

                                        if line_qty <= po_qty:
                                            unit_value = po_price_subtotal * rate

                                            price_unit[product_id] = unit_value
                                            po_details[product_id]['quantity'] -= line_qty
                                        else:
                                            unit_value = po_price_subtotal * rate

                                            price_unit[product_id] = unit_value
                                            line_qty -= po_qty
                                            po_details[product_id]['quantity'] = 0

                                # Recalculate and update the stock valuation layers
                                valuation_layers_to_update = self.env['stock.valuation.layer']
                                for line in picking.move_ids_without_package:
                                    product_id = line.product_id.id
                                    if product_id not in duplicate_product:
                                        valuation_layers = self.env['stock.valuation.layer'].search([
                                            ('product_id', '=', product_id),
                                            ('reference', 'ilike', str(picking.name + "%"))
                                        ])

                                        for valuation_layer in valuation_layers:
                                            if product_id in price_unit:
                                                unit_value = price_unit[product_id]
                                                valuation_layer.unit_cost = unit_value / valuation_layer.quantity
                                                valuation_layer.value = valuation_layer.unit_cost * valuation_layer.quantity
                                                valuation_layer.remaining_value = valuation_layer.remaining_qty * (unit_value / valuation_layer.quantity)
                                                valuation_layers_to_update |= valuation_layer

                                                journal_entry = valuation_layer.account_move_id

                                                if journal_entry:
                                                    for journal in journal_entry:
                                                        for move_line in journal.line_ids:
                                                            with self.env.cr.savepoint():
                                                                move_line.with_context(check_move_validity=False).write({
                                                                    'debit': unit_value if move_line.debit > 0 else move_line.debit,
                                                                    'credit': unit_value if move_line.credit > 0 else move_line.credit,
                                                                })

                                                        journal_entry_ids.append(journal.id)

                                                        # Ganti nama journal entry mengikuti tanggal
                                                        # Pertama direset dulu nama dan prefixnya dan commit ke DB
                                                        self.env.cr.execute("""
                                                                    UPDATE account_move
                                                                    SET name = '/',
                                                                        date = %s,
                                                                        sequence_prefix = '/'
                                                                    WHERE id = %s
                                                                """, (selected_date, journal.id))

                                                        self.env.cr.commit()

                                    elif product_id in duplicate_product:
                                        valuation_layers = self.env['stock.valuation.layer'].search([
                                            ('product_id', '=', product_id),
                                            ('reference', 'ilike', str(picking.name + "%"))
                                        ])

                                        for valuation_layer in valuation_layers:
                                            if valuation_layer.account_move_id:
                                                valuation_layer.account_move_id.sudo().button_draft()
                                                valuation_layer.account_move_id.sudo().unlink()
                                            valuation_layer.sudo().unlink()

                                for product in po_details_duplicate_product:
                                    # Avoid division by zero
                                    if product['quantity'] > 0:
                                        unit_cost = (product['price_subtotal'] / product['quantity']) * rate
                                    else:
                                        unit_cost = 0

                                    # Create the valuation layer
                                    new_valuation_layer = self.env['stock.valuation.layer'].sudo().create({
                                        'product_id': product['product_id'],
                                        'quantity': product['quantity'],
                                        'remaining_qty': product['quantity'],
                                        'unit_cost': unit_cost,
                                        'value': product['price_subtotal'] * rate,
                                        'company_id': picking.company_id.id,
                                        'stock_move_id': stock_move_id,
                                    })

                                    # Then use SQL to update the create_date
                                    self.env.cr.execute("""
                                        UPDATE stock_valuation_layer
                                        SET create_date = %s
                                        WHERE id = %s
                                    """, (picking.date_of_transfer, new_valuation_layer.id))

                                    # Get the product once
                                    prod = self.env['product.product'].browse(product['product_id'])

                                    # Get the category once
                                    product_category = prod.product_tmpl_id.categ_id

                                    # Now use the cached product and category
                                    journal_id = product_category.property_stock_journal.id
                                    interim_stock_account_id = product_category.property_stock_account_input_categ_id.id
                                    inventory_account_id = product_category.property_stock_valuation_account_id.id

                                    move_vals = {
                                        'ref': picking.name,
                                        'journal_id': journal_id,
                                        'date': picking.date_of_transfer.date(),
                                        'company_id': picking.company_id.id,
                                        'line_ids': [
                                            (0, 0, {
                                                'name': f"{picking.name} - {prod.name}",
                                                'account_id': interim_stock_account_id,
                                                'partner_id': picking.partner_id.id,
                                                'debit': 0.0,
                                                'credit': product['price_subtotal'] * rate,
                                                'company_id': picking.company_id.id,
                                            }),
                                            (0, 0, {
                                                'name': f"{picking.name} - {prod.name}",
                                                'account_id': inventory_account_id,
                                                'partner_id': picking.partner_id.id,
                                                'debit': product['price_subtotal'] * rate,
                                                'credit': 0.0,
                                                'company_id': picking.company_id.id,
                                            })
                                        ]
                                    }

                                    journal_entry = self.env['account.move'].sudo().create(move_vals)
                                    journal_entry.sudo().action_post()
                                    new_valuation_layer.account_move_id = journal_entry.id

                                # Change journal entry name by re-posting it again
                                if journal_entry_ids:
                                    for journal_entry_id in journal_entry_ids:
                                        account_move = self.env['account.move'].search([('id', '=', journal_entry_id)])

                                        # Repost the move to get a new sequence number based on the new date
                                        account_move.sudo().button_draft()
                                        account_move.sudo().action_post()
                                        account_move.made_sequence_gap = False
                    else:
                        pass

                self.env.cr.commit()

                # Link lots in picking to each stock valuation
                for move in picking.move_ids_without_package:
                    # Get lots from move lines since lots are stored on move lines, not moves
                    if move.lot_ids:

                        self.env.cr.execute("""
                            UPDATE stock_lot
                            SET create_date = %s
                            WHERE id IN %s
                        """, (picking.date_done, tuple(move.lot_ids.ids)))

                        valuation_layers = self.env['stock.valuation.layer'].search([
                            ('product_id', '=', move.product_id.id),
                            ('reference', 'ilike', picking.name + "%")
                        ])

                        for valuation_layer in valuation_layers:
                            if not valuation_layer.lot_id:
                                # Take the first lot from move lines
                                valuation_layer.lot_id = move.lot_ids[0]

                                self.env.cr.execute("""
                                    UPDATE stock_lot
                                    SET standard_price = to_jsonb(%s::numeric)
                                    WHERE id IN %s
                                """, (valuation_layer.unit_cost, tuple(move.lot_ids.ids)))

        return res

