# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Moxsenebiti(models.Model):
    _inherit = 'moxsenebiti'

    def action_edit_file(self):
        """Action to send file to external editor"""
        self.ensure_one()
        
        # Check if file exists
        if not self.word_file:
            raise UserError(_('No file attached to edit'))
        
        # Create editing session
        session = self.env['file.editor.session.moxsenebiti'].create_session(
            moxsenebiti_id=self.id,
            file_field='word_file',
            expiration_hours=24
        )
        
        # Get file name
        file_name = self.word_filename if hasattr(self, 'word_filename') else 'document.docx'
        
        # Return client action to call external editor
        return {
            'type': 'ir.actions.client',
            'tag': 'external_file_editor_moxsenebiti',
            'params': {
                'session_id': session.id,
                'hash_code': session.hash_code,
                'token': session.token,
                'callback_url': session.callback_url,
                'external_editor_url': session.external_editor_url,
                'file_content': self.word_file,  # Base64 encoded file
                'file_name': file_name,
                'db': session.database_name,
                'login': session.user_login,
            }
        }
