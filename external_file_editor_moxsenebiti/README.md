# External File Editor - Moxsenebiti

This module allows editing moxsenebiti files using an external editor service.

## Key Differences from `external_file_editor`

- **Model**: Works with `moxsenebiti` instead of `approval.request`
- **Session Model**: `file.editor.session.moxsenebiti` with `moxsenebiti_id` field
- **Button**: Added "ფაილის რედაქტირება" button in moxsenebiti form view
- **Callback Route**: `/external_file_editor_moxsenebiti/callback`
- **Client Action**: `external_file_editor_moxsenebiti`

## Installation

1. Copy module to addons directory
2. Update Apps List
3. Install "External File Editor - Moxsenebiti" module
4. Make sure external editor service is running on `http://localhost:4706/wordedit`

## Usage

1. Open a moxsenebiti record that has a file attached (`x_studio_file`)
2. Click "ფაილის რედაქტირება" button in header
3. File will be sent to external editor silently (no popup)
4. External editor must call back with: db, login, password, token, Document

## Callback Payload

```json
{
  "db": "database_name",
  "login": "user_login",
  "password": "user_password",
  "token": "session-token-uuid",
  "Document": "base64_edited_file_content"
}
```
