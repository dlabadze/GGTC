from re import T
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    is_duplicate_check_lines_invisible = fields.Boolean(
        string='Is Duplicate Check Lines Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_checked_invisible = fields.Boolean(
        string='Is Checked Invisible',
        default=False,
        compute='_compute_all_invisible_fields',
    )
    is_dasaxeleba_invisible = fields.Boolean(
        string='Is Dasaxeleba Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_line_code_invisible = fields.Boolean(
        string='Is Line Code Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_line_descr_invisible = fields.Boolean(
        string='Is Line Description Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_uom_id_invisible = fields.Boolean(
        string='Is UOM ID Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_quantity_invisible = fields.Boolean(
        string='Is Quantity Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_request_date_invisible = fields.Boolean(
        string='Is Request Date Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_budget_analytic_invisible = fields.Boolean(
        string='Is Budget Analytic Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_budget_analytic_line_account_invisible = fields.Boolean(
        string='Is Budget Analytic Line Account Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_budget_analytic_line_invisible = fields.Boolean(
        string='Is Budget Analytic Line Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_preiskurantidan_invisible = fields.Boolean(
        string='Is Preiskurantidan Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_preiskurantifasi_invisible = fields.Boolean(
        string='Is Preiskurantifasi Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_unit_price_invisible = fields.Boolean(
        string='Is Unit Price Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_amount_invisible = fields.Boolean(
        string='Is Amount Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_on_hand_invisible = fields.Boolean(
        string='Is On Hand Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_warehouse_invisible = fields.Boolean(
        string='Is Warehouse Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_purchase_invisible = fields.Boolean(
        string='Is Purchase Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_gatvaliswinebuli_invisible = fields.Boolean(
        string='Is Gatvaliswinebuli Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_dasamzadebeli_invisible = fields.Boolean(
        string='Is Dasamzadebeli Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_purchase_plan_invisible = fields.Boolean(
        string='Is Purchase Plan Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_purchase_plan_line_invisible = fields.Boolean(
        string='Is Purchase Plan Line Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_on_hand_button_invisible = fields.Boolean(
        string='Is On Hand Button Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_garantiavada_invisible = fields.Boolean(
        string='Is Garantiavada Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_ganawileba_invisible = fields.Boolean(
        string='Is Ganawileba Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_ganawileba_user_id_invisible = fields.Boolean(
        string='Is Ganawileba User ID Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_kategoria_invisible = fields.Boolean(
        string='Is Kategoria Invisible',
        compute='_compute_all_invisible_fields',
    )
   
    is_dep_head_invisible = fields.Boolean(
        string='Is Dep Head Invisible',
        compute='_compute_all_invisible_fields',
    )

    is_shesyidvis_group_invisible = fields.Boolean(
        string='Is Sheshyidvis Group Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_user_in_lines_invisible = fields.Boolean(
        string='Is User in Lines Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_ganawileba_button_invisible = fields.Boolean(
        string='Is Ganawileba Button Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_exceeds_budget_invisible = fields.Boolean(
        string='Is Exceeds Budget Invisible',
        compute='_compute_all_invisible_fields',
    )
    is_tag_ids_invisible = fields.Boolean(
        string='Is Tag IDs Invisible',
        compute='_compute_all_invisible_fields',
    )
    
    def _calculate_invisible_fields(self, request_type, stage_name):
        """
        Helper method to calculate all invisible field values based on request type and stage.
        Returns a dictionary with all invisible field values.
        """
        # Initialize all fields to default values
        is_product_request = request_type == 'პროდუქციის მოთხოვნა'
        is_service_request = request_type == 'სხვა მომსახურება'
        is_trasport_request = request_type == 'მომსახურების მოთხოვნა - ტრასპორტი'
        _logger.info(f"==================calculate_invisible_fields============================")
        result = {}
        _logger.info(f"Stage Name: {stage_name}")
        _logger.info(f"Is Product Request: {is_product_request}")
        _logger.info(f"Is Service Request: {is_service_request}")
        _logger.info(f"Request Type: {request_type}")
        # 1. is_checked_invisible - კოპირება (ველი)
        if is_product_request:
            result['is_checked_invisible'] = stage_name not in [
                'ადგ. საწყობი', 'სასაწყობე მეურ. სამმ.', 'ლოგისტიკის დეპარტამენტი'
            ]
        elif is_service_request:
            result['is_checked_invisible'] = stage_name not in [
                'ადგ. საწყობი', 'სასაწყობე მეურ. სამმ.', 'ლოგისტიკის დეპარტამენტი'
            ]
        else:
            result['is_checked_invisible'] = True
        
        # 2. is_duplicate_check_lines_invisible - მასალის ჩანაწერების კოპირება (ღილაკი)
        if is_product_request:
            result['is_duplicate_check_lines_invisible'] = stage_name not in [
                'ადგ. საწყობი', 'სასაწყობე მეურ. სამმ.', 'ლოგისტიკის დეპარტამენტი'
            ]
        elif is_service_request:
            result['is_duplicate_check_lines_invisible'] = stage_name not in [
                'ადგ. საწყობი', 'სასაწყობე მეურ. სამმ.', 'ლოგისტიკის დეპარტამენტი'
            ]
        else:
            result['is_duplicate_check_lines_invisible'] = False
        
        # 3. is_dasaxeleba_invisible - დასახელება (ველი)
        result['is_dasaxeleba_invisible'] = True
        
        # 4. is_line_code_invisible - კოდი (ველი)
        if is_product_request:
            result['is_line_code_invisible'] = True
        elif is_service_request:
            result['is_line_code_invisible'] = True
        else:
            result['is_line_code_invisible'] = True

        
        # 5. is_line_descr_invisible - აღწერა (ველი)
        result['is_line_descr_invisible'] = is_product_request or is_service_request
        
        # 6. is_uom_id_invisible - ერთ. (ველი)
        result['is_uom_id_invisible'] = False
        
        # 7. is_quantity_invisible - რაოდენობა (ველი)
        result['is_quantity_invisible'] = False
        
        # 8. is_request_date_invisible - მოთხ. თარიღი (ველი)
        result['is_request_date_invisible'] = True
       
        # 9. is_budget_analytic_invisible - ბიუჯეტი (ველი)
        if is_product_request:
            result['is_budget_analytic_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი","შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "ფინანსური სამმართველო", "ფინანსური დეპარტამენტი", "CPV კოდები"
            ]
        elif is_service_request:
            result['is_budget_analytic_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი","შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "ფინანსური სამმართველო", "ფინანსური დეპარტამენტი", "CPV კოდები"
            ]
        else:
            result['is_budget_analytic_invisible'] = True
        
        # 10. is_budget_analytic_line_account_invisible - ბიუჯეტის კოდი (ველი)
        if is_product_request:
            result['is_budget_analytic_line_account_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ."
            ]
        elif is_service_request:
            result['is_budget_analytic_line_account_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ.",
            ]
        else:
            result['is_budget_analytic_line_account_invisible'] = True
        
        # 11. is_budget_analytic_line_invisible - ბიუჯეტის მუხლი (ველი)
        if is_product_request:
            result['is_budget_analytic_line_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ."
            ]
        elif is_service_request:
            result['is_budget_analytic_line_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ.",
            ]
        else:
            result['is_budget_analytic_line_invisible'] = True
        
        # 12. is_preiskurantidan_invisible - შეთანხმებული (ველი)
        result['is_preiskurantidan_invisible'] = is_product_request or is_service_request
        
        # 13. is_preiskurantifasi_invisible - პრეისკურანტის ფასი (ველი)
        result['is_preiskurantifasi_invisible'] = is_product_request
        
        # 14. is_unit_price_invisible - ერთ. ფასი (ველი)
        if is_product_request:
            result['is_unit_price_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ."
            ]
        elif is_service_request:
            result['is_unit_price_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ.",
                "ლოგისტიკის დეპარტამენტი",
            ]
        else:
            result['is_unit_price_invisible'] = False
        
        # 15. is_amount_invisible - თანხა (ველი)
        if is_product_request:
            result['is_amount_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ.",
            ]
        elif is_service_request:
            result['is_amount_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი", "სასაწყობე მეურ. სამმ.",
            ]
        else:
            result['is_amount_invisible'] = False


        # 16. is_on_hand_invisible - საერთო ნაშთი (ველი)
        if is_product_request:
            result['is_on_hand_invisible'] = stage_name not in[
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი", 
                "ლოგისტიკის დირექტორი",
            ]
        elif is_service_request:
            result['is_on_hand_invisible'] = stage_name not in [
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი",
                "ლოგისტიკის დირექტორი",
            ]
        else:
            result['is_on_hand_invisible'] = True
        
        # 17. is_warehouse_invisible - გასაცემი საწყობი (ველი)
        if is_product_request:
            result['is_warehouse_invisible'] = stage_name  in [
               "ინიციატორი", "ზემდგომი", "ფილიალის უფროსი", "დეპ. ხელმძღვანელი",
               "ხელმძღვანელი",
            ]
        elif is_service_request:
            result['is_warehouse_invisible'] = stage_name in [
                "ინიციატორი", "ზემდგომი", "ფილიალის უფროსი", "დეპ. ხელმძღვანელი",
                "ხელმძღვანელი",
            ]
        else:
            result['is_warehouse_invisible'] = True
        
        # 18. is_purchase_invisible - შესასყიდი (ველი)
        if is_product_request:
            result['is_purchase_invisible'] = stage_name in [
                "ინიციატორი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი"
            ]
        elif is_service_request:
            result['is_purchase_invisible'] = stage_name in [
                "ინიციატორი", "ზემდგომი", "ფილიალის უფროსი", "დეპ. ხელმძღვანელი",
                "ხელმძღვანელი",
            ]
        else:
            result['is_purchase_invisible'] = True
        
        # 19. is_gatvaliswinebuli_invisible - გათვალისწინებული (ველი)
        if is_product_request:
            result['is_gatvaliswinebuli_invisible'] = stage_name in [
                "ინიციატორი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი"
            ]
        elif is_service_request:
            result['is_gatvaliswinebuli_invisible'] = stage_name not in [
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დირექტორი",
            ]
        else:
            result['is_gatvaliswinebuli_invisible'] = True
        
        # 20. is_dasamzadebeli_invisible - დასამზადებელი (ველი)
        if is_product_request:
            result['is_dasamzadebeli_invisible'] = stage_name in [
                "ინიციატორი", "ზემდგომი", "ფილიალის უფროსი",
                "დეპ. ხელმძღვანელი", "ხელმძღვანელი"
            ]
        elif is_service_request:
            result['is_dasamzadebeli_invisible'] = stage_name not in [
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დირექტორი",
            ]
        else:
            result['is_dasamzadebeli_invisible'] = True
        
        # 21. is_purchase_plan_invisible - შესყ-ის გეგმა (ველი)
        if is_product_request:
            result['is_purchase_plan_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი",
                "ფილიალის უფროსი", "დეპ. ხელმძღვანელი", "ხელმძღვანელი",
                "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი", 
                "ლოგისტიკის დირექტორი",
            ]
        elif is_service_request:
            result['is_purchase_plan_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი",
                "ფილიალის უფროსი", "დეპ. ხელმძღვანელი", "ხელმძღვანელი",
                "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი", 
                "ლოგისტიკის დირექტორი",
            ]
        else:
            result['is_purchase_plan_invisible'] = True
        
        # 22. is_purchase_plan_line_invisible - CPV კოდი (ველი)
        if is_product_request:
            result['is_purchase_plan_line_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი",
                "ფილიალის უფროსი", "დეპ. ხელმძღვანელი", "ხელმძღვანელი",
                "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი", 
                "ლოგისტიკის დირექტორი",
            ]
        elif is_service_request:
            result['is_purchase_plan_line_invisible'] = stage_name in [
                "ინიციატორი", "ადგ. საწყობი", "ზემდგომი",
                "ფილიალის უფროსი", "დეპ. ხელმძღვანელი", "ხელმძღვანელი",
                "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი", 
                "ლოგისტიკის დირექტორი",
            ]
        else:
            result['is_purchase_plan_line_invisible'] = True
        
        # 23. is_on_hand_button_invisible - on hand (ღილაკი)
        if is_product_request:
            result['is_on_hand_button_invisible'] = stage_name not in [
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.",
                "ლოგისტიკის დეპარტამენტი", "ლოგისტიკის დირექტორი"
            ]
        elif is_service_request:
            result['is_on_hand_button_invisible'] = stage_name not in [
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", "ლოგისტიკის დეპარტამენტი",
                "ლოგისტიკის დირექტორი",
            ]
        else:
            result['is_on_hand_button_invisible'] = True
        
        # 24. is_garantiavada_invisible - გარნატია (ველი)
        if is_product_request:
            result['is_garantiavada_invisible'] = True
        elif is_service_request:
            result['is_garantiavada_invisible'] = True
        else:
            result['is_garantiavada_invisible'] = False

        # 25. is_ganawileba_invisible - განფასება (ველი)
        if is_product_request:
            result['is_ganawileba_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "ფინანსური სამმართველო", "ფინანსური დეპარტამენტი", "CPV კოდები",
            ]
        elif is_service_request:
            result['is_ganawileba_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "ფინანსური სამმართველო", "ფინანსური დეპარტამენტი", "CPV კოდები",
            ]
        else:
            result['is_ganawileba_invisible'] = True

        # 26. is_kategoria_invisible - კატეგორია (ველი)
        if is_product_request:
            result['is_kategoria_invisible'] = True
        elif is_service_request:
            result['is_kategoria_invisible'] = True
        else:
            result['is_kategoria_invisible'] = True

        # 27. is_ganawileba_user_id_invisible - განფასება (ველი)
        if is_product_request:
            result['is_ganawileba_user_id_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "ფინანსური სამმართველო", "ფინანსური დეპარტამენტი", "CPV კოდები",
                "გენერალური დირექტორი", "ფინანსური დირექტორი",
            ]
        elif is_service_request:
            result['is_ganawileba_user_id_invisible'] = stage_name in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "ფინანსური სამმართველო", "ფინანსური დეპარტამენტი", "CPV კოდები",
                "გენერალური დირექტორი", "ფინანსური დირექტორი",
            ]
        else:
            result['is_ganawileba_user_id_invisible'] = True

        # 28. is_dep_head_invisible - დეპ. ხელმძღვანელი (ველი)
        if is_product_request:
            result['is_dep_head_invisible'] = False
        elif is_service_request:
            result['is_dep_head_invisible'] = stage_name in ["ინიციატორი", "ადგ. საწყობი"]
        else:
            result['is_dep_head_invisible'] = False
        
        # 29. is_shesyidvis_group_invisible - შესყიდვის ჯგუფი (ველი)
        if is_product_request:
            result['is_shesyidvis_group_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "CPV კოდები",
            ]
        elif is_service_request:
            result['is_shesyidvis_group_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "CPV კოდები",
            ]
        else:
            result['is_shesyidvis_group_invisible'] = True
        
        # 30. is_user_in_lines_invisible - იუზერები განფასებაში (ველი)
        if is_product_request:
            result['is_user_in_lines_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "CPV კოდები",
            ]
        elif is_service_request:
            result['is_user_in_lines_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "CPV კოდები",
            ]
        else:
            result['is_user_in_lines_invisible'] = True
        
        # 31. is_ganawileba_button_invisible - განფასება (ღილაკი)
        if is_product_request:
            result['is_ganawileba_button_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "CPV კოდები",
            ]
        elif is_service_request:
            result['is_ganawileba_button_invisible'] = stage_name not in [
                "შესყ. დეპ. უფროსი", "შესყ.დეპ. ჯგუფი", "ბაზრის კვლევა და განფასება", 
                "CPV კოდები",
            ]
        else:
            result['is_ganawileba_button_invisible'] = False
        
        # 32. is_exceeds_budget_invisible - exceeds budget (ველი)
        if is_product_request:
            result['is_exceeds_budget_invisible'] = stage_name in [
               "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.", 
            ]
        elif is_service_request:
            result['is_exceeds_budget_invisible'] = stage_name in [
                "ადგ. საწყობი", "სასაწყობე მეურ. სამმ.",
            ]
        else:
            result['is_exceeds_budget_invisible'] = True

        # 33. is_tag_ids_invisible - tags (ველი)
        if is_product_request:
            result['is_tag_ids_invisible'] = stage_name in [
               "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი", "დეპ. ხელმძღვანელი",
               "ხელმძღვანელი",
            ]
        elif is_service_request:
            result['is_tag_ids_invisible'] = stage_name in [
               "ინიციატორი", "ადგ. საწყობი", "ზემდგომი", "ფილიალის უფროსი", "დეპ. ხელმძღვანელი",
               "ხელმძღვანელი",
            ]
        else:
            result['is_tag_ids_invisible'] = False
        
        return result
        
    
    @api.model
    def default_get(self, fields_list):
        """
        Set default values for invisible fields when creating new records.
        Uses the same logic as the compute method.
        """
        res = super().default_get(fields_list)
        
        # Set default request type if not already set
        if 'x_studio_type' in fields_list and not res.get('x_studio_type'):
            res['x_studio_type'] = 'ინვენტარი'
        
        # Set default stage if not already set
        if 'stage_id' in fields_list and not res.get('stage_id'):
            # Get the stage_id field definition to find the correct model
            stage_field = self._fields.get('stage_id')
            if stage_field and hasattr(stage_field, 'comodel_name'):
                stage_model = stage_field.comodel_name
                # Search for the "ინიციატორი" stage
                default_stage = self.env[stage_model].search([('name', '=', 'ინიციატორი')], limit=1)
                if default_stage:
                    res['stage_id'] = default_stage.id
        
        # Get values for request_type and stage
        request_type = res.get('x_studio_type', False)
        stage_id = res.get('stage_id', False)
        
        # Get stage name if stage_id is set
        stage_name = False
        if stage_id:
            # Get the stage_id field definition to find the correct model
            stage_field = self._fields.get('stage_id')
            if stage_field and hasattr(stage_field, 'comodel_name'):
                stage_model = stage_field.comodel_name
                stage = self.env[stage_model].browse(stage_id)
                stage_name = stage.name if stage else False
        
        # Calculate invisible fields using the same logic as compute
        invisible_fields = self._calculate_invisible_fields(request_type, stage_name)
        
        # Only add fields that are requested
        for field, value in invisible_fields.items():
            if field in fields_list:
                res[field] = value
        
        return res
    
    @api.depends('x_studio_type', 'stage_id', 'stage_id.name')
    def _compute_all_invisible_fields(self):
        """
        Consolidated compute method for all invisible fields.
        Calculates all visibility fields in a single pass for better performance.
        Uses the helper method to avoid code duplication.
        """
        for rec in self:
            # Get common values once
            request_type = rec.x_studio_type or False
            stage_name = rec.stage_id.name if rec.stage_id else False
            
            # Calculate all invisible fields using the helper method
            invisible_fields = rec._calculate_invisible_fields(request_type, stage_name)
            
            # Set all fields on the record
            for field, value in invisible_fields.items():
                setattr(rec, field, value)
