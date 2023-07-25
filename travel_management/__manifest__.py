# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Travel Management',
    'version': '1.1',
    'category': 'Extra tools',
    'depends' : ['base', 'mail', 'uom'],
    'description': '''
    ''',
    'data': [
        'security/ir.model.access.csv',
        'views/travel.xml',
    ],
    'demo': [

    ],
    'installable': True,
    'auto_install':False,
    'license': 'LGPL-3',
    'application': True,
}