# Document to PDF Converter

## Overview
This Odoo module allows you to convert DOCX (Microsoft Word) files to PDF format with a single click.

## Features
- Upload DOCX files
- Convert DOCX to PDF with one click
- Store both DOCX and PDF files
- Download converted PDF files
- Track conversion history with chatter
- Status tracking (Draft/Converted)

## Installation

### Prerequisites
This module uses **pure Python libraries** - NO external programs needed! No LibreOffice, no MS Word, no paths!

#### Install Required Libraries
Just run this command in your Odoo environment:

```bash
cd D:\odoo-work\odoo18
venv\Scripts\python.exe -m pip install python-docx reportlab
```

That's it! No external programs, no complicated setup!

### Module Installation
1. Copy the `doc_to_pdf_converter` folder to your Odoo addons directory (fmgGeo1)
2. Install Python libraries: `venv\Scripts\python.exe -m pip install python-docx reportlab`
3. Restart your Odoo server
4. Update the Apps list
5. Search for "Document to PDF Converter"
6. Click Install

## Usage

### Converting a Document
1. Go to **Document Converter** → **Documents**
2. Click **Create** (or New)
3. Enter a **Document Name** (optional - will auto-fill from filename)
4. Upload your **DOCX File**
5. Click **Convert to PDF** button
6. The PDF will be generated and stored in the PDF File field
7. You can download the PDF using the **Download PDF** button

### Resetting a Document
If you want to upload a new DOCX file and reconvert:
1. Open the document record
2. Click **Reset to Draft**
3. Upload a new DOCX file
4. Click **Convert to PDF** again

## Technical Details

### Model: `document.converter`
- **Fields:**
  - `name`: Document name
  - `docx_file`: Binary field for DOCX file
  - `pdf_file`: Binary field for generated PDF (readonly)
  - `state`: Draft or Converted
  - `conversion_date`: When the conversion was performed
  - `notes`: Additional notes

### Conversion Methods
The module uses **pure Python libraries**:
1. **python-docx + reportlab** - Professional conversion with styling, tables, headings
2. **Simple text extraction** - Fallback method if needed

✅ No external programs required!
✅ No paths to configure!
✅ Works on all platforms!

## Troubleshooting

### "PDF conversion failed" error
**Solution**: Install the required Python libraries:
```bash
cd D:\odoo-work\odoo18
venv\Scripts\python.exe -m pip install python-docx reportlab
```
Then restart Odoo server.

### Import errors
If you see "ImportError" in logs, it means libraries aren't installed.
Run: `venv\Scripts\python.exe -m pip install python-docx reportlab`

### Permission errors
- Ensure the Odoo user has read/write permissions to the temp directory
- On Windows: Usually no issues
- On Linux: Check `/tmp` permissions

## Support
For issues or questions, please contact your system administrator.

## License
LGPL-3

