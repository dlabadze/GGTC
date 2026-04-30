# -*- coding: utf-8 -*-
import hashlib
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FileEditorSessionMoxsenebiti(models.Model):
    _name = 'file.editor.session.moxsenebiti'
    _description = 'File Editor Session for Moxsenebiti'
    _order = 'create_date desc'

    name = fields.Char('Session Name', compute='_compute_name', store=True)
    hash_code = fields.Char('Hash Code', required=True, index=True, readonly=True)
    token = fields.Char('Token', required=True, index=True, readonly=True)

    # Document information
    moxsenebiti_id = fields.Many2one('moxsenebiti', string='Moxsenebiti', ondelete='cascade')
    file_field = fields.Char('File Field Name', default='word_file')
    file_name = fields.Char('File Name')

    # Session parameters
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    user_login = fields.Char('User Login', compute='_compute_user_login', store=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], default='active', required=True)

    # Callback information
    callback_url = fields.Char('Callback URL', compute='_compute_callback_url', store=True)
    external_editor_url = fields.Char('External Editor URL', default='http://localhost:4706/wordedit')
    database_name = fields.Char('Database Name', compute='_compute_database_name', store=True)

    # Metadata
    expire_date = fields.Datetime('Expiration Date', required=True)

    @api.depends('hash_code')
    def _compute_name(self):
        for record in self:
            record.name = f"Session {record.hash_code[:8] if record.hash_code else 'New'}"

    @api.depends('user_id')
    def _compute_user_login(self):
        for record in self:
            record.user_login = record.user_id.login if record.user_id else False

    @api.depends('token')
    def _compute_callback_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.token:
                dbname = record.database_name or self.env.cr.dbname
                record.callback_url = f"{base_url}/external_file_editor_moxsenebiti/callback"
            else:
                record.callback_url = False

    def _compute_database_name(self):
        for record in self:
            record.database_name = self.env.cr.dbname

    @api.model
    def generate_hash_and_token(self):
        """Generate unique hash code and token for a session"""
        timestamp = str(datetime.now().timestamp())
        random_uuid = str(uuid.uuid4())
        
        # Generate hash code
        hash_input = f"{timestamp}{random_uuid}{self.env.user.id}"
        hash_code = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Generate token
        token = str(uuid.uuid4())
        
        return hash_code, token

    @api.model
    def create_session(self, moxsenebiti_id, file_field='word_file', expiration_hours=24):
        """Create a new file editing session"""
        moxsenebiti = self.env['moxsenebiti'].browse(moxsenebiti_id)
        
        if not moxsenebiti.exists():
            raise UserError(_('Moxsenebiti record not found'))
        
        # Check if file exists
        file_content = getattr(moxsenebiti, file_field, False)
        if not file_content:
            raise UserError(_('No file attached to this moxsenebiti'))
        
        # Generate hash and token
        hash_code, token = self.generate_hash_and_token()
        
        # Calculate expiration date
        expire_date = datetime.now() + timedelta(hours=expiration_hours)
        
        # Get file name (if exists)
        file_name_field = f"{file_field}_filename"
        file_name = getattr(moxsenebiti, file_name_field, 'document.docx')
        
        # Create session
        session = self.create({
            'hash_code': hash_code,
            'token': token,
            'moxsenebiti_id': moxsenebiti_id,
            'file_field': file_field,
            'file_name': file_name,
            'user_id': self.env.user.id,
            'expire_date': expire_date,
            'state': 'active',
        })

        return session
