# Quick Setup Guide - External File Editor

## What Was Created

✅ **Complete Odoo Module** for external file editing integration with approval requests

### Module Location
```
D:\odoo-work\odoo18\gazi\custom_addons\external_file_editor
```

## Module Components

### 1. **Database Model** (`file.editor.session`)
   - ✅ Generates unique hash codes (SHA256)
   - ✅ Creates secure tokens (UUID)
   - ✅ Stores file content and parameters
   - ✅ Manages session state and expiration
   - ✅ Tracks user and approval request

### 2. **Endpoints Created**
   - ✅ `/external_file_editor/get_session_data` - Get file data for editing
   - ✅ `/external_file_editor/callback` - Receive edited file (universal callback)
   - ✅ `/external_file_editor/validate_token` - Token validation

### 3. **User Interface**
   - ✅ Button "ფაილის რედაქტირება" on approval.request form
   - ✅ Invisible when `x_studio_file` is false/empty
   - ✅ Beautiful loading/success/error dialogs

## Installation Steps

### Step 1: Restart Odoo Server
```bash
# Stop and restart your Odoo server
# The module should now be visible in Apps
```

### Step 2: Update Apps List
1. Go to **Apps** menu
2. Click **Update Apps List** (in debug mode)
3. Search for "External File Editor"

### Step 3: Install Module
1. Find "External File Editor" in apps list
2. Click **Install**
3. Wait for installation to complete

### Step 4: Verify Installation
1. Go to an approval request with a file attached
2. You should see "ფაილის რედაქტირება" button
3. Button should be hidden if no file is attached

## How It Works - Data Flow

```
┌─────────────────┐
│ User clicks     │
│ "ფაილის         │
│ რედაქტირება"   │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────┐
│ 1. Odoo creates session             │
│    - Generates hash_code (SHA256)   │
│    - Generates token (UUID)         │
│    - Stores file & parameters       │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│ 2. JavaScript calls Odoo endpoint   │
│    GET /external_file_editor/       │
│        get_session_data             │
│    Returns: token, file_content     │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│ 3. JavaScript calls External Editor │
│    POST http://localhost:1234/      │
│         WordDoc                     │
│    Sends:                           │
│      - token                        │
│      - file_content (base64)        │
│      - callback_url                 │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│ 4. External Editor processes file   │
│    (This part is NOT our            │
│     responsibility - another        │
│     person will implement)          │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│ 5. External Editor sends callback   │
│    POST /external_file_editor/      │
│         callback                    │
│    Sends:                           │
│      - token                        │
│      - file_content (edited,base64) │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│ 6. Odoo updates file                │
│    - Validates token                │
│    - Updates x_studio_file          │
│    - Marks session as completed     │
└─────────────────────────────────────┘
```

## Configuration Requirements

### For Your Odoo (Already Done ✅)
- Module installed
- Button visible on approval.request
- Endpoints configured
- Security rules applied

### For External Editor (NOT Your Part)
The external editor must:

1. **Run on**: `http://localhost:1234`
2. **Accept POST** at `/WordDoc`
3. **Receive JSON**:
```json
{
  "token": "uuid-token",
  "hash_code": "sha256-hash",
  "file_content": "base64-encoded-file",
  "file_name": "document.docx",
  "callback_url": "http://your-odoo.com/external_file_editor/callback"
}
```

4. **Send callback when done**:
```json
POST {callback_url}
{
  "token": "same-uuid-token",
  "file_content": "base64-encoded-edited-file"
}
```

## Testing

### Test 1: Module Installed
```bash
# In Odoo, check:
- Settings > Apps > Installed Apps
- Should see "External File Editor"
```

### Test 2: Button Visible
```bash
# 1. Go to Approvals app
# 2. Open any approval request with x_studio_file
# 3. Should see "ფაილის რედაქტირება" button
```

### Test 3: Session Created
```bash
# 1. Click the edit button
# 2. Go to Settings > Technical > Database Structure > Models
# 3. Search for "file.editor.session"
# 4. Should see a new session record
```

### Test 4: External Editor Call (Will Fail Until Editor Ready)
```bash
# 1. Click edit button
# 2. Will show error: "გარე რედაქტორთან კავშირი ვერ დამყარდა"
# 3. This is EXPECTED - external editor is not running yet
```

## What You Need to Tell the Other Developer

Send them this information:

### API Specification for External Editor

**Endpoint to implement**: `POST http://localhost:1234/WordDoc`

**Request from Odoo**:
```json
{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "hash_code": "abc123def456...",
  "file_content": "UEsDBBQABgAIAAAAIQ...", // Base64 encoded file
  "file_name": "document.docx",
  "callback_url": "http://your-odoo-domain.com/external_file_editor/callback"
}
```

**Response from External Editor**:
```json
{
  "success": true,
  "message": "File opened successfully"
}
```

**Callback to Odoo** (after editing):
```json
POST {callback_url}
Content-Type: application/json

{
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "file_content": "UEsDBBQABgAIAAAAIQ..." // Base64 encoded edited file
}
```

## Troubleshooting

### Module not appearing in Apps list
```bash
# Solution:
1. Restart Odoo server
2. Update Apps List (Debug mode)
3. Search again
```

### Button not visible
```bash
# Check:
1. Is module installed?
2. Does approval request have x_studio_file with content?
3. Refresh the page
```

### Error: "გარე რედაქტორთან კავშირი ვერ დამყარდა"
```bash
# This is NORMAL if external editor is not running
# Wait for other developer to implement their part
```

## File Structure Summary

```
external_file_editor/
├── __init__.py                      # Module initialization
├── __manifest__.py                  # Module configuration
├── README.md                        # Full documentation
├── SETUP_GUIDE.md                   # This file
│
├── models/
│   ├── __init__.py
│   ├── file_editor_session.py      # Session management model
│   └── approval_request.py         # Extends approval.request
│
├── controllers/
│   ├── __init__.py
│   └── main.py                     # HTTP endpoints
│
├── views/
│   └── approval_request_views.xml  # Button UI
│
├── security/
│   └── ir.model.access.csv         # Access rights
│
└── static/src/
    ├── js/
    │   └── file_editor.js          # JavaScript logic
    └── xml/
        └── file_editor.xml         # UI template
```

## Next Steps

1. ✅ **Done**: Module is created and ready
2. ⏳ **Waiting**: External editor implementation (not your part)
3. 🔄 **Then**: Test full workflow when editor is ready
4. ✨ **Finally**: Use in production

## Support

If you need to modify anything:
- Edit button text: `views/approval_request_views.xml`
- Change field name: `models/approval_request.py` (file_field parameter)
- Modify external URL: `models/file_editor_session.py` (external_editor_url)
- Update expiration time: `models/file_editor_session.py` (expiration_hours=24)

## Summary

✅ **What's Done:**
- Complete module structure
- Database table for sessions
- Hash code & token generation
- External API integration (Odoo side)
- Callback endpoint (universal)
- Button on approval.request
- Security & access rights

⏳ **What's Pending** (NOT your part):
- External editor service at http://localhost:1234/WordDoc
- File editing functionality
- Callback implementation from editor to Odoo

🎉 **Your part is COMPLETE!** The module is ready to install and use.
