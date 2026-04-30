# -*- coding: utf-8 -*-
from datetime import datetime, date
import base64
import binascii
from PIL import Image
import io
import logging

_logger = logging.getLogger(__name__)

# Georgian month names
GEORGIAN_MONTHS = {
    1: 'იანვარი',
    2: 'თებერვალი',
    3: 'მარტი',
    4: 'აპრილი',
    5: 'მაისი',
    6: 'ივნისი',
    7: 'ივლისი',
    8: 'აგვისტო',
    9: 'სექტემბერი',
    10: 'ოქტომბერი',
    11: 'ნოემბერი',
    12: 'დეკემბერი',
}


def field1(value):
    """
    Convert False values to empty string
    Returns the value as-is if it's not False
    """
    if value is False:
        return ''
    return value


def date1(date_value):
    """
    Format date as dd/mm/yyyy
    Args:
        date_value: datetime, date object, or string
    Returns:
        Formatted date string as dd/mm/yyyy or empty string if value is False/None
    """
    if not date_value or date_value is False:
        return ''
    
    try:
        # If it's already a datetime object
        if isinstance(date_value, datetime):
            return date_value.strftime('%d/%m/%Y')
        
        # If it's a date object
        if isinstance(date_value, date):
            return date_value.strftime('%d/%m/%Y')
        
        # If it's a string, try to parse it
        if isinstance(date_value, str):
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    return parsed_date.strftime('%d/%m/%Y')
                except ValueError:
                    continue
            
            # If parsing failed, return the original value
            return date_value
        
    except Exception:
        pass
    
    return ''


def date2(date_value, format_type='full'):
    """
    Format date with Georgian month names
    Args:
        date_value: datetime, date object, or string
        format_type: 'full' (16 იანვარი 2025), 'short' (16 იანვარი), 'month_year' (იანვარი 2025)
    Returns:
        Formatted date string with Georgian month name or empty string if value is False/None
    """
    if not date_value or date_value is False:
        return ''
    
    try:
        # Convert to datetime object if needed
        parsed_date = None
        
        # If it's already a datetime object
        if isinstance(date_value, datetime):
            parsed_date = date_value
        
        # If it's a date object
        elif isinstance(date_value, date):
            parsed_date = datetime.combine(date_value, datetime.min.time())
        
        # If it's a string, try to parse it
        elif isinstance(date_value, str):
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(date_value, fmt)
                    break
                except ValueError:
                    continue
        
        if not parsed_date:
            return ''
        
        # Get day, month, year
        day = parsed_date.day
        month = parsed_date.month
        year = parsed_date.year
        
        # Get Georgian month name
        month_name = GEORGIAN_MONTHS.get(month, '')
        
        # Format based on type
        if format_type == 'short':
            return f'{day} {month_name}'
        elif format_type == 'month_year':
            return f'{month_name} {year}'
        else:  # full
            return f'{day} {month_name} {year}'
        
    except Exception:
        pass
    
    return ''


def format_value(value):
    """
    Universal value formatter:
    - Returns empty string for False
    - Formats dates as dd/mm/yyyy
    - Returns other values as-is
    """
    if value is False:
        return ''
    
    if isinstance(value, (datetime, date)):
        return date1(value)
    
    return value


def get_record(recordset, index=0):
    """
    Get a specific record from a recordset by index
    Args:
        recordset: Odoo recordset (One2many, Many2many, or any recordset)
        index: Index of the record to retrieve (0-based, default: 0)
    Returns:
        Single record at the specified index or empty recordset if index is out of range
    
    Usage in template:
        {{get_record(docs.employee_line_ids, 0).employee_id.name}}
        {{get_record(docs.employee_line_ids, 1).employee_id.name}}
    """
    if not recordset:
        return recordset.browse()  # Return empty recordset of the same model
    
    try:
        if 0 <= index < len(recordset):
            return recordset[index]
        return recordset.browse()  # Return empty recordset if index out of range
    except Exception:
        return recordset.browse()


def get_first(recordset):
    """
    Get the first record from a recordset
    Args:
        recordset: Odoo recordset
    Returns:
        First record or empty recordset if empty
    
    Usage in template:
        {{get_first(docs.employee_line_ids).employee_id.name}}
    """
    return get_record(recordset, 0)


def get_last(recordset):
    """
    Get the last record from a recordset
    Args:
        recordset: Odoo recordset
    Returns:
        Last record or empty recordset if empty
    
    Usage in template:
        {{get_last(docs.employee_line_ids).employee_id.name}}
    """
    if not recordset:
        return recordset.browse()
    return get_record(recordset, len(recordset) - 1)


def join_field(recordset, field_name, separator=', '):
    """
    Join values from a specific field across all records in a recordset
    Args:
        recordset: Odoo recordset
        field_name: Name of the field to extract values from
        separator: String to join values with (default: ', ')
    Returns:
        Joined string of all field values
    
    Usage in template:
        {{join_field(docs.employee_line_ids, 'employee_id.name')}}
        {{join_field(docs.employee_line_ids, 'employee_id.name', ' | ')}}
    """
    if not recordset:
        return ''
    
    try:
        values = []
        for record in recordset:
            # Handle nested field access (e.g., 'employee_id.name')
            value = record
            for field_part in field_name.split('.'):
                if value:
                    value = getattr(value, field_part, None)
                else:
                    break
            
            # Add the value if it's not False or None
            if value not in (False, None):
                values.append(str(value))
        
        return separator.join(values)
    except Exception as e:
        _logger.error(f"Error in join_field: {e}")
        return ''


def count_records(recordset):
    """
    Count the number of records in a recordset
    Args:
        recordset: Odoo recordset
    Returns:
        Integer count of records
    
    Usage in template:
        {{count_records(docs.employee_line_ids)}}
    """
    if not recordset:
        return 0
    return len(recordset)
