# Document to PDF Wizard

## Overview
This Odoo module provides a **wizard interface** to convert DOCX files to PDF and **automatically attach** them to any record.

## Features
- **Wizard (TransientModel)** - Popup interface for conversion
- **Auto-attach to records** - PDF automatically added to source record's attachments
- Upload DOCX files
- Convert DOCX to PDF with one click
- Works from any model (Sale Order, Invoice, etc.)
- Works with LibreOffice or MS Word

## Installation

### Prerequisites
Install one of the following:

**Option 1: docx2pdf (Windows with MS Word)**
```bash
cd D:\odoo-work\odoo18
venv\Scripts\python.exe -m pip install docx2pdf
```

**Option 2: LibreOffice (All platforms)**
- Windows: Download from https://www.libreoffice.org/download/download/
- Linux: `sudo apt-get install libreoffice`

### Module Installation
1. Copy the `doc_pdf_wizard` folder to your Odoo addons directory (fmgGeo1)
2. Install dependencies (see above)
3. Restart your Odoo server
4. Update the Apps list
5. Search for "Document to PDF Wizard"
6. Click Install

## Usage

### From Sale Order (or any record)
1. Open a **Sale Order** (or any other record)
2. Click the **"Convert DOCX to PDF"** button in the header
3. Wizard popup opens
4. Upload your **DOCX File**
5. Click **Convert to PDF**
6. PDF is automatically attached to the Sale Order!
7. Check the **Attachments** icon - your PDF is there!

### From Menu
1. Go to **PDF Wizard** → **Convert DOCX to PDF**
2. Upload DOCX file
3. Click **Convert to PDF**
4. (No attachment created when opened from menu)

## How It Works

### Context Detection
- When opened from a record (e.g., Sale Order), the wizard captures:
  - `active_model` - The model name (e.g., 'sale.order')
  - `active_id` - The record ID
- After conversion, creates `ir.attachment` linked to that record

### Example Flow
```
Sale Order (ID: 123)
  ↓ Click "Convert DOCX to PDF" button
  ↓ Wizard opens with context
  ↓ Upload DOCX file
  ↓ Click "Convert to PDF"
  ↓ PDF created and attached
  ↓ ir.attachment created:
      - res_model: 'sale.order'
      - res_id: 123
      - name: 'document.pdf'
```

## Add Button to Any Model

To add the wizard button to other models, create a view inheritance:

```xml
<record id="view_YOUR_MODEL_form_convert_pdf" model="ir.ui.view">
    <field name="name">your.model.form.convert.pdf</field>
    <field name="model">your.model</field>
    <field name="inherit_id" ref="module.view_your_form"/>
    <field name="arch" type="xml">
        <xpath expr="//header" position="inside">
            <button name="%(doc_pdf_wizard.action_doc_pdf_wizard)d" 
                    string="Convert DOCX to PDF" 
                    type="action" 
                    class="btn-secondary"/>
        </xpath>
    </field>
</record>
```

## Technical Details

### Model: `doc.pdf.wizard`
- **Type:** TransientModel (Wizard)
- **Fields:**
  - `name`: Document name
  - `docx_file`: Binary field for DOCX file
  - `pdf_file`: Binary field for generated PDF (invisible)
  - `source_model`: Source model from context
  - `source_res_id`: Source record ID from context
  - `state`: Upload or Converted

### Attachment Creation
When wizard is opened from a record:
- Captures `active_model` and `active_id` from context
- After conversion, creates `ir.attachment`:
  - Links to source record
  - Visible in record's attachment list
  - Can be downloaded from there

## Example Use Cases

1. **Sale Orders** - Convert quotation documents to PDF
2. **Invoices** - Convert supporting documents to PDF
3. **Projects** - Convert project documents to PDF
4. **Partners** - Convert contracts to PDF
5. **Any model** - Add conversion capability anywhere!

## Advantages

✅ **Auto-attachment** - PDF saved to record automatically
✅ **Popup interface** - No page navigation
✅ **Universal** - Works from any model
✅ **Clean** - No visible PDF field in wizard
✅ **Tracked** - Attachments visible in record's chatter/attachments

## License
LGPL-3
