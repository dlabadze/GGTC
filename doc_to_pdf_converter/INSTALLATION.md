# Quick Installation Guide

## ✅ Pure Python Solution - NO External Programs Needed!

This module works **WITHOUT** LibreOffice, MS Word, or any external programs!

## Step 1: Install Python Libraries

### Option A: Run the Installation Script (Easiest)
1. Double-click: `install_dependencies.bat`
2. Wait for installation to complete
3. Restart Odoo server

### Option B: Manual Installation
Open PowerShell or Command Prompt:

```powershell
cd D:\odoo-work\odoo18
venv\Scripts\python.exe -m pip install python-docx reportlab
```

## Step 2: Install Odoo Module
1. Restart your Odoo server
2. Go to Apps → Update Apps List
3. Search for "Document to PDF Converter"
4. Click Install

## Step 3: Test It!
1. Go to **Document Converter** menu
2. Click **Create**
3. Upload a DOCX file
4. Click **Convert to PDF**
5. Download your PDF! ✨

## What's Installed?
- `python-docx` - Reads DOCX files
- `reportlab` - Creates PDF files

**Both are pure Python libraries - no external dependencies!**

## Troubleshooting

### Error: "PDF conversion failed"
→ Run: `venv\Scripts\python.exe -m pip install python-docx reportlab`

### Error: "ImportError: No module named 'docx'"
→ Install python-docx: `venv\Scripts\python.exe -m pip install python-docx`

### Error: "ImportError: No module named 'reportlab'"
→ Install reportlab: `venv\Scripts\python.exe -m pip install reportlab`

## Done!
Your module is ready to convert DOCX files to PDF!

