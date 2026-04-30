# -*- coding: utf-8 -*-
from odoo import models
from . import misc_tools


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_rendering_context_docx(self, doc_template):
        """
        Extend the rendering context with custom filters and functions
        """
        # Get the original context from parent
        context = super()._get_rendering_context_docx(doc_template)
        
        # Add custom functions for handling false values, date formatting, and image processing
        context.update({
            'field1': misc_tools.field1,
            'date1': misc_tools.date1,
            'date2': misc_tools.date2,
            'format_value': misc_tools.format_value,
            'get_record': misc_tools.get_record,
            'get_first': misc_tools.get_first,
            'get_last': misc_tools.get_last,
            'join_field': misc_tools.join_field,
            'count_records': misc_tools.count_records,
        })

        render_image = context.get('render_image')
        if render_image:
            def image_display_full(image_data, max_width=None, max_height=None):
                width = float(max_width) if max_width else None
                height = float(max_height) if max_height else None
                return render_image(image_data, width=width, height=height)
            context['image_display_full'] = image_display_full
        
        return context

