# Inventory Line Scroll Arrows

## Description
This module adds smooth horizontal scrolling with left/right navigation arrows to the inventory lines table.

## Features
- **Smooth Scrolling**: Animated horizontal scrolling effect
- **Hover-Activated Arrows**: Navigation arrows appear when you hover over the table
- **Auto-Hide**: Arrows automatically hide when at the beginning/end of the table
- **Modern Design**: Circular arrows with shadow effects
- **Responsive**: Works on different screen sizes

## Installation
1. Copy this module to your addons folder: `gazi/custom_addons/inventory_line_scroll_arrows/`
2. Update the app list in Odoo
3. Install the "Inventory Line Scroll Arrows" module

## Dependencies
- `inventory_request_extension`

## Usage
Once installed, the module automatically adds scroll arrows to the inventory lines table:
- **Left Arrow**: Click to scroll left
- **Right Arrow**: Click to scroll right
- **Hover Effect**: Move your mouse over the table to see the arrows
- **Smooth Animation**: All scrolling is animated smoothly

## Technical Details
- Uses Odoo 18 OWL (Odoo Web Library) framework
- Custom JavaScript renderer extending ListRenderer
- Custom CSS for styling and animations
- Non-intrusive: Only applies to inventory.line model

## Customization
You can adjust the scroll speed by modifying the `scrollAmount` variable in:
```
static/src/js/inventory_line_scroll.js
```

Default: 300px per click

## Author
Your Company

## License
LGPL-3
