# Georgian Month Names Reference

## All 12 Months in Georgian

| Month # | Georgian Name | English Name |
|---------|---------------|--------------|
| 1 | იანვარი | January |
| 2 | თებერვალი | February |
| 3 | მარტი | March |
| 4 | აპრილი | April |
| 5 | მაისი | May |
| 6 | ივნისი | June |
| 7 | ივლისი | July |
| 8 | აგვისტო | August |
| 9 | სექტემბერი | September |
| 10 | ოქტომბერი | October |
| 11 | ნოემბერი | November |
| 12 | დეკემბერი | December |

## Usage Examples

### Full Date Format (Default)
```jinja
{{ date2(docs.date_field) }}
```
**Output:** `16 იანვარი 2025`

### Short Format (Without Year)
```jinja
{{ date2(docs.date_field, 'short') }}
```
**Output:** `16 იანვარი`

### Month and Year Only
```jinja
{{ date2(docs.date_field, 'month_year') }}
```
**Output:** `იანვარი 2025`

## Common Use Cases

### Contract Date (ხელშეკრულების თარიღი)
```jinja
ხელშეკრულება დადებულია {{ date2(docs.date_contract) }} წელს
```
**Output:** `ხელშეკრულება დადებულია 16 იანვარი 2025 წელს`

### Birth Date (დაბადების თარიღი)
```jinja
დაბადების თარიღი: {{ date2(docs.birthday) }}
```
**Output:** `დაბადების თარიღი: 5 მარტი 1990`

### Employment Date (დასაქმების თარიღი)
```jinja
სამსახურში მიღების თარიღი: {{ date2(docs.date_join) }}
```
**Output:** `სამსახურში მიღების თარიღი: 1 აპრილი 2020`

### Invoice Date (ინვოისის თარიღი)
```jinja
გადახდის თარიღი: {{ date2(docs.invoice_date) }}
ვადა: {{ date2(docs.invoice_date_due) }}
```
**Output:** 
```
გადახდის თარიღი: 15 მაისი 2025
ვადა: 30 მაისი 2025
```

### Period Range (პერიოდი)
```jinja
პერიოდი: {{ date2(docs.date_start, 'short') }} - {{ date2(docs.date_end, 'short') }}
```
**Output:** `პერიოდი: 1 იანვარი - 31 დეკემბერი`

### Month Report (თვიური ანგარიში)
```jinja
ანგარიში {{ date2(docs.report_date, 'month_year') }}-ის თვისთვის
```
**Output:** `ანგარიში იანვარი 2025-ის თვისთვის`

## Test Examples

### Different Months
```jinja
{{ date2('2025-01-01') }} → 1 იანვარი 2025
{{ date2('2025-02-14') }} → 14 თებერვალი 2025
{{ date2('2025-03-08') }} → 8 მარტი 2025
{{ date2('2025-04-15') }} → 15 აპრილი 2025
{{ date2('2025-05-26') }} → 26 მაისი 2025
{{ date2('2025-06-30') }} → 30 ივნისი 2025
{{ date2('2025-07-04') }} → 4 ივლისი 2025
{{ date2('2025-08-15') }} → 15 აგვისტო 2025
{{ date2('2025-09-01') }} → 1 სექტემბერი 2025
{{ date2('2025-10-16') }} → 16 ოქტომბერი 2025
{{ date2('2025-11-25') }} → 25 ნოემბერი 2025
{{ date2('2025-12-31') }} → 31 დეკემბერი 2025
```

