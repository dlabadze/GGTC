# Alnas DOCX Extension

A comprehensive Odoo module that extends document generation capabilities with custom utility functions for handling dates, fields, and images in DOCX templates.

## Features

### 📅 Date Formatting
- **Standard Date Format**: Convert dates to `dd/mm/yyyy` format
- **Georgian Date Format**: Format dates with Georgian month names
- **Multiple Format Options**: Full date, short date, or month-year only

### 🖼️ Image Processing
- **Full Image Display**: Display complete images in DOCX templates
- **Automatic Resizing**: Optional max width/height with aspect ratio preservation
- **Binary Field Support**: Works directly with Odoo binary field data
- **Format Conversion**: Automatic format handling and optimization

### 🔧 Field Processing
- **False Value Handling**: Convert False values to empty strings
- **Universal Formatting**: Handle any field type safely
- **Type Safety**: Robust error handling for all functions

## Installation

1. Copy the module to your Odoo addons directory
2. Update the module list in Odoo
3. Install the `alnas_docx_extension` module

## Usage in DOCX Templates

### Basic Field Handling
```jinja2
<!-- Handle False values safely -->
{{ field1(record.name) }}
{{ field1(record.description) }}

<!-- Universal field formatting -->
{{ format_value(record.any_field) }}
```

### Date Formatting
```jinja2
<!-- Standard date format -->
{{ date1(record.create_date) }}              <!-- Output: 15/03/2024 -->

<!-- Georgian date format -->
{{ date2(record.create_date) }}              <!-- Output: 15 მარტი 2024 -->
{{ date2(record.create_date, 'short') }}     <!-- Output: 15 მარტი -->
{{ date2(record.create_date, 'month_year') }} <!-- Output: მარტი 2024 -->
```

### Image Processing
```jinja2
<!-- Display full image (original size) -->
{{ image_display_full(record.logo) }}

<!-- Display image with max width constraint (aspect ratio preserved) -->
{{ image_display_full(record.logo, 800) }}

<!-- Display image with max height constraint -->
{{ image_display_full(record.logo, None, 600) }}

<!-- Display image with max width and height (whichever is more restrictive) -->
{{ image_display_full(record.logo, 1200, 800) }}
```

### Conditional Usage
```jinja2
<!-- Display image only if it exists -->
{% if record.logo %}
    {{ image_display_full(record.logo, 300) }}
{% endif %}

<!-- Safe field display -->
{% if field1(record.company_id.name) %}
    Company: {{ field1(record.company_id.name) }}
{% endif %}
```

### Complex Examples
```jinja2
<!-- Document header with formatted data -->
Document created on {{ date2(record.create_date) }}
Company: {{ field1(record.company_id.name) }}

{% if record.logo %}
    {{ image_display_full(record.logo, 200) }}
{% endif %}

<!-- Table with images and formatted dates -->
<table>
    <tr>
        <td>Image</td>
        <td>Date</td>
        <td>Description</td>
    </tr>
    {% for line in record.line_ids %}
    <tr>
        <td>{{ image_display_full(line.image, 150) }}</td>
        <td>{{ date1(line.date) }}</td>
        <td>{{ field1(line.description) }}</td>
    </tr>
    {% endfor %}
</table>
```

## Available Functions

### Field Processing
- **`field1(value)`**: Convert False values to empty string
- **`format_value(value)`**: Universal value formatter

### Date Formatting
- **`date1(date_value)`**: Format date as `dd/mm/yyyy`
- **`date2(date_value, format_type)`**: Format date with Georgian months
  - `format_type` options: `'full'`, `'short'`, `'month_year'`

### Image Processing
- **`image_display_full(image_data, max_width=None, max_height=None)`**: Display complete image with optional resizing
  - `image_data`: Binary field image data (bytes from Odoo)
  - `max_width`: Optional maximum width in pixels
  - `max_height`: Optional maximum height in pixels
  - Returns base64 encoded image data ready for DOCX templates
  - Automatically preserves aspect ratio when resizing

## Georgian Month Names

The module includes support for Georgian month names:
- იანვარი (January)
- თებერვალი (February)
- მარტი (March)
- აპრილი (April)
- მაისი (May)
- ივნისი (June)
- ივლისი (July)
- აგვისტო (August)
- სექტემბერი (September)
- ოქტომბერი (October)
- ნოემბერი (November)
- დეკემბერი (December)

## Python Usage

You can also use these functions in Python code:

```python
from odoo.addons.alnas_docx_extension.models.misc_tools import (
    image_display_full, date2, field1
)

# Display image with resizing
image_data = image_display_full(record.logo, max_width=800)

# Format date with Georgian months
formatted_date = date2(record.create_date, 'full')

# Handle field safely
safe_value = field1(record.description)
```

## Error Handling

All functions include comprehensive error handling:
- **Safe Defaults**: Return appropriate defaults (empty string) for invalid inputs
- **Type Safety**: Handle different input types gracefully
- **Exception Handling**: Catch and handle all exceptions silently

## Dependencies

- **PIL (Pillow)**: For image processing and dimension extraction
- **Python Standard Library**: datetime, base64, io modules

## Technical Details

### Image Processing
- Works directly with Odoo binary field data (bytes)
- Handles both binary and base64 string input formats
- Uses PIL (Python Imaging Library) for image processing
- Supports common image formats (JPEG, PNG, GIF, etc.)
- Automatic aspect ratio preservation when resizing
- Safe error handling - returns empty string on errors

### Date Processing
- Supports datetime, date objects, and string inputs
- Handles multiple date formats automatically
- Georgian month names are hardcoded for consistency
- Timezone-aware processing

### Field Processing
- Handles Odoo's False values properly
- Type-safe conversion and formatting
- Maintains data integrity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This module is licensed under the LGPL-3 license.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation for common solutions

## Changelog

### Version 1.2.0
- Simplified image processing to single comprehensive function
- Replaced multiple image functions with `image_display_full()`
- Added automatic resizing with aspect ratio preservation
- Enhanced binary field support
- Improved error handling
- Updated documentation

### Version 1.1.0
- Added image processing functions
- Added image dimension extraction
- Added image format detection
- Added file size information
- Enhanced documentation with image examples

### Version 1.0.0
- Initial release
- Added date formatting functions
- Added field handling utilities
- Added Georgian month name support
- Added comprehensive documentation

---

**Note**: This module extends Odoo's document generation capabilities and is designed to work seamlessly with existing DOCX template functionality.