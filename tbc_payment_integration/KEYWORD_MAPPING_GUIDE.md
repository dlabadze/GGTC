# Keyword to Account Mapping - User Guide

## Overview

This feature allows you to map specific keywords found in transaction comments (`entry_comment` field) directly to accounts. When a transaction contains a keyword like "პრემია" (bonus), it will automatically use the account you specified (e.g., 3130).

## How It Works

### Priority System:
```
1. KEYWORD MAPPING (Highest Priority)
   └─> If keyword found in entry_comment → Use mapped account

2. TBC CODE MAPPING (Fallback)
   └─> If no keyword match → Use product group mapping

3. STANDARD ODOO (Final Fallback)
   └─> If no TBC mapping → Use Odoo's default matching
```

## Setup Instructions

### Step 1: Access Keyword Mappings
```
ბანკის ამონაწერი → Keyword → Account Mapping
```

### Step 2: Create Your First Mapping

Click **Create** and fill in:

| Field | Example | Description |
|-------|---------|-------------|
| **Keyword** | `პრემია` | Word to search in entry_comment |
| **Account** | `3130` | Account to use when keyword is found |
| **Priority (Sequence)** | `10` | Lower = higher priority (optional) |
| **Case Sensitive** | ☐ Unchecked | Usually leave unchecked for Georgian text |
| **Active** | ☑ Checked | Enable this mapping |

Click **Save**.

### Step 3: Create More Mappings

**Example Setup for Georgian Business:**

| Priority | Keyword | Account | Account Name |
|----------|---------|---------|--------------|
| 1 | პრემია | 3130 | Bonus Expenses |
| 2 | ხელფასი | 3110 | Salary Expenses |
| 3 | მივლინება | 3210 | Travel Expenses |
| 4 | საწვავი | 3310 | Fuel Expenses |
| 5 | კომუნალური | 3410 | Utility Expenses |
| 6 | ქირა | 3510 | Rent Expenses |
| 7 | ინტერნეტი | 3420 | Internet Expenses |
| 8 | დივიდენდი | 5310 | Dividend Expenses |

## Real Usage Examples

### Example 1: Bonus Payment

**Transaction:**
- `entry_comment`: "თანამშრომლისთვის პრემიის გადახდა"
- `entry_amount_debit`: 500

**Result:**
- ✅ Keyword "პრემია" found
- ✅ Account 3130 (Bonus Expenses) used automatically
- ✅ Reconciliation suggests correct account

### Example 2: Salary Payment

**Transaction:**
- `entry_comment`: "თებერვლის ხელფასი"
- `entry_amount_debit`: 2000

**Result:**
- ✅ Keyword "ხელფასი" found
- ✅ Account 3110 (Salary Expenses) used automatically

### Example 3: Multiple Keywords

**Transaction:**
- `entry_comment`: "ხელფასი და პრემია"

**Result:**
- 🔍 System checks in sequence order
- ✅ First match wins (e.g., if "პრემია" has lower sequence)
- Account 3130 used

## Advanced Features

### 1. Priority Control

Use **Sequence** field to control which keyword has priority:

```
Sequence 1:  პრემია → 3130  (checked first)
Sequence 10: ხელფას → 3110  (checked second)
Sequence 20: bonus → 3130   (checked third)
```

**Pro Tip:** Use increments of 10 (10, 20, 30...) so you can insert new mappings between existing ones later.

### 2. Case Sensitivity

**Unchecked (recommended):**
- "პრემია" matches "პრემია", "ᲞᲠᲔᲛᲘᲐ", "Პრემია"
- More flexible for Georgian text

**Checked:**
- "პრემია" only matches exact case "პრემია"
- "ᲞᲠᲔᲛᲘᲐ" won't match

### 3. Partial Matching

Keywords match anywhere in the comment:

```
Keyword: "ხელფასი"

✅ Matches: "თებერვლის ხელფასი"
✅ Matches: "ხელფასის დარიცხვა"
✅ Matches: "გადახდილი ხელფასი თანამშრომელს"
❌ No match: "თებერვალი პრემია"
```

### 4. Archive Instead of Delete

Don't delete mappings - archive them!

- Click the archive button (📦) in the form
- Keeps history but disables the mapping
- Can be restored later

## Integration with Reconciliation

### Automatic Reconciliation:

1. **Import transaction** with entry_comment
2. **Create statement line**
3. **Open reconciliation widget**
4. System checks:
   - First: Keyword mappings ✓
   - Second: TBC code mappings
   - Third: Standard Odoo matching
5. **Suggests account** from keyword mapping
6. **Validate** - done!

### Manual Override:

Even with keyword mapping, you can always:
- Change the suggested account manually
- Add additional lines
- Modify partner, amount, etc.

## Troubleshooting

### Keyword Not Matching

**Check:**
1. ✅ Mapping is Active
2. ✅ Keyword spelled correctly
3. ✅ Case sensitivity setting
4. ✅ entry_comment actually contains the keyword
5. ✅ No higher priority keyword matched first

**Debug:**
- Check Odoo logs for message: `"Keyword match found: 'პრემია' -> Account 3130"`

### Wrong Account Used

**Possible Causes:**
1. Higher priority keyword matched first
2. Different keyword with same substring
3. TBC code mapping overriding (shouldn't happen - keyword has priority)

**Solution:**
- Adjust sequence numbers
- Make keywords more specific
- Check logs to see which keyword matched

### Multiple Accounts for Same Keyword

**Not supported directly.** But you can:

**Option A:** Use more specific keywords
```
Instead of:        Use:
"ხელფასი"  →      "ხელფასი ოფისი" → 3110
                  "ხელფასი მაღაზია" → 3111
```

**Option B:** Use TBC code mapping with comment keywords
- Combine product group + keyword in TBC code mapping
- Keep keyword mapping for simple cases

## Best Practices

### 1. Start Simple
```
✅ Create 5-10 most common keywords
✅ Test with real transactions
✅ Add more as needed
```

### 2. Use Clear Keywords
```
✅ Good: "პრემია", "ხელფასი", "ქირა"
❌ Bad: "გა", "და", "ი" (too generic)
```

### 3. Document Your Mappings
```
Use the Description field:
"პრემია" → "Monthly and annual bonuses for all staff"
```

### 4. Review Regularly
```
Monthly:
- Check if mappings are being used
- Add new keywords for recurring transactions
- Archive unused keywords
```

### 5. Coordinate with Team
```
- Use consistent keywords in transaction comments
- Document which keywords map to which accounts
- Train accounting staff on the system
```

## Quick Reference

### Access Menu:
```
ბანკის ამონაწერი → Keyword → Account Mapping
```

### Create Mapping:
```
Keyword: [your keyword]
Account: [account code]
Sequence: [priority number]
Active: ✓
```

### Test Mapping:
```
1. Create test transaction with keyword in entry_comment
2. Create statement line
3. Open reconciliation
4. Check suggested account
```

### Priority Formula:
```
Lower Sequence Number = Higher Priority = Checked First
```

## Examples by Industry

### Retail:
```
სახელფასო → 3110
დღგ → 2410
საქონელი → 2110
```

### Service Company:
```
კონსულტაცია → 4110
მომსახურება → 4120
გადასახადი → 2410
```

### Manufacturing:
```
ნედლეული → 2010
ხელფასი → 3110
ელექტროენერგია → 3310
```

## Summary

✅ **Simple** - Just keyword + account
✅ **Flexible** - Works with any keyword
✅ **Priority** - Sequence control
✅ **Automatic** - No manual selection needed
✅ **Override** - Can manually change if needed

Perfect for recurring transactions with consistent comment patterns!
