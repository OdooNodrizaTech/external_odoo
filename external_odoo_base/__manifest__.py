# -*- coding: utf-8 -*-
{
    'name': 'External Odoo',
    'version': '12.0.1.0.0',    
    'author': 'Odoo Nodriza Tech (ONT)',
    'website': 'https://nodrizatech.com/',
    'category': 'Tools',
    'license': 'AGPL-3',
    'depends': ['base', 'sale', 'utm_websites', 'delivery', 'stock'],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/external_odoo_view.xml',
    ],
    'installable': True,
    'auto_install': False,    
}