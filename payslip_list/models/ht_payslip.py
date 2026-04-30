from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    line_basic = fields.Float(
        string='მიმდინარე ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_ins = fields.Float(
        string='პირადი დაზღვევა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_mob = fields.Float(
        string='მობილურის დაკავება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_trip = fields.Float(
        string='მივლინების დაკავება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_prem = fields.Float(
        string='პრემია',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_iveria = fields.Float(
        string='ივერიის ფონდი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_fitpass = fields.Float(
        string='ფიტპასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_sapcomp = fields.Float(
        string='კომპანიის 2 %',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_sap = fields.Float(
        string='საპენსიო 2 %',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_gross = fields.Float(
        string='დასაბეგრი ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_income = fields.Float(
        string='საშემოსავლო',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )

    line_assig_salary = fields.Float(
        string='ანაზღაურების დანიშვნა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_child_support = fields.Float(
        string='ბავშვის ფინანსური მხარდაჭერა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_deduction = fields.Float(
        string='გამოქვითვა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_fondi = fields.Float(
        string='ფონდი სოლიდარობა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_net = fields.Float(
        string='ხელფასი (NET)',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_agsr = fields.Float(
        string='აღსრულების ეროვნული ბიურო',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_pension_4 = fields.Float(
        string='საპენსიო 4 %',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_compsap = fields.Float(
        string='დაზღვევაზე კომპანიის საპენსიო',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_tansap = fields.Float(
        string='დაზღვევაზე თანამშრომლის საპენსიო',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_compdazg = fields.Float(
        string='კომპანიის დაზღვევა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )

    line_avansi = fields.Float(
        string='ავანსად გაცემული ხელფასი/შვებულება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_premiapr = fields.Float(
        string='პრემია %',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )

    @api.depends('line_ids.total', 'line_ids.salary_rule_id.name')
    def _compute_lines(self):
        code_to_field = {
            'მიმდინარე ხელფასი': 'line_basic',
            'პირადი დაზღვევა': 'line_ins',
            'მობილურის დაკავება': 'line_mob',
            'მივლინების დაკავება': 'line_trip',
            'პრემია': 'line_prem',
            'ივერიის ფონდი': 'line_iveria',
            'ფიტპასი': 'line_fitpass',
            'საპენსიო 2%': 'line_sap',
            'კომპანიის 2%': 'line_sapcomp',
            'დასაბეგრი ხელფასი': 'line_gross',
            'საშემოსავლო': 'line_income',
            'პრემია %': 'line_premiapr',
            'CHILD_SUPPORT': 'line_child_support',
            'DEDUCTION': 'line_deduction',
            'ფონდი სოლიდარობა': 'line_fondi',
            'ხელფასი (NET)': 'line_net',
            'აღსრულების ეროვნული ბიურო': 'line_agsr', #gros moashore da daamate
            'საპენსიო 4%': 'line_pension_4', # დაამატე ფილდი
            'დაზღვევაზე კომპანიის საპენსიო' : 'line_compsap', # დაამატე ფილდი
            'დაზღვევაზე თანამშრომლის საპენსიო':'line_tansap', # დაამატე ფილდი
            'კომპანიის დაზღვევა' : 'line_compdazg',  # დაამატე ფილდი
            'ავანსად გაცემული ხელფასი/შვებულება' : 'line_avansi' , #daamate
        }

        for slip in self:
            code_map = {l.salary_rule_id.name : l.total for l in slip.line_ids}

            for field_name in code_to_field.values():
                setattr(slip, field_name, 0.0)

            for code, field_name in code_to_field.items():
                if code in code_map:
                    setattr(slip, field_name, code_map[code])
