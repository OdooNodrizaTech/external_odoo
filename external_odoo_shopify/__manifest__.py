# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'External Odoo Shopify',
    'version': '10.0.1.0.0',    
    'author': 'Odoo Nodriza Tech (ONT)',
    'website': 'https://nodrizatech.com/',
    'category': 'Tools',
    'license': 'AGPL-3',
    'depends': ['external_odoo_base', 'stock'],
    'external_dependencies': {
        'python' : ['shopify'],
    },
    'data': [
        'data/ir_cron.xml',
        'views/external_sale_order.xml',
        'views/external_source.xml',
    ],
    'installable': True,
    'auto_install': False,    
}