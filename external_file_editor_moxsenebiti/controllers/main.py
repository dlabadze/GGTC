# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ExternalFileEditorMoxsenebitiController(http.Controller):

    @http.route('/external_file_editor_moxsenebiti/callback', type='json', auth='public', methods=['POST'], csrf=False)
    def callback(self, **kwargs):
        """
        Callback endpoint for external editor (Moxsenebiti)
        Receives edited file and updates moxsenebiti record
        
        Expected payload:
        {
            "db": "database_name",
            "login": "user_login",
            "password": "user_password",
            "token": "session_token",
            "Document": "base64_encoded_file"
        }
        """
        # Get parameters
        db = kwargs.get('db')
        login = kwargs.get('login')
        password = kwargs.get('password')
        token = kwargs.get('token')
        Document = kwargs.get('Document')
        
        try:
            _logger.info("=== MOXSENEBITI CALLBACK RECEIVED ===")
            _logger.info("Database: %s", db)
            _logger.info("Login: %s", login)
            _logger.info("Token: %s", token[:20] if token else "None")
            _logger.info("Document length: %s", len(Document) if Document else 0)
            
            # Validate required authentication fields
            if not all([db, login, password]):
                _logger.error("Missing authentication fields")
                return {
                    'success': False,
                    'error': 'Missing required fields: db, login, password'
                }
            
            # Authenticate user
            try:
                uid = request.session.authenticate(db, {
                    'login': login,
                    'password': password,
                    'type': 'password'
                })
                if not uid:
                    _logger.error("Authentication failed for user: %s", login)
                    return {
                        'success': False,
                        'error': 'Authentication failed'
                    }
                _logger.info("User authenticated successfully: %s (UID: %s)", login, uid)
            except Exception as auth_error:
                _logger.exception("Authentication error: %s", str(auth_error))
                return {
                    'success': False,
                    'error': f'Authentication error: {str(auth_error)}'
                }
            
            # Validate file data
            if not token:
                _logger.error("Missing token")
                return {'success': False, 'error': 'Missing token'}
            
            if not Document:
                _logger.error("Missing Document")
                return {'success': False, 'error': 'Missing Document'}
            
            # Find active session by token
            session = request.env['file.editor.session.moxsenebiti'].sudo().search([
                ('token', '=', token),
                ('state', '=', 'active')
            ], limit=1)
            
            if not session:
                _logger.error("Invalid token: %s", token)
                return {'success': False, 'error': 'Invalid or inactive session'}
            
            # Update file in moxsenebiti
            if not session.moxsenebiti_id:
                _logger.error("No moxsenebiti record found")
                return {'success': False, 'error': 'No moxsenebiti record found'}
            
            _logger.info("Updating moxsenebiti ID: %s", session.moxsenebiti_id.id)
            
            # Write the new file content
            session.moxsenebiti_id.sudo().write({
                'word_file': Document
            })
            
            # Mark session as completed
            session.sudo().write({'state': 'completed'})
            
            _logger.info("=== MOXSENEBITI FILE UPDATED SUCCESSFULLY ===")
            
            return {
                'success': True,
                'message': 'File updated successfully',
                'moxsenebiti_id': session.moxsenebiti_id.id,
                'session_id': session.id
            }
            
        except Exception as e:
            _logger.exception("Error in moxsenebiti callback: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }
