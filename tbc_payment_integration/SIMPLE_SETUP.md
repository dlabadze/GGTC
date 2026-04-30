# TBC Payment Integration - SIMPLE Setup Guide

## You Already Have Everything You Need!

Your existing `tbc.code.mapping` model handles EVERYTHING:
- ✅ Product group codes
- ✅ Keywords in comments (პრემია, ხელფასი, etc.)
- ✅ Account mapping
- ✅ Debit/Credit type

## What You Need to Do

### Step 1: Configure Your TBC Code Mappings (You probably already did this!)

Go to: **ბანკის ამონაწერი → კოდების მეპინგი**

**Example:**
```
Code: 210105
Debit/Credit: Debit
Comment Keywords: პრემია, bonus
Account: 3130 (Bonus Expense)
Partner Required: Yes
```

**Another Example:**
```
Code: 210105
Debit/Credit: Debit
Comment Keywords: ხელფასი, salary
Account: 3110 (Salary Expense)
Partner Required: Yes
```

**Generic Fallback:**
```
Code: 210105
Debit/Credit: Debit
Comment Keywords: (empty)
Account: 3100 (General Salary)
Partner Required: Yes
```

### Step 2: Create ONE Reconciliation Model (NEW!)

Go to: **Accounting → Configuration → Reconciliation Models**

Click **Create**:
```
Name: TBC Bank Transactions
Rule Type: Suggestion of counterpart values
Match Journals: [Select your bank journals]
Use TBC Mapping: ✓ CHECK THIS!
TBC Match Product Group: (leave empty to match all)
TBC Code Mappings: (leave empty - system uses all)
Auto-validate: ☐ (uncheck - review manually first)
```

**That's it!** This ONE model handles ALL your TBC transactions using ALL your code mappings.

### Step 3: Use It

1. **Import transactions** (via TBC Payment Wizard)
2. **Create statement lines** (click button)
3. **Open reconciliation** (Accounting → Bank → Reconciliation)
4. System automatically:
   - Checks product_group (e.g., "210105")
   - Checks entry_comment for keywords ("პრემია")
   - Suggests correct account (3130)
5. **Validate** - Done!

## How It Works

```
Transaction:
├─ product_group: "210105"
├─ entry_comment: "თანამშრომლის პრემია"
├─ entry_amount_debit: 500
└─ Creates statement line
    ↓
Reconciliation Model: "TBC Bank Transactions"
├─ Checks: Is this from TBC? YES
├─ Finds tbc.code.mapping records with code_field="210105"
├─ Found 3 mappings:
│   1. Comment: "პრემია" → Account 3130 ✓ MATCHES!
│   2. Comment: "ხელფასი" → Account 3110
│   3. Comment: empty → Account 3100
└─ Uses mapping #1 (პრემია → 3130)
    ↓
Suggests: Account 3130
```

## FAQ

**Q: Do I need one reconciliation model per code mapping?**
**A: NO!** One reconciliation model uses ALL your code mappings.

**Q: Do I need a separate keyword model?**
**A: NO!** Your `tbc.code.mapping` already has the `comment` field for keywords.

**Q: What if I have 100 code mappings?**
**A: Still just ONE reconciliation model!** The system automatically finds the right mapping based on product_group + keywords.

**Q: Can I have multiple reconciliation models?**
**A: Yes, if you want different rules:**
- One for auto-validate salaries
- One for manual review expenses
- One per bank journal
- One for small/large amounts

But you can start with just ONE and it will work!

## Summary

**What you already have:**
- ✅ `tbc.code.mapping` records with product groups and keywords

**What you need to create:**
- ✅ ONE reconciliation model with "Use TBC Mapping" checked

**What you DON'T need:**
- ❌ Separate keyword model
- ❌ Multiple reconciliation models (unless you want different rules)
- ❌ Complexity!

## Example Complete Setup

**Your existing tbc.code.mapping records:**
```
1. 210105, Debit, "პრემია" → 3130
2. 210105, Debit, "ხელფასი" → 3110
3. 210103, Credit, "" → 4110
4. 340120, Debit, "კომუნალური" → 3410
... (50 more mappings)
```

**One new reconciliation model:**
```
"TBC Transactions"
- Use TBC Mapping: ✓
- Everything else: default
```

**Result:** All 50+ mappings work automatically! 🎉
