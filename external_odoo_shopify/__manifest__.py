# -*- coding: utf-8 -*-
{
    'name': 'External Odoo Shopify',
    'version': '10.0.1.0.0',    
    'author': 'Odoo Nodriza Tech (ONT)',
    'website': 'https://nodrizatech.com/',
    'category': 'Tools',
    'license': 'AGPL-3',
    'depends': ['external_odoo_base'],
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