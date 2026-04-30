# Budgeting Request Decorations Module

This Odoo module adds decorative styling to budgeting request views, highlighting price fields based on specific stage conditions.

## Features

- Adds monetary widget to price fields
- Highlights price fields with green background and white text when in specific stages:
  - ლოჯისტიკის სამსახური (Logistics Service)
  - ფინანსური სამმართველო (Financial Management)
- Configures currency field options for proper monetary display

## Installation

1. Place this module in your Odoo addons directory
2. Update the addons list in Odoo
3. Install the module from the Apps menu

## Dependencies

- `base` - Odoo base module
- `studio_customization` - Studio customization module containing the base view

## Files

- `__manifest__.py` - Module manifest and metadata
- `views/budgeting_request_views.xml` - View modifications
- `__init__.py` - Package initialization files

## Usage

After installation, the budgeting request form will automatically display the enhanced styling for price fields based on the current stage.
