# 🚀 Quick Start Guide - Batch Upload

## ✨ **NEW FEATURE: Batch Upload Multiple Records!**

---

## 📍 **Where Are The Buttons?**

### **For Invoices (AccountMove):**
```
Accounting → Customers → Invoices (List View)

You'll see at the top:
┌─────────────────────────────────────────────┐
│ [📤 RS ზედნადები (ბათჩი)]  [📋 RS ფაქტურა (ბათჩი)] │
└─────────────────────────────────────────────┘
```

### **For Deliveries (StockPicking):**
```
Inventory → Operations → Transfers (List View)

You'll see at the top:
┌──────────────────────────┐
│ [📦 RS ზედნადები (ბათჩი)]  │
└──────────────────────────┘
```

---

## 🎯 **How To Use - 3 Simple Steps**

### **Step 1: Select Records**
```
☐ INV/2024/001  ←  Click checkboxes
☑ INV/2024/002  ←  to select multiple
☑ INV/2024/003
☑ INV/2024/004
☐ INV/2024/005
```

### **Step 2: Click Batch Button**
```
Click: 📋 RS ფაქტურა (ბათჩი)

Confirmation popup appears:
┌──────────────────────────────┐
│ გსურთ შერჩეული ფაქტურების   │
│ ატვირთვა?                    │
│                              │
│     [Cancel]     [OK]        │
└──────────────────────────────┘
```

### **Step 3: View Results**
```
Success notification appears:
┌────────────────────────────────────────────┐
│ ფაქტურების ატვირთვა დასრულდა               │
│                                            │
│ ✓ წარმატებით ატვირთულია (3):              │
│   INV/2024/002, INV/2024/003, INV/2024/004 │
│                                            │
│ ⊘ გამოტოვებულია (1):                      │
│   - INV/2024/001: უკვე ატვირთულია          │
└────────────────────────────────────────────┘
```

---

## 📊 **What The System Does**

```
For Each Selected Record:
├── Check if already uploaded
│   ├── Yes → Skip (count as skipped)
│   └── No → Continue
│
├── Try to upload
│   ├── Success → Save (commit)
│   └── Error → Log error, rollback
│
└── Continue to next record
    (doesn't stop on errors!)

After All Records:
└── Show summary of results
```

---

## 🎨 **Result Types**

### ✓ **Success (Green)**
```
✓ წარმატებით ატვირთულია (5)
→ All 5 records uploaded successfully
```

### ⊘ **Skipped (Yellow)**  
```
⊘ გამოტოვებულია (2):
  - INV/001: უკვე ატვირთულია
  - INV/002: უკვე ატვირთულია
→ 2 records were already uploaded
```

### ✗ **Errors (Red)**
```
✗ შეცდომები (1):
  - INV/003: ბარკოდი არ არის მითითებული
→ 1 record failed (missing barcode)
```

---

## 💡 **Pro Tips**

### **Tip 1: Filter First, Then Batch**
```
1. Filter: State = "Posted", Not Uploaded
2. Select All matching records
3. Batch upload!
```

### **Tip 2: Check Results Carefully**
```
Green = All good ✅
Yellow = Some skipped (check why)
Red = Errors (fix and retry)
```

### **Tip 3: Already Uploaded = Auto-Skip**
```
System automatically skips records with:
- invoice_id filled (waybill uploaded)
- factura_num filled (factura uploaded)

No need to manually deselect!
```

### **Tip 4: Errors Don't Stop Batch**
```
If 1 out of 10 fails:
→ Other 9 still upload
→ Fix the 1 error
→ Upload just that one
```

---

## ⚡ **Common Scenarios**

### **Scenario 1: Upload 50 Invoices**
```
Time: ~2-5 minutes
Steps:
1. Filter unpublished invoices
2. Select all (or first 50)
3. Click batch button
4. Wait for completion
5. Check results
```

### **Scenario 2: Some Already Uploaded**
```
Selected: 10 invoices
Already uploaded: 3
Will upload: 7

Result:
✓ წარმატებით ატვირთულია (7)
⊘ გამოტოვებულია (3)
```

### **Scenario 3: Network Error**
```
If internet disconnects during batch:
→ Uploaded records are saved
→ Failed records show error
→ Retry failed ones when internet returns
```

---

## 🔍 **Troubleshooting**

### **Problem: Button Not Visible**
**Check:**
- Are you in LIST view? (not form view)
- Are records selected? (checkboxes)
- Is module updated?

### **Problem: All Records Skip**
**Reason:** Already uploaded
**Solution:** Check if invoice_id/factura_num is filled

### **Problem: All Records Fail**
**Check:**
- RS.GE credentials (rs_acc, rs_pass)
- Internet connection
- Required fields (barcode, unit_id, etc.)

### **Problem: Takes Too Long**
**Normal:** 3-5 seconds per record
**50 records** = ~2-5 minutes is normal

---

## 📝 **Comparison: Old vs New**

### **Old Way (One at a Time):**
```
1. Open Invoice 001 → Upload → Wait
2. Open Invoice 002 → Upload → Wait
3. Open Invoice 003 → Upload → Wait
...
50. Open Invoice 050 → Upload → Done!

Time: ~1 hour (includes clicking, waiting, etc.)
```

### **New Way (Batch):**
```
1. Select all 50 invoices
2. Click batch button
3. Wait 2-5 minutes
4. Done!

Time: ~5 minutes total
→ 12x faster! 🚀
```

---

## 🎯 **Best Practices**

### **Do:**
✅ Filter records before selecting  
✅ Check results notification  
✅ Retry failed records after fixing  
✅ Use batch for 5+ records  

### **Don't:**
❌ Upload 1 record with batch button (use form view)  
❌ Ignore error messages  
❌ Select more than 100 at once (too slow)  
❌ Close window during upload  

---

## 🏆 **Success Checklist**

Before batch upload, verify:
- [ ] Records are in correct state (Posted for invoices)
- [ ] Required fields filled (barcode, unit_id, etc.)
- [ ] RS.GE credentials configured
- [ ] Internet connection stable
- [ ] Filtered to show only target records

After batch upload, check:
- [ ] Success count matches expected
- [ ] Skipped records already uploaded (OK)
- [ ] Error messages make sense
- [ ] Failed records fixable

---

## 📞 **Need Help?**

### **Check Logs:**
```
Settings → Technical → Logging

Search for:
- "button_send_soap_request"
- "button_factura"
- Record name (e.g., "INV/2024/001")
```

### **Common Error Messages:**

| Error | Meaning | Fix |
|-------|---------|-----|
| `ბარკოდი არ არის მითითებული` | Missing barcode | Add barcode to product |
| `უკვე ატვირთულია` | Already uploaded | Skip or check invoice_id |
| `კავშირის შეცდომა` | Network error | Check internet |
| `არასწორი პაროლი` | Wrong credentials | Check RS.GE settings |

---

**You're all set! Start uploading in batches and save hours of work!** 🎉

**Remember:** 
- Select multiple → Click batch button → View results
- It's that simple!

