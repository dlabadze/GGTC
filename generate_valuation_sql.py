import pandas as pd
from datetime import datetime
import os

def generate_valuation_sql(env, excel_path, output_sql_path):
    print(f"Reading Excel: {excel_path}")
    df = pd.read_excel(excel_path)
    
    # Clean column names
    df.columns = df.columns.astype(str).str.strip()
    
    date_jan_1 = datetime(2026, 1, 1, 0, 0, 0)
    sql_statements = [
        "-- Stock Valuation Update Script generated on " + str(datetime.now()),
        "BEGIN;",
        ""
    ]
    
    success_count = 0
    error_count = 0
    
    print(f"Processing {len(df)} rows...")
    
    for index, row in df.iterrows():
        try:
            ext_id = str(row.get('id', '')).strip()
            cost = float(row.get('standard_price', 0.0))
            
            if not ext_id or ext_id == 'nan':
                continue
                
            # 1. Resolve External ID to Product
            record = env.ref(ext_id, raise_if_not_found=False)
            if not record:
                # Try finding as product.product if template failed
                record = env.ref(ext_id.replace('product_template', 'product_product'), raise_if_not_found=False)
            
            if not record or record._name not in ['product.product', 'product.template']:
                print(f"[{index}] ID not found: {ext_id}")
                error_count += 1
                continue
            
            if record._name == 'product.template':
                products = record.product_variant_ids
                sql_statements.append(f"-- Product Template: {record.name} ({ext_id})")
                sql_statements.append(f"UPDATE product_template SET standard_price = {cost} WHERE id = {record.id};")
            else:
                products = record
                sql_statements.append(f"-- Product: {record.name} ({ext_id})")
                sql_statements.append(f"UPDATE product_template SET standard_price = {cost} WHERE id = {record.product_tmpl_id.id};")
            
            for product in products:
                # 2. Find Valuation Layers on Jan 1st
                jan_layers = env['stock.valuation.layer'].search([
                    ('product_id', '=', product.id),
                    ('create_date', '>=', date_jan_1.replace(hour=0, minute=0, second=0)),
                    ('create_date', '<=', date_jan_1.replace(hour=23, minute=59, second=59))
                ])
                
                if not jan_layers:
                    # If no layers on Jan 1st, maybe they were created with another date but linked to an inventory adjustment
                    # We'll stick to Jan 1st for now as per requirement
                    pass
                
                for layer in jan_layers:
                    new_value = layer.quantity * cost
                    sql_statements.append(f"  -- Layer {layer.id}: Qty {layer.quantity} -> Cost {cost}, Value {new_value}")
                    sql_statements.append(f"  UPDATE stock_valuation_layer SET unit_cost = {cost}, value = {new_value}, remaining_value = {new_value} WHERE id = {layer.id};")
                    
                    # 3. Handle Journal Entry
                    if layer.account_move_id:
                        move = layer.account_move_id
                        sql_statements.append(f"  -- Move {move.name} (ID: {move.id})")
                        
                        # Find accounts
                        categ = product.categ_id
                        val_account = categ.property_stock_valuation_account_id
                        adj_account = categ.property_stock_inventory_account_id or categ.property_stock_account_input_categ_id
                        
                        if not val_account or not adj_account:
                            sql_statements.append(f"  -- WARNING: Missing accounts for category {categ.name}")
                            continue
                            
                        # Update Move Lines
                        # Positive quantity adjustment: Debit Valuation, Credit Adjustment
                        # Negative: Credit Valuation, Debit Adjustment
                        
                        debit_acc = val_account.id if layer.quantity > 0 else adj_account.id
                        credit_acc = adj_account.id if layer.quantity > 0 else val_account.id
                        abs_value = abs(new_value)
                        
                        sql_statements.append(f"  -- Updating move lines for move {move.id}")
                        # We identify lines by current balance or accounts
                        # More reliable to just update based on sign
                        sql_statements.append(f"  UPDATE account_move_line SET debit = CASE WHEN balance > 0 THEN {abs_value} ELSE 0 END, credit = CASE WHEN balance < 0 THEN {abs_value} ELSE 0 END, account_id = CASE WHEN balance > 0 THEN {debit_acc} ELSE {credit_acc} END WHERE move_id = {move.id};")
                        # Also update the amount_currency if needed, but assuming base currency for now
                        sql_statements.append(f"  UPDATE account_move SET date = '2026-01-01' WHERE id = {move.id};")

            success_count += 1
            if success_count % 100 == 0:
                print(f"Processed {success_count}...")
                
        except Exception as e:
            print(f"Error on row {index}: {e}")
            error_count += 1
            
    sql_statements.append("")
    sql_statements.append("COMMIT;")
    
    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_statements))
        
    print(f"SQL script generated: {output_sql_path}")
    print(f"Success: {success_count}, Errors: {error_count}")

# Execution context for Odoo shell:
# import sys
# sys.path.append('c:/Users/arkik/OneDrive/Documents/GitHub/ggtc/custom_addons/')
# import generate_valuation_sql
# generate_valuation_sql.generate_valuation_sql(env, 'c:/Users/arkik/OneDrive/Documents/GitHub/ggtc/custom_addons/stock_valuation_jan1.xlsx', 'c:/Users/arkik/OneDrive/Documents/GitHub/ggtc/custom_addons/update_valuation.sql')
