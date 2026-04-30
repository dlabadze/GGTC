# External File Editor Module

This module integrates Odoo with an external file editor service running on `http://localhost:4706/wordedit`.

## Features

✅ Sends file to external editor via JavaScript POST request
✅ Creates secure session with hash code and token
✅ Receives callback from external editor with edited file
✅ Updates file in Odoo after editing

## Workflow

### 1. User Clicks "ფაილის რედაქტირება" Button
- Creates a new file editing session
- Generates unique token and hash code
- Opens JavaScript client action

### 2. JavaScript Sends File to External Editor
**POST Request to:** `http://localhost:4706/wordedit`

**Payload:**
```json
{
  "Document": "base64_encoded_file_content",
  "fileName": "document.docx",
  "CallbackURL": "http://your-odoo-server.com/external_file_editor/callback",
  "token": "unique-session-token"
}
```

### 3. External Editor Processes File
- User edits the file in external editor
- When done, external editor sends callback to Odoo

### 4. Callback Updates File in Odoo
**Callback Endpoint:** `/external_file_editor/callback`

**Expected Callback Payload:**
```json
{
  "token": "unique-session-token",
  "Document": "base64_encoded_edited_file_content"
}
```

**Callback Logic:**
1. Finds active session by token
2. Validates session is active
3. Updates file in approval request
4. Marks session as completed

## Installation

1. Copy module to addons directory
2. Update Apps List
3. Install "External File Editor" module
4. Make sure external editor service is running on `http://localhost:4706/wordedit`

## Configuration

### Change External Editor URL
Edit the default URL in `models/file_editor_session.py`:

```python
external_editor_url = fields.Char('External Editor URL', default='http://localhost:4706/wordedit')
```

## File Structure

```
external_file_editor/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py              # Callback endpoint handler
├── models/
│   ├── __init__.py
│   ├── approval_request.py  # Button action to send file
│   └── file_editor_session.py  # Session management
├── static/
│   └── src/
│       ├── js/
│       │   └── file_editor.js  # JavaScript to call external editor
│       └── xml/
│           └── file_editor.xml  # UI template
├── views/
│   └── approval_request_views.xml  # Button definition
└── security/
    └── ir.model.access.csv
```

## Technical Details

### Session Model (`file.editor.session`)
- **hash_code**: Unique SHA256 hash for session
- **token**: UUID token for authentication
- **state**: active | completed | expired | cancelled
- **expire_date**: Session expiration (default: 24 hours)
- **callback_url**: Computed callback URL
- **external_editor_url**: External editor endpoint

### Security
- Token-based authentication
- Public callback endpoint (csrf=False)
- Session validation before file update
- Only active sessions can receive callbacks

## API Reference

### Callback Endpoint

**URL:** `/external_file_editor/callback`
**Method:** POST (JSON)
**Auth:** Public
**CSRF:** Disabled

**Request:**
```json
{
  "token": "uuid-token",
  "Document": "base64_encoded_file"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "File updated successfully"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message"
}
```

## Troubleshooting

### Error: "გარე რედაქტორთან კავშირი ვერ დამყარდა"
- Check external editor service is running
- Verify URL: `http://localhost:4706/wordedit`
- Check browser console for CORS errors

### Error: "Invalid or inactive session token"
- Session may have expired (24 hours)
- Session may have already been used (completed)
- Token mismatch

### File Not Updating After Callback
- Check Odoo logs for callback errors
- Verify callback payload format
- Ensure token is valid and active

## Logs

Check Odoo server logs for callback processing:
```
_logger.info("Callback received with data: ...")
_logger.info("Updating file for approval request ID: ...")
_logger.error("Invalid or inactive session token: ...")
```

## Support

For issues or questions, check the Odoo server logs and browser console for detailed error messages.
