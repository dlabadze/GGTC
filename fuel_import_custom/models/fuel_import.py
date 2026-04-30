from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo
import threading
import base64
import pandas as pd
import io
import logging
from datetime import datetime
import calendar

_logger = logging.getLogger(__name__)


class FuelImportWizard(models.TransientModel):
    _name = 'fuel.import.wizard'
    _description = 'Fuel Filling Log Import Wizard'
    
    file_data = fields.Binary('Excel File', required=True)
    file_name = fields.Char('File Name')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done')
    ], default='draft', string='Status')
    processed_vehicle_ids = fields.Text('Processed Vehicle IDs', default='')
    total_vehicles = fields.Integer('Total Vehicles', default=0)
    processed_count = fields.Integer('Processed Count', default=0)
    
    def action_import_fuel_logs(self):
        """Spawns a background thread to completely bypass HTTP timeouts"""
        try:
            _logger.info("🎯 STARTING BACKGROUND IMPORT")
            self.state = 'processing'
            
            # 1. Parse Excel in the main thread so we catch formatting/upload errors immediately
            data_rows = self._parse_excel_file()
            _logger.info(f"📊 Parsed {len(data_rows)} rows from Excel")
            
            # 2. Spawn a background thread for the heavy database operations
            thread = threading.Thread(
                target=self._run_in_background, 
                args=(self.env.cr.dbname, self.env.user.id, self.id, data_rows)
            )
            thread.start()
            
            # 3. Return immediately to the user before any timeout can trigger
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import Started',
                    'message': 'Your file is being processed in the background. You can close this window.',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            error_msg = f"Import failed to start: {str(e)}"
            _logger.error(error_msg, exc_info=True)
            self.state = 'draft'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import Failed',
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    @api.model
    def _run_in_background(self, dbname, uid, wizard_id, data_rows):
        """Creates a new database cursor and runs the import outside the HTTP request"""
        registry = odoo.registry(dbname)
        
        with registry.cursor() as cr:
            env = api.Environment(cr, uid, {})
            wizard = env['fuel.import.wizard'].browse(wizard_id)
            
            try:
                _logger.info("🚀 Background worker picked up the import task.")
                wizard._import_with_total_calculation(data_rows)
                cr.commit()
                _logger.info("✅ Background import finished and committed successfully.")
                
            except Exception as e:
                cr.rollback()
                wizard.state = 'draft'
                _logger.error(f"❌ Background import completely failed: {e}", exc_info=True)

    def _get_last_day_of_month(self, date_obj):
        """Get the last day of the month for a given date"""
        if not date_obj:
            return date_obj
        
        last_day = calendar.monthrange(date_obj.year, date_obj.month)[1]
        return date_obj.replace(day=last_day)
    
    def _import_with_total_calculation(self, data_rows):
        """Import with proper total calculation and optimized bulk creation"""
        
        if not data_rows:
            _logger.warning("⚠️ No data rows to process")
            self.state = 'done'
            return
        
        _logger.info(f"📊 Processing {len(data_rows)} rows from Excel")
        
        vehicle_totals = {}
        avzidan_totals = {}  # NEW: Tracks tank fuel exactly like card fuel
        vehicle_details = {}
        vehicle_info = {}
        
        _logger.info("🎯 STEP 1: GROUPING DATA BY SPECIFIC VEHICLE (BY PLATE)")
        
        all_vehicles = self.env['fleet.vehicle'].search([])
        vehicles_by_plate = {}
        vehicles_by_nomeri = {}
        
        def normalize_plate(plate):
            return plate.replace(' ', '').replace('-', '').upper() if plate else ''
            
        for v in all_vehicles:
            norm_plate = normalize_plate(v.license_plate)
            if norm_plate:
                if norm_plate not in vehicles_by_plate:
                    vehicles_by_plate[norm_plate] = v
            
            if hasattr(v, 'x_studio_sawvavis_baratis_nomeri') and v.x_studio_sawvavis_baratis_nomeri:
                nomeri = str(v.x_studio_sawvavis_baratis_nomeri)
                if nomeri not in vehicles_by_nomeri:
                    vehicles_by_nomeri[nomeri] = v
        
        for i, row in enumerate(data_rows, 1):
            try:
                desc = str(row[0]).strip() if len(row) > 0 and not pd.isna(row[0]) else "ივნისი"
                date_raw = row[1] if len(row) > 1 else None
                vehicle = str(row[2]).strip() if len(row) > 2 and not pd.isna(row[2]) else ""
                fuel_raw = row[3] if len(row) > 3 else 0
                fuel_type = str(row[4]).strip() if len(row) > 4 and not pd.isna(row[4]) else ""
                remaining_raw = row[5] if len(row) > 5 else None  
                avzidan_chasxmuli = row[6] if len(row) > 6 else 0
                
                fuel_amount = 0.0
                try:
                    if not pd.isna(fuel_raw) and str(fuel_raw).strip():
                        fuel_amount = float(str(fuel_raw).replace(',', '.'))
                except:
                    fuel_amount = 0.0
                
                fuel_date = self._parse_date(date_raw)
                fuel_date_only = fuel_date.date() if fuel_date and hasattr(fuel_date, 'date') else fuel_date

                remaining_value = 0.0
                try:
                    if remaining_raw is not None and not pd.isna(remaining_raw) and str(remaining_raw).strip():
                        remaining_value = float(str(remaining_raw).replace(',', '.'))
                except Exception:
                    remaining_value = 0.0
                
                avzidan_value = 0.0
                try:
                    if avzidan_chasxmuli is not None and not pd.isna(avzidan_chasxmuli) and str(avzidan_chasxmuli).strip():
                        avzidan_value = float(str(avzidan_chasxmuli).replace(',', '.'))
                except Exception:
                    avzidan_value = 0.0
                
                excel_plate = normalize_plate(vehicle)
                vehicle_obj = None
                
                if excel_plate and excel_plate in vehicles_by_plate:
                    vehicle_obj = vehicles_by_plate[excel_plate]
                elif vehicle and vehicle in vehicles_by_nomeri:
                    vehicle_obj = vehicles_by_nomeri[vehicle]
                
                vehicle_model_id = vehicle_obj.model_id.id if vehicle_obj else None
                vehicle_id = vehicle_obj.id if vehicle_obj else None
                vehicle_plate = vehicle_obj.license_plate if vehicle_obj else vehicle
                
                if not vehicle_id:
                    _logger.warning(f"⚠️ Row {i} skipped: No vehicle found for plate '{vehicle}'")
                    continue
                
                # Group by specific vehicle (by vehicle_id)
                if vehicle_id not in vehicle_totals:
                    vehicle_totals[vehicle_id] = 0.0
                    avzidan_totals[vehicle_id] = 0.0  # Initialize tank fuel at 0.0
                    vehicle_details[vehicle_id] = []
                    last_day_of_month = self._get_last_day_of_month(fuel_date_only)
                    
                    vehicle_info[vehicle_id] = {
                        'vehicle_obj': vehicle_obj,
                        'plate': vehicle_plate,
                        'model_id': vehicle_model_id,
                        'fuel_type': fuel_type,
                        'date_start': last_day_of_month,
                        'remaining_value': remaining_value,
                        'x_studio_konkretuli_manqana': vehicle_id,
                    }
                else:
                    # Update remaining value to the latest seen (only if it's > 0)
                    if remaining_value > 0:
                        vehicle_info[vehicle_id]['remaining_value'] = remaining_value
                
                # BOTH fuel types now sit together and add up row by row
                vehicle_totals[vehicle_id] += fuel_amount
                avzidan_totals[vehicle_id] += avzidan_value
                
                vehicle_details[vehicle_id].append({
                    'desc': desc,
                    'date': fuel_date_only, 
                    'fuel_amount': fuel_amount,
                    'vehicle_id': vehicle_id,
                    'vehicle_name': vehicle_plate,
                    'avzidan_chasxmuli': avzidan_value,
                })
                
            except Exception as row_error:
                _logger.error(f"❌ Row {i} failed: {row_error}")
        
        if not vehicle_totals:
            _logger.warning("No valid vehicles found. Import halted.")
            self.state = 'done'
            return
        
        # 🚀 STEP 2: OPTIMIZED BULK BATCH PROCESSING
        all_vehicle_ids = list(vehicle_totals.keys())
        self.total_vehicles = len(all_vehicle_ids)
        
        batch_size = 50 
        journal_success = 0
        detail_success = 0
        
        optimized_context = {
            'tracking_disable': True,
            'mail_create_nolog': True,
            'mail_notrack': True,
            'mail_create_nosubscribe': True,
        }
        
        journal_model = self.env['x_fuel_filling_log'].with_context(**optimized_context)
        detail_model = self.env['x_fuel_filling_log_det'].with_context(**optimized_context)

        for batch_index in range(0, self.total_vehicles, batch_size):
            batch_vehicle_ids = all_vehicle_ids[batch_index:batch_index + batch_size]
            _logger.info(f"🎯 PROCESSING BATCH {batch_index//batch_size + 1}")
            
            journal_values_list = []
            
            for vehicle_id in batch_vehicle_ids:
                total_fuel = vehicle_totals[vehicle_id]
                avzidan_val = avzidan_totals[vehicle_id]  # Pull from our new totals dict
                v_info = vehicle_info.get(vehicle_id, {})
                
                chasxmebis_total = avzidan_val + total_fuel

                journal_values = {
                    'x_name': f"Fuel Import - {v_info.get('plate', 'Unknown')}",
                    'x_studio_modeli_manqanis': v_info.get('model_id'),
                    'x_studio_baratidan_chasxmuli': total_fuel,
                    'x_studio_tipi_sawvavis': v_info.get('fuel_type', ''),
                    'x_studio_date_2': v_info.get('date_start'),
                    'x_studio_avzebshi_darchenili': v_info.get('remaining_value', 0.0),
                    'x_studio_avzidan_chasxmuli': avzidan_val,  # Using the clean total here
                    'x_studio_chasxmebis_raodenoba': chasxmebis_total,
                    'x_studio_konkretuli_manqana': vehicle_id,
                }
                journal_values_list.append(journal_values)
                
            try:
                created_journals = journal_model.create(journal_values_list)
                journal_success += len(created_journals)
                
                all_detail_values_list = []
                
                for vehicle_id, journal_record in zip(batch_vehicle_ids, created_journals):
                    for detail_info in vehicle_details[vehicle_id]:
                        chasxmebis_raodenoba_det = detail_info['fuel_amount'] + detail_info['avzidan_chasxmuli']

                        detail_values = {
                            'x_name': detail_info['desc'],
                            'x_studio_date_chasxma': detail_info['date'],
                            'x_studio_chasxmebis_raodenoba_det': chasxmebis_raodenoba_det,
                            'x_studio_modeli_manqanisss': vehicle_info[vehicle_id].get('model_id'),
                            'x_studio_fleetcar': vehicle_id,
                            'x_studio_fuelid': journal_record.id, 
                        }
                        all_detail_values_list.append(detail_values)
                
                if all_detail_values_list:
                    created_details = detail_model.create(all_detail_values_list)
                    detail_success += len(created_details)
                    _logger.info(f"✅ Batch created {len(created_journals)} journals and {len(created_details)} detail lines.")
                    
            except Exception as batch_error:
                _logger.error(f"❌ Batch creation failed: {batch_error}")
            
            try:
                if hasattr(self.env, 'flush_all'):
                    self.env.flush_all()
                else:
                    self.env.cr.flush()
            except Exception as e:
                _logger.error(f"❌ Could not flush batch: {e}")

        # Finish
        self.state = 'done'
        _logger.info(f"🎉 FINAL RESULT: {self.total_vehicles} vehicles processed. Created {journal_success} journals and {detail_success} details.")
    
    def _parse_excel_file(self):
        """Parse Excel file"""
        if not self.file_data:
            raise UserError("No file uploaded")
        
        file_content = base64.b64decode(self.file_data)
        
        df = None
        
        if self.file_name.lower().endswith('.xlsx'):
            try:
                df = pd.read_excel(io.BytesIO(file_content), header=None, engine='openpyxl')
            except Exception as e:
                _logger.warning(f"openpyxl failed: {e}")
        
        if df is None and self.file_name.lower().endswith('.xls'):
            try:
                df = pd.read_excel(io.BytesIO(file_content), header=None, engine='xlrd')
            except Exception as e:
                _logger.warning(f"xlrd failed: {e}")
        
        if df is None:
            try:
                df = pd.read_excel(io.BytesIO(file_content), header=None)
            except Exception as e:
                raise UserError(f"Could not read file: {e}")
        
        clean_rows = []
        for idx, row in df.iterrows():
            row_list = row.tolist()
            if any(str(cell).strip() and str(cell) != 'nan' for cell in row_list):
                clean_rows.append(row_list)
        
        if clean_rows and any(str(cell) in ['ლიტრი', 'თარიღი', 'აღწერა'] for cell in clean_rows[0]):
            clean_rows = clean_rows[1:]
        
        return clean_rows
    
    def _parse_date(self, date_raw):
        """Parse date from Excel"""
        if not date_raw or pd.isna(date_raw):
            return fields.Datetime.now()
        
        if isinstance(date_raw, (pd.Timestamp, datetime)):
            return date_raw
        
        date_str = str(date_raw).strip()
        
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y', '%d/%m/%Y',
            '%m-%d-%Y', '%d-%m-%Y', '%d.%m.%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return fields.Datetime.now()


class FuelImportHelper(models.TransientModel):
    _name = 'fuel.import.helper'
    _description = 'Fuel Import Helper'
    
    @api.model
    def open_fuel_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Fuel Data'),
            'res_model': 'fuel.import.wizard',
            'view_mode': 'form',
            'target': 'new'
        }