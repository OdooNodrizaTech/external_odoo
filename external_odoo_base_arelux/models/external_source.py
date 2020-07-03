# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

class ExternalSource(models.Model):
    _inherit = 'external.source'        
    
    #external_customer
    external_customer_ar_qt_activity_type = fields.Selection(
        [
            ('todocesped', 'Todocesped'),
            ('arelux', 'Arelux'),
            ('evert', 'Evert'),        
        ],
        string='Tipo de actividad', 
        default='arelux'
    )
    external_customer_ar_qt_customer_type = fields.Selection(
        [
            ('particular', 'Particular'),
            ('profesional', 'Profesional'),        
        ], 
        string='Tipo de cliente',
        default='particular'
    )    
    external_customer_res_partner_category_id = fields.Many2one(
        comodel_name='res.partner.category',
        string='Res partner category',
        help='Customer (res partner category)'
    )
    external_customer_res_partner_contact_form = fields.Many2one(
        comodel_name='res.partner.contact.form',
        string='Res partner contact form',
        help='Customer (res partner contact form)'
    )                    