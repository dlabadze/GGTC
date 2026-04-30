from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class Preiskuranti(models.Model):
    _name = 'preiskuranti'
    _description = 'preiskuranti'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # --- Main fields ---
    date = fields.Date(
        string="თარიღი",
        required=True,
        default=fields.Date.context_today
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="მომწოდებელი",
        required=True
    )
    preiskuranti_line_ids = fields.One2many(
        'preiskuranti_det',
        'preiskuranti_id',
        string='დეტალიზაცია'
    )
    candidate_line_ids = fields.One2many(
        'preiskuranti.candidate',
        'preiskuranti_id',
        string='შესათანხმებელი პროდუქცია'
    )
    model_ids = fields.Many2many(
        'fleet.vehicle.model',
        string="მოდელები"
    )

    name = fields.Char(string="დასახელება", required=False)

    active = fields.Boolean(
        string="აქტიური",
        default=True,
        help="Uncheck to archive this record."
    )

    purchase_agreement_id = fields.Many2one(
        'purchase.requisition',
        string="ხელშეკრულება"
    )

    total_preiskuranti = fields.Float(
        string="ჯამი პრეისკურანტი",
        compute='_compute_totals',
        store=True
    )
    initial_total = fields.Float(
        string="პირველადი ჯამი"
    )
    total_agreement = fields.Float(
        string="ჯამი ხელშეკრულება",
        compute='_compute_totals',
        store=True
    )

    @api.depends('preiskuranti_line_ids.fasi', 'purchase_agreement_id.contract_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_preiskuranti = sum(rec.preiskuranti_line_ids.mapped('fasi'))
            rec.total_agreement = rec.purchase_agreement_id.contract_amount or 0.0

    # @api.constrains('preiskuranti_line_ids', 'preiskuranti_line_ids.fasi', 'purchase_agreement_id')
    # def _check_preiskuranti_limit(self):
    #     """
    #     Constraint removed as per request.
    #     Previously checked if sum of all preiskurantis > 1.1 * agreement.
    #     """
    #     pass

class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    allowed_product_ids = fields.Many2many(
        'product.product',
        string='Allowed Products',
        compute='_compute_allowed_products',
        store=False,
    )

    allowed_preiskuranti_ids_new = fields.Many2many(
        'preiskuranti',
        string='Allowed preiskuranti',
        compute='_compute_allowed_preiskuranti',
        store=False,
    )

    preiskuranti_id_new = fields.Many2one(
        'preiskuranti',
        string='პრეისკურანტი',
    )

    bypass_preiskuranti_filter = fields.Boolean(
        string="სრული პროდუქცია",
        help="If checked, all products will be available regardless of selected პრეისკურანტი."
    )

    @api.depends('x_studio_vehile')
    def _compute_allowed_preiskuranti(self):
        Preiskuranti = self.env['preiskuranti']
        for req in self:
            if req.x_studio_vehile and req.x_studio_vehile.model_id:
                model_id = req.x_studio_vehile.model_id.id
                req.allowed_preiskuranti_ids_new = Preiskuranti.search([
                    ('model_ids', 'in', [model_id])
                ])
            else:
                req.allowed_preiskuranti_ids_new = Preiskuranti.browse([])

    @api.depends('preiskuranti_id_new')
    def _compute_allowed_products(self):
        Product = self.env['product.product']
        for req in self:
            try:
                if req.bypass_preiskuranti_filter:
                    products = Product.search([])
                else:
                    pricelist = req.preiskuranti_id_new
                    if pricelist and pricelist.preiskuranti_line_ids:
                        products = Product.search([
                            ('id', 'in', pricelist.preiskuranti_line_ids.mapped('product_id').ids)
                        ])
                    else:
                        products = Product.search([])
            except Exception:
                products = Product.search([])

            req.allowed_product_ids = products

    @api.depends('preiskuranti_id_new')
    def get_product_price_from_preiskuranti(self, product):
        """Find product price from selected პრეისკურანტი."""
        self.ensure_one()
        pricelist = self.preiskuranti_id_new
        if not (pricelist and hasattr(pricelist, 'preiskuranti_line_ids')):
            return 0.0

        line = pricelist.preiskuranti_line_ids.filtered(
            lambda l: l.product_id.id == product.id
        )
        return line.fasi if line else 0.0
    
    @api.depends('preiskuranti_id_new')
    def get_product_garantia_from_preiskuranti(self, product):
        """Find product price from selected პრეისკურანტი."""
        self.ensure_one()
        pricelist = self.preiskuranti_id_new
        if not (pricelist and hasattr(pricelist, 'preiskuranti_line_ids')):
            return 0.0

        line = pricelist.preiskuranti_line_ids.filtered(
            lambda l: l.product_id.id == product.id
        )
        return line.garantia if line else 0.0

    @api.onchange('line_ids.product_id')
    def _onchange_line_product_fill_price(self):
        """Automatically fill unit price on lines from chosen პრეისკურანტი."""
        for req in self:
            for line in req.line_ids:
                if not line.product_id:
                    continue
                price = req.get_product_price_from_preiskuranti(line.product_id)
                garantiavad = req.get_product_garantia_from_preiskuranti(line.product_id)
                if price and hasattr(line, 'preiskurantifasi'):
                    line.preiskurantifasi = price
                    line.preiskurantidan = True
                if garantiavad and hasattr(line,'garantiavada'):
                    line.garantiavada = garantiavad    

        # ------------------------------------------------------------------
        # DEBUG WARRANTY METHOD — THIS IS THE ONLY MODIFICATION YOU ASKED
        # ------------------------------------------------------------------
    def check_product_warranty(self, product):
        self.ensure_one()

        vehicle = self.x_studio_vehile
        if not vehicle:
            return  # no vehicle = no warranty check

        # find last request with pricelist
        last_request = self.env['inventory.request'].search([
            ('x_studio_vehile', '=', vehicle.id),
            ('id', '!=', self.id),
            #('preiskuranti_id_new', '!=', False),           preiskuranti_line_ids
        ], order='create_date desc', limit=1)

        if not last_request:
            return

        #last_preis = last_request.preiskuranti_id_new
        #if not last_preis:
        #    return

        # product line in previous pricelist
        #last_line = last_preis.preiskuranti_line_ids.filtered(
        #    lambda l: l.product_id.id == product._origin.id
        #)
        #if not last_line:
        #    return
        last_line = last_request.line_ids.filtered(lambda l: l.product_id.id == product._origin.id)

        if len(last_line) > 1:
            last_line = last_line[-1]

        garantia_days = last_line.garantiavada or 0
        if garantia_days <= 0:
            return

        # date calculation
        warranty_start = last_request.request_date
        warranty_end = warranty_start + timedelta(days=garantia_days)
        current_date = self.request_date or fields.Date.context_today(self)

        # if warranty still active → raise meaningful popup
        if current_date <= warranty_end:
            return {
                'warning': {
                    'title': "🚫 პროდუქტი საგარანტიოშია!",
                    'message': (
                        f"პროდუქტი: {product.display_name}\n"
                        f"შესყიდვის თარიღი: {warranty_start}\n"
                        f"გარანტიის ვადა: {garantia_days} დღე\n"
                        f"ვადაგასვლა: {warranty_end}\n\n"
                        f"გთხოვთ გადაამოწმოთ საჭიროებს თუ არა გადახდას."
                    )
                }
            }

    @api.onchange('line_ids.product_id')
    def _onchange_line_product_check_warranty(self):
        for req in self:
            for line in req.line_ids:
                if line.product_id:
                    warning = req.check_product_warranty(line.product_id)
                    if warning:
                        return warning

    def check_agreement_limit(self):
        """
        Checks if (Current Preiskuranti Total + Request Non-Preiskuranti Sum) > 110% of Initial Preiskuranti.
        Only performs the check if there are non-preiskuranti items in the request.
        """
        # 1. Bypass (Admin=2, Utharashvili=17)
        if self.env.user.id in [2, 17]:
            return

        for req in self:
            # 2. Context Validation
            preiskuranti = req.preiskuranti_id_new
            if not preiskuranti:
                continue

            # 3. Check for Non-Preiskuranti Items
            non_preiskuranti_lines = req.line_ids.filtered(lambda l: not l.preiskurantidan)
            if not non_preiskuranti_lines:
                continue

            # 4. Calculate Limit: 110% of Preiskurantis Initial Totals under the same agreement
            agreement = preiskuranti.purchase_agreement_id
            if agreement:
                all_preiskurantis = self.env['preiskuranti'].search([
                    ('purchase_agreement_id', '=', agreement.id)
                ])
                base_initial_total = sum(all_preiskurantis.mapped('initial_total'))
                current_preiskuranti_sum = sum(all_preiskurantis.mapped('total_preiskuranti'))
            else:
                base_initial_total = preiskuranti.initial_total or 0.0
                current_preiskuranti_sum = preiskuranti.total_preiskuranti or 0.0

            limit = base_initial_total * 1.1

            # 5. Calculate Current Status
            # Extra from current request (items NOT from preiskuranti)
            request_extra_sum = sum(non_preiskuranti_lines.mapped('unit_price') or [0.0])

            total_usage = current_preiskuranti_sum + request_extra_sum

            # Check Condition
            if total_usage > limit:
                raise UserError(
                    f"ლიმიტი გადაჭარბებულია!\n"
                    f"პრეისკურანტის მიმდინარე ჯამი: {current_preiskuranti_sum:.2f}\n"
                    f"დამატებითი (არაპრეისკურანტული) თანხა: {request_extra_sum:.2f}\n"
                    f"მთლიანი ჯამი: {total_usage:.2f}\n"
                    f"ლიმიტი (110% პირველადი ჯამიდან): {limit:.2f}\n\n"
                    f"თუ აუცილებელი მოთხოვნაა მიმართეთ ირაკლი უთარაშვილს"
                )


class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    preiskurantifasi = fields.Float(
        string='პრეისკურანტის ფასი'
    )

    preiskurantidan = fields.Boolean(
        string="პრეისკურანტიდან გადმოსული",
        help="If checked, პროდუქცია იყო არჩეულ პრეისკურანტში."
    )

    garantiavada = fields.Integer(string = "საგარანტიო პერიოდი (დღე)")

    @api.onchange('product_id')
    def _onchange_product_id_fill_price_from_preiskuranti(self):
        """Auto-fill unit price from parent's პრეისკურანტი."""
        for line in self:
            if not (line.product_id and line.request_id):
                continue

            price = line.request_id.get_product_price_from_preiskuranti(line.product_id)
            garantiavad = line.request_id.get_product_garantia_from_preiskuranti(line.product_id)
            if price:
                if hasattr(line, 'preiskurantifasi'):
                    line.preiskurantifasi = price
                    line.unit_price = price
                    line.preiskurantidan = True
            if garantiavad:
                if hasattr(line, 'garantiavada'):  
                    line.garantiavada = garantiavad     

    @api.onchange('product_id')
    def _onchange_product_id_check_warranty(self):
        for line in self:
            if line.product_id and line.request_id:
                warning = line.request_id.check_product_warranty(line.product_id)
                if warning:
                    return warning


