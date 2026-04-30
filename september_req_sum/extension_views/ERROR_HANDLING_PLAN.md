# Comprehensive Error Handling Plan for All RS.GE API Calls

## Current Situation

### ✅ **Already Has Error Handling:**
1. `save_waybill` - Checks Status, calls get_error_codes if Status < '0'
2. `save_invoice` - Has some error checking
3. Main upload methods - Have try-except blocks

### ❌ **Missing Error Handling:**
1. `get_name_from_tin` - No error checking
2. `chek_service_user` - No error checking  
3. `get_invoice` - No error checking
4. `get_un_id_from_tin` - No error checking
5. `change_invoice_status` - No error checking
6. `save_invoice_desc` - No error checking
7. Network failures - Inconsistent handling
8. XML parsing errors - Not handled

---

## Proposed Solution: Centralized Error Handler

### **Step 1: Create Helper Methods**

Add these to both `AccountMove` and `StockPicking` classes:

```python
def _get_error_text_from_code(self, rs_acc, rs_pass, error_code):
    """
    Get human-readable error text from RS.GE error code
    
    Args:
        rs_acc: RS account username
        rs_pass: RS account password  
        error_code: Error code (negative number or string)
        
    Returns:
        str: Error message in Georgian
    """
    try:
        soap_request = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <soap:Body>
                <get_error_codes xmlns="http://tempuri.org/">
                    <su>{rs_acc}</su>
                    <sp>{rs_pass}</sp>
                </get_error_codes>
            </soap:Body>
        </soap:Envelope>
        """
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_error_codes"
        }
        
        response = requests.post(
            "http://services.rs.ge/waybillservice/waybillservice.asmx",
            data=soap_request,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            return f"HTTP Error {response.status_code}: {response.text[:200]}"
        
        root = ET.fromstring(response.content)
        error_dict = {}
        
        for error_code_elem in root.findall(".//ERROR_CODE"):
            id_elem = error_code_elem.find("ID")
            text_elem = error_code_elem.find("TEXT")
            if id_elem is not None and text_elem is not None:
                error_dict[id_elem.text] = text_elem.text
        
        # Convert error_code to string for lookup
        error_code_str = str(error_code)
        return error_dict.get(error_code_str, f"უცნობი შეცდომა: კოდი {error_code}")
        
    except Exception as e:
        _logger.exception("Error getting error codes from RS.GE")
        return f"შეცდომის კოდის მიღება ვერ მოხერხდა: {str(e)}"


def _safe_soap_request(self, url, soap_body, headers, service_name="API"):
    """
    Send SOAP request with comprehensive error handling
    
    Args:
        url: SOAP endpoint URL
        soap_body: SOAP XML request body
        headers: HTTP headers
        service_name: Name of service for logging
        
    Returns:
        tuple: (success: bool, response_text: str, error_msg: str)
    """
    try:
        _logger.info(f'=== {service_name} REQUEST ===')
        _logger.info(f'URL: {url}')
        _logger.info(f'Body: {soap_body[:500]}...' if len(soap_body) > 500 else f'Body: {soap_body}')
        
        response = requests.post(
            url, 
            data=soap_body.encode('utf-8'), 
            headers=headers,
            timeout=60  # 60 second timeout
        )
        
        _logger.info(f'{service_name} Response Status: {response.status_code}')
        _logger.info(f'{service_name} Response: {response.text[:500]}...' if len(response.text) > 500 else f'{service_name} Response: {response.text}')
        
        # Check HTTP status
        if response.status_code != 200:
            error_msg = f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
            return False, response.text, error_msg
        
        # Check for SOAP faults
        if 'soap:Fault' in response.text or 'faultstring' in response.text:
            try:
                root = ET.fromstring(response.text)
                fault_string = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body/{http://schemas.xmlsoap.org/soap/envelope/}Fault/faultstring')
                if fault_string is not None:
                    error_msg = f"SOAP შეცდომა: {fault_string.text}"
                    return False, response.text, error_msg
            except:
                pass
            error_msg = "SOAP შეცდომა დაფიქსირდა"
            return False, response.text, error_msg
        
        return True, response.text, None
        
    except requests.exceptions.Timeout:
        error_msg = f"{service_name}: დროის ლიმიტი ამოიწურა (60 წამი)"
        _logger.error(error_msg)
        return False, None, error_msg
        
    except requests.exceptions.ConnectionError:
        error_msg = f"{service_name}: კავშირის შეცდომა - შეამოწმეთ ინტერნეტი"
        _logger.error(error_msg)
        return False, None, error_msg
        
    except Exception as e:
        error_msg = f"{service_name}: {str(e)}"
        _logger.exception(f"Unexpected error in {service_name}")
        return False, None, error_msg


def _parse_xml_response(self, response_text, xpath, namespaces=None):
    """
    Safely parse XML and extract element
    
    Args:
        response_text: XML response string
        xpath: XPath to element
        namespaces: XML namespaces dict
        
    Returns:
        str: Element text or None
    """
    if namespaces is None:
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
    
    try:
        root = ET.fromstring(response_text)
        element = root.find(xpath, namespaces)
        return element.text if element is not None else None
    except Exception as e:
        _logger.error(f"XML parsing error: {str(e)}")
        return None
```

---

## **Step 2: Refactor All API Calls to Use Helper**

### **Example 1: get_name_from_tin** (Before & After)

#### ❌ Before (No error handling):
```python
def get_name_from_tin(self, rs_acc, rs_pass, tin):
    soap_request = f"""..."""
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {...}
    response = requests.post(url, data=soap_request, headers=headers)
    
    start_tag = "<get_name_from_tinResult>"
    end_tag = "</get_name_from_tinResult>"
    start_index = response.text.find(start_tag) + len(start_tag)
    end_index = response.text.find(end_tag)
    name = response.text[start_index:end_index]
    return name
```

#### ✅ After (With full error handling):
```python
def get_name_from_tin(self, rs_acc, rs_pass, tin):
    """Get company name from TIN with error handling"""
    
    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                   xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                   xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
          <tin>{tin}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""
    
    url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/get_name_from_tin"
    }
    
    # Use safe request handler
    success, response_text, error_msg = self._safe_soap_request(
        url, soap_request, headers, "get_name_from_tin"
    )
    
    if not success:
        raise UserError(f"სახელის მიღება ვერ მოხერხდა: {error_msg}")
    
    # Parse response safely
    name = self._parse_xml_response(
        response_text,
        './/ns:get_name_from_tinResult',
        {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
         'ns': 'http://tempuri.org/'}
    )
    
    if not name:
        # Check if it's an error code
        if '<get_name_from_tinResult>' in response_text:
            # Extract result the old way as fallback
            start_tag = "<get_name_from_tinResult>"
            end_tag = "</get_name_from_tinResult>"
            start_index = response_text.find(start_tag) + len(start_tag)
            end_index = response_text.find(end_tag)
            result = response_text[start_index:end_index].strip()
            
            # Check if it's a negative error code
            if result.startswith('-'):
                error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
                raise UserError(f"სახელის მიღება ვერ მოხერხდა: {error_text}")
            
            return result if result else "უცნობი"
        
        raise UserError("სახელის მიღება ვერ მოხერხდა: პასუხი ცარიელია")
    
    _logger.info(f'Name from TIN {tin}: {name}')
    return name
```

---

### **Example 2: chek_service_user**

#### ✅ With Error Handling:
```python
def check_seller_and_service_user_id(self, rs_acc, rs_pass):
    """Check service user with comprehensive error handling"""
    
    _logger.info('Starting check_seller_and_service_user_id')
    
    # First check - RS.GE service
    url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                   xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                   xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <chek_service_user xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
        </chek_service_user>
      </soap:Body>
    </soap:Envelope>"""
    
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    
    success, response_text, error_msg = self._safe_soap_request(
        url, soap_body, headers, "chek_service_user"
    )
    
    if not success:
        raise UserError(f"RS.GE ავტორიზაცია ვერ მოხერხდა: {error_msg}")
    
    # Parse un_id
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns': 'http://tempuri.org/'
    }
    
    seller_un_id = self._parse_xml_response(response_text, './/ns:un_id', namespaces)
    
    if not seller_un_id:
        # Check for error code in response
        error_code = self._parse_xml_response(response_text, './/ns:error', namespaces)
        if error_code:
            error_text = self._get_error_text_from_code(rs_acc, rs_pass, error_code)
            raise UserError(f"RS.GE ავტორიზაცია ვერ მოხერხდა: {error_text}")
        raise UserError("un_id ვერ მოიძებნა პასუხში")
    
    _logger.info(f'Seller UN ID: {seller_un_id}')
    
    # Second check - Revenue service
    # ... similar pattern
    
    return seller_un_id, user_id
```

---

## **Step 3: Update All SOAP Calls**

### API Calls to Update:

#### **RS.GE Waybill Service:**
1. ✅ `get_name_from_tin` - Add error handling
2. ✅ `chek_service_user` - Add error handling
3. ✅ `save_waybill` - Already has (improve)
4. ✅ `get_error_codes` - Already exists (make reusable)

#### **Revenue Service (www.revenue.mof.ge):**
1. ✅ `chek` - Add error handling
2. ✅ `get_un_id_from_tin` - Add error handling
3. ✅ `save_invoice` - Add error handling
4. ✅ `save_invoice_desc` - Add error handling
5. ✅ `change_invoice_status` - Add error handling
6. ✅ `get_invoice` - Add error handling

---

## **Step 4: Standardize Response Handling**

### Pattern for All Responses:

```python
# 1. Send request
success, response_text, error_msg = self._safe_soap_request(url, body, headers, "service_name")

# 2. Check success
if not success:
    raise UserError(f"Operation failed: {error_msg}")

# 3. Parse response
result = self._parse_xml_response(response_text, xpath, namespaces)

# 4. Validate result
if not result:
    raise UserError("Response empty or invalid")

# 5. Check for error codes (if applicable)
if result.startswith('-') or int(result) < 0:
    error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
    raise UserError(error_text)

# 6. Return result
return result
```

---

## **Step 5: Error Code Categories**

### **RS.GE Error Codes** (from get_error_codes):
```python
# Common error codes to handle:
# -1: Invalid credentials
# -2: Invalid TIN
# -3: Invalid waybill data
# -4: Missing required fields
# -5: Duplicate entry
# -100: System error
# etc.
```

### **Revenue Service Error Codes:**
```python
# Different error code system
# Need to map these as well
```

---

## **Step 6: Network & Timeout Handling**

### Add Retry Logic (Optional):
```python
def _safe_soap_request_with_retry(self, url, soap_body, headers, service_name="API", max_retries=3):
    """Send SOAP request with retry logic"""
    
    for attempt in range(max_retries):
        try:
            success, response_text, error_msg = self._safe_soap_request(
                url, soap_body, headers, service_name
            )
            
            if success:
                return True, response_text, None
            
            # Don't retry on authentication errors
            if 'ავტორიზაცია' in error_msg or 'credentials' in error_msg.lower():
                return False, response_text, error_msg
            
            # Retry on network/timeout errors
            if attempt < max_retries - 1:
                _logger.warning(f"{service_name} attempt {attempt + 1} failed, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                continue
            
            return False, response_text, error_msg
            
        except Exception as e:
            if attempt < max_retries - 1:
                _logger.warning(f"{service_name} attempt {attempt + 1} error: {str(e)}, retrying...")
                time.sleep(2 ** attempt)
                continue
            return False, None, str(e)
    
    return False, None, "Max retries exceeded"
```

---

## **Step 7: Logging Improvements**

### Structured Logging:
```python
def _log_api_call(self, service_name, request_data, response_data, status, error=None):
    """Structured logging for API calls"""
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'service': service_name,
        'model': self._name,
        'record_id': self.id,
        'record_name': self.name,
        'request_summary': request_data[:200] if request_data else None,
        'response_summary': response_data[:200] if response_data else None,
        'status': status,
        'error': error
    }
    
    if status == 'success':
        _logger.info(f"API Success: {service_name} - {self.name}", extra=log_entry)
    else:
        _logger.error(f"API Error: {service_name} - {self.name}", extra=log_entry)
    
    # Optional: Store in database for audit trail
    # self.env['api.log'].create(log_entry)
```

---

## **Implementation Checklist**

### Phase 1: Core Helper Methods
- [ ] Add `_get_error_text_from_code()` to AccountMove
- [ ] Add `_get_error_text_from_code()` to StockPicking  
- [ ] Add `_safe_soap_request()` to AccountMove
- [ ] Add `_safe_soap_request()` to StockPicking
- [ ] Add `_parse_xml_response()` to AccountMove
- [ ] Add `_parse_xml_response()` to StockPicking

### Phase 2: Update RS.GE Waybill Calls
- [ ] Update `get_name_from_tin()` with error handling
- [ ] Update `chek_service_user()` calls with error handling
- [ ] Improve `save_waybill()` error handling
- [ ] Ensure all RS.GE calls use new helpers

### Phase 3: Update Revenue Service Calls
- [ ] Update `chek()` with error handling
- [ ] Update `get_un_id_from_tin()` with error handling
- [ ] Update `save_invoice()` with error handling
- [ ] Update `save_invoice_desc()` with error handling
- [ ] Update `change_invoice_status()` with error handling
- [ ] Update `get_invoice()` with error handling

### Phase 4: Testing
- [ ] Test with invalid credentials
- [ ] Test with invalid TIN
- [ ] Test with network timeout
- [ ] Test with malformed XML
- [ ] Test with various RS error codes
- [ ] Test with various Revenue error codes

### Phase 5: Batch Integration
- [ ] Ensure batch methods catch and log all errors
- [ ] Show specific error codes in batch summary
- [ ] Don't stop on first error - continue processing

---

## **Expected Error Messages (User-Friendly)**

### Before:
```
Error: list index out of range
Error: 'NoneType' object has no attribute 'text'
Error: Connection refused
```

### After:
```
✗ RS.GE ავტორიზაცია ვერ მოხერხდა: არასწორი მომხმარებელი ან პაროლი
✗ საიდენტიფიკაციო ნომერი არასწორია
✗ კავშირის შეცდომა - შეამოწმეთ ინტერნეტი
✗ ბარკოდი სავალდებულოა
✗ ზედნადების ატვირთვა ვერ მოხერხდა: ასეთი ინვოისი უკვე არსებობს
```

---

## **Benefits**

1. ✅ **Every API call** has error handling
2. ✅ **User-friendly** Georgian error messages
3. ✅ **No silent failures** - all errors logged and shown
4. ✅ **Network resilient** - timeouts, retries, connection errors handled
5. ✅ **Debugging friendly** - comprehensive logging
6. ✅ **Batch friendly** - errors don't stop entire batch
7. ✅ **Maintainable** - centralized error handling code

---

## **Estimated Work**

- **Helper methods:** 3 methods × 2 classes = 6 methods (~200 lines)
- **Update API calls:** ~15 methods × 2 classes = 30 updates (~600 lines)  
- **Testing:** ~4 hours
- **Total time:** ~8-10 hours

---

## **My Recommendation**

Implement in this order:
1. **Add helper methods first** (1 hour)
2. **Update most critical calls** - save_waybill, save_invoice (2 hours)
3. **Update remaining calls** - get_name_from_tin, etc (3 hours)
4. **Add retry logic** if needed (1 hour)
5. **Testing** (3 hours)

Want me to start implementing? 🚀

