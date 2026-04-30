# External File Editor - Database Authentication

## Overview

This module now supports **multi-database authentication** similar to `transfer_board_api`.

## Authentication Flow

### 1. **Odoo Sends to External Editor**

When user clicks "ფაილის რედაქტირება", Odoo sends:

```json
POST http://localhost:4706/wordedit
{
  "Document": "base64_file_content",
  "fileName": "document.docx",
  "CallbackURL": "http://10.10.53.111:8069/external_file_editor/callback?db=ggtc",
  "token": "session-token-uuid",
  "db": "database_name",
  "login": "user_login"
}
```

### 2. **External Editor Must Call Back With:**

```json
POST http://10.10.53.111:8069/external_file_editor/callback?db=ggtc
Content-Type: application/json

{
  "db": "database_name",
  "login": "user_login",
  "password": "user_password",
  "token": "session-token-uuid",
  "Document": "base64_edited_file_content"
}
```

### 3. **Odoo Callback Process**

1. ✅ Validates `db`, `login`, `password` are provided
2. ✅ Authenticates user: `request.session.authenticate(db, {login, password})`
3. ✅ Finds active session by `token`
4. ✅ Updates `x_studio_file` in approval request
5. ✅ Marks session as `completed`

## Security Notes

⚠️ **Important:**
- Password is **NOT** stored in Odoo session
- Password must come from external editor's secure storage
- Each callback authenticates fresh against specified database
- Token ensures request is for correct session

## Testing

### Test Callback with Postman:

**URL:** `http://10.10.53.111:8069/external_file_editor/callback`

**Method:** POST

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "db": "your_database_name",
  "login": "admin",
  "password": "admin_password",
  "token": "test-token-12345",
  "Document": "VGVzdCBFZGl0ZWQgRG9jdW1lbnQ="
}
```

### Expected Responses:

**Authentication Failed:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": false,
    "error": "Authentication failed"
  }
}
```

**Invalid Token:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": false,
    "error": "Invalid or inactive session"
  }
}
```

**Success:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "message": "File updated successfully",
    "approval_request_id": 123,
    "session_id": 456
  }
}
```

## Logs

Check Odoo logs for:
```
INFO ... === CALLBACK RECEIVED ===
INFO ... Database: your_database
INFO ... Login: user_login
INFO ... Token: session-token...
INFO ... User authenticated successfully: user_login (UID: 2)
INFO ... Updating approval request ID: 123
INFO ... === FILE UPDATED SUCCESSFULLY ===
```

## Comparison with transfer_board_api

| Feature | transfer_board_api | external_file_editor |
|---------|-------------------|---------------------|
| Auth Method | db + login + password | db + login + password |
| Endpoint Type | `type='json'` | `type='json'` |
| Auth Required | Yes | Yes |
| CSRF | Disabled | Disabled |
| Multi-DB Support | ✅ Yes | ✅ Yes |
| Session Token | ❌ No | ✅ Yes |

## Implementation Pattern

Both modules use the same authentication pattern:

```python
# Validate credentials provided
if not all([db, login, password]):
    return {'success': False, 'error': 'Missing fields'}

# Authenticate
uid = request.session.authenticate(db, {
    'login': login,
    'password': password,
    'type': 'password'
})

if not uid:
    return {'success': False, 'error': 'Authentication failed'}

# Process request with authenticated user
# request.env['model'].sudo().operation()
```

This ensures the callback works correctly even when:
- Multiple databases exist
- Different users have different permissions
- Cross-database operations are attempted
