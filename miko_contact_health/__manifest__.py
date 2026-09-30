# -*- coding: utf-8 -*-
{
    'name': 'Contact Audit: Email Validation & Duplicate Contacts (Miko)',
    'version': '17.0.1.0.1',
    'summary': 'Email validator and duplicate contact finder, run locally: email verification of address syntax (no external service) and duplicate contacts that share an address, found before they cost you an invoice',
    'description': """
Audits your contacts for the data faults that silently break invoicing, delivery
and follow up: malformed email addresses, contacts sharing an address, and the
fields an invoice cannot be issued without.
""",
    'author': 'Tripster Developers',
    'website': 'https://miko.co.nz/odoo/email-validation',
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
