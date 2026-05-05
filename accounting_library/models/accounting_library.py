import logging

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RS_VAT_ENDPOINT = "http://services.rs.ge/waybillservice/waybillservice.asmx"


class AccountMove(models.Model):
    _inherit = "account.move"

    accounting_library_id = fields.Many2one(
        "accounting.library", string="რეესტრის ჩანაწერი", readonly=True, copy=False,
    )

    def unlink(self):
        libraries = self.env["accounting.library"].search([("vendor_bill_id", "in", self.ids)])
        res = super().unlink()
        if libraries:
            libraries.write({
                "vendor_bill_id": False,
                "is_vat_payer": False,
                "invoice_received": False,
            })
        return res


class AccountingLibrary(models.Model):
    _name = "accounting.library"
    _description = "Accounting Library"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "document_number"

    inspektireba_id = fields.Many2one(
        "inspektireba", string="ინსპექტირება", tracking=True,
    )
    approval_id = fields.Many2one(
        "approval.request", string="მოთხოვნა", tracking=True,
    )
    moxsenebiti_id = fields.Many2one(
        "moxsenebiti", string="მოხსენებითი", tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="კონტრაგენტი", tracking=True,
    )
    vendor_bill_id = fields.Many2one(
        "account.move", string="ფაქტურა",
        domain="[('move_type', '=', 'in_invoice')]",
        readonly=True, copy=False, tracking=True,
    )
    is_vat_payer = fields.Boolean(
        string="დღგ-ს გადამხდელი", readonly=True, copy=False, tracking=True,
        help="ავტომატურად ისმება rs.ge SOAP სერვისიდან კონტრაგენტის TIN-ის მიხედვით.",
    )
    invoice_received = fields.Boolean(
        string="ფაქტურა მიღებულია", copy=False, tracking=True,
    )
    comment = fields.Text(string="საფუძველი", tracking=True)
    document_number = fields.Char(
        string="დოკუმენტის ნომერი",
        compute="_compute_document_number",
        store=True,
        tracking=True,
    )
    date = fields.Date(
        string="თარიღი",
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("incoming", "შემოსული"),
            ("awaiting_invoice", "ფაქტურის მოლოდინში"),
            ("done", "დასრულებული"),
        ],
        string="სტატუსი",
        compute="_compute_state",
        store=True,
        tracking=True,
    )

    @api.depends("vendor_bill_id", "is_vat_payer", "invoice_received")
    def _compute_state(self):
        for rec in self:
            if not rec.vendor_bill_id:
                rec.state = "incoming"
            elif not rec.is_vat_payer:
                rec.state = "done"
            elif rec.invoice_received:
                rec.state = "done"
            else:
                rec.state = "awaiting_invoice"

    @api.depends(
        "inspektireba_id",
        "inspektireba_id.number",
        "approval_id",
        "approval_id.name",
        "moxsenebiti_id",
        "moxsenebiti_id.number",
    )
    def _compute_document_number(self):
        for rec in self:
            if rec.inspektireba_id:
                rec.document_number = rec.inspektireba_id.number
            elif rec.moxsenebiti_id:
                rec.document_number = rec.moxsenebiti_id.number
            elif rec.approval_id:
                rec.document_number = rec.approval_id.name
            else:
                rec.document_number = False

    def _get_rs_credentials(self):
        """Read rs.ge credentials (rs_acc / rs_pass) from the current user."""
        user = self.env.user
        su = getattr(user, "rs_acc", False)
        sp = getattr(user, "rs_pass", False)
        if not su or not sp:
            raise UserError(_(
                "თქვენი მომხმარებლისთვის rs.ge ავტორიზაცია არ არის კონფიგურირებული "
                "(rs_acc / rs_pass ცარიელია). გთხოვთ მიმართოთ ადმინისტრატორს."
            ))
        return su, sp

    def _check_vat_payer(self, tin):
        """Call rs.ge is_vat_payer_tin SOAP 1.2 endpoint. Returns True/False or raises UserError."""
        rs_acc, rs_pass = self._get_rs_credentials()
        soap_request = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
            ' xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            '<is_vat_payer_tin xmlns="http://tempuri.org/">'
            f'<su>{rs_acc}</su><sp>{rs_pass}</sp><tin>{tin}</tin>'
            '</is_vat_payer_tin>'
            '</soap12:Body>'
            '</soap12:Envelope>'
        )

        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
        }
        try:
            response = requests.post(RS_VAT_ENDPOINT, data=soap_request, headers=headers, timeout=30)
        except requests.RequestException as e:
            _logger.exception("rs.ge is_vat_payer_tin request failed")
            raise UserError(_("rs.ge სერვისთან კავშირი ვერ შედგა: %s") % e)

        if response.status_code != 200:
            _logger.error("rs.ge returned %s: %s", response.status_code, response.text)
            raise UserError(_("rs.ge-მ დააბრუნა შეცდომა: HTTP %s") % response.status_code)

        start_tag = "<is_vat_payer_tinResult>"
        end_tag = "</is_vat_payer_tinResult>"
        start_index = response.text.find(start_tag)
        end_index = response.text.find(end_tag)
        if start_index == -1 or end_index == -1:
            _logger.error("Unexpected rs.ge response: %s", response.text)
            raise UserError(_("rs.ge-ს მოულოდნელი პასუხი მოვიდა. დაუკავშირდით ადმინისტრატორს."))

        result = response.text[start_index + len(start_tag):end_index].strip().lower()
        return result == "true"

    def action_create_vendor_bill(self):
        self.ensure_one()
        if self.vendor_bill_id:
            return self.action_open_vendor_bill()
        if not self.partner_id:
            raise UserError(_("გთხოვთ ჯერ აირჩიოთ კონტრაგენტი."))

        tin = (self.partner_id.vat or "").strip()
        if not tin:
            raise UserError(_("არჩეულ კონტრაგენტს არ აქვს TIN (Tax ID). გთხოვთ შეავსოთ."))

        is_vat = self._check_vat_payer(tin)

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "ref": self.document_number or "",
            "narration": self.comment or "",
            "accounting_library_id": self.id,
        })
        self.write({
            "vendor_bill_id": bill.id,
            "is_vat_payer": is_vat,
            "invoice_received": False,
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("ფაქტურა"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": bill.id,
            "target": "current",
        }

    def action_open_vendor_bill(self):
        self.ensure_one()
        if not self.vendor_bill_id:
            raise UserError(_("ფაქტურა ჯერ არ შექმნილა."))
        return {
            "type": "ir.actions.act_window",
            "name": _("ფაქტურა"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.vendor_bill_id.id,
            "target": "current",
        }

    @api.model
    def action_refresh_from_moxsenebiti(self):
        """Pull eligible documents into the registry:
        - moxsenebiti where for_accounting=True AND state in (signed, order_sent)
        - inspektireba where state='confirmed' AND has at least one attachment
        Skips records that already have a corresponding accounting.library entry."""
        new_records = self.env["accounting.library"]

        # ---- Moxsenebiti ----
        Mox = self.env["moxsenebiti"]
        mox_signed = Mox.search([
            ("for_accounting", "=", True),
            ("state", "in", ("signed", "order_sent")),
        ])
        mox_existing = set(
            self.search([("moxsenebiti_id", "in", mox_signed.ids)])
                .mapped("moxsenebiti_id.id")
        )
        for mox in mox_signed:
            if mox.id in mox_existing:
                continue
            new_records |= self.create({
                "moxsenebiti_id": mox.id,
                "comment": getattr(mox, "x_studio_text", False) or "",
                "date": fields.Date.context_today(self),
            })

        # ---- Inspektireba ----
        Insp = self.env["inspektireba"]
        insp_confirmed = Insp.search([("state", "=", "confirmed")])
        if insp_confirmed:
            attachment_counts = self.env["ir.attachment"].read_group(
                domain=[
                    ("res_model", "=", "inspektireba"),
                    ("res_id", "in", insp_confirmed.ids),
                ],
                fields=["res_id"],
                groupby=["res_id"],
            )
            insp_with_files = {row["res_id"] for row in attachment_counts if row["res_id_count"]}
            insp_eligible = insp_confirmed.filtered(lambda r: r.id in insp_with_files)
            insp_existing = set(
                self.search([("inspektireba_id", "in", insp_eligible.ids)])
                    .mapped("inspektireba_id.id")
            )
            for insp in insp_eligible:
                if insp.id in insp_existing:
                    continue
                new_records |= self.create({
                    "inspektireba_id": insp.id,
                    "comment": getattr(insp, "comment", False) or "",
                    "date": fields.Date.context_today(self),
                })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("განახლება"),
                "message": _("დაემატა %d ახალი ჩანაწერი.") % len(new_records),
                "type": "success" if new_records else "info",
                "sticky": False,
            },
        }
