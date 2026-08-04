# -*- coding: utf-8 -*-
{
    'name': 'Email Validation & Duplicate Contacts (Miko)',
    'version': '16.0.1.0.0',
    'summary': 'Find unusable email addresses and duplicate contacts before they cost you an invoice',
    'description': """
Audits your contacts for the data faults that silently break invoicing, delivery
and follow up: malformed email addresses, contacts sharing an address, and the
fields an invoice cannot be issued without.
""",
    'author': 'Tripster Developers',
    'website': 'https://tripsterdevelopers.com/odoo/',
    'category': 'Sales/CRM',
    'license': 'OPL-1',
    'depends': ['base'],
    'data': [
        'views/miko_contact_health_views.xml',
    ],
    'price': 19.00,
    'currency': 'USD',
    'images': ['images/banner.gif', 'images/banner.png'],
    'application': True,
    'installable': True,
    'support': 'support@tripsterdevelopers.com',
}
