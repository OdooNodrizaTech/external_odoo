# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'External Odoo Base Arelux',
    'version': '10.0.1.0.0',    
    'author': 'Odoo Nodriza Tech (ONT)',
    'website': 'https://nodrizatech.com/',
    'category': 'Tools',
    'license': 'AGPL-3',
    'depends': ['external_odoo_base', 'arelux_partner_questionnaire', 'sale', 'stock', 'shipping_expedition'],
    'data': [
        'views/external_source.xml',
    ],
    'installable': True,
    'auto_install': False,    
}