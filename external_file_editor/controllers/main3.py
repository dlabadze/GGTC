# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from odoo import fields

_logger = logging.getLogger(__name__)


class ExternalFileEditorController(http.Controller):

    @http.route('/external_file_editor/callback', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def callback(self, **kwargs):
        """
        Callback endpoint for external editor
        Receives edited file and updates approval request

        This endpoint is intentionally tolerant:
        - Works with multi-db by relying on `?db=<dbname>` in the URL.
        - Accepts JSON body (preferred) or form/query parameters.
        - Requires only: token + Document (base64).
        """
        try:
            method = request.httprequest.method

            # Quick sanity check endpoint (browser-friendly)
            if method == 'GET':
                return request.make_json_response({
                    'success': True,
                    'message': 'external_file_editor callback route is reachable',
                    'db': request.db,
                    'params': dict(request.params),
                })

            # POST: accept JSON body or request params
            payload = {}
            raw = request.httprequest.data
            if raw:
                try:
                    payload = json.loads(raw.decode('utf-8'))
                except Exception:
                    payload = {}

            token = payload.get('token') or request.params.get('token') or kwargs.get('token')
            document = payload.get('Document') or request.params.get('Document') or kwargs.get('Document')
            file_name = payload.get('fileName') or request.params.get('fileName') or payload.get('file_name') or request.params.get('file_name')

            _logger.info("=== EXTERNAL FILE EDITOR CALLBACK (POST) ===")
            _logger.info("DB (request.db): %s", request.db)
            _logger.info("Token: %s", token[:20] if token else "None")
            _logger.info("Document length: %s", len(document) if document else 0)
            _logger.info("File name: %s", file_name or "N/A")

            if not token:
                return request.make_json_response({'success': False, 'error': 'Missing token'}, status=400)
            if not document:
                return request.make_json_response({'success': False, 'error': 'Missing Document'}, status=400)

            session = request.env['file.editor.session'].sudo().search([('token', '=', token)], limit=1)
            if not session:
                return request.make_json_response({'success': False, 'error': 'Invalid token'}, status=404)

            # Session validation
            if session.state != 'active':
                return request.make_json_response({'success': False, 'error': f'Session is not active (state={session.state})'}, status=409)

            if session.expire_date and fields.Datetime.now() > session.expire_date:
                session.sudo().write({'state': 'expired'})
                return request.make_json_response({'success': False, 'error': 'Session has expired'}, status=410)

            if not session.approval_request_id:
                return request.make_json_response({'success': False, 'error': 'No approval request linked to session'}, status=500)

            field_name = session.file_field or 'x_studio_file'
            approval_request = session.approval_request_id
            if not hasattr(approval_request, field_name):
                return request.make_json_response({'success': False, 'error': f'Approval request has no field {field_name}'}, status=500)

            _logger.info("Updating approval.request ID=%s field=%s", approval_request.id, field_name)

            # Write as the original session user (but sudo to avoid public-user limitations)
            approval_request.with_user(session.user_id).sudo().write({field_name: document})
            session.sudo().write({'state': 'completed'})

            _logger.info("=== FILE UPDATED SUCCESSFULLY ===")
            return request.make_json_response({
                'success': True,
                'message': 'File updated successfully',
                'approval_request_id': approval_request.id,
                'session_id': session.id,
                'file_field': field_name,
                'file_name': file_name,
            })

        except Exception as e:
            _logger.exception("Error in callback: %s", str(e))
            return request.make_json_response({'success': False, 'error': str(e)}, status=500)
