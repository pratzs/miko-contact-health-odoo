# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .email_check import validate_email, normalise_email, EMAIL_STATUS

# Extra statuses layered on top of the pure address check.
PARTNER_EMAIL_STATUS = EMAIL_STATUS + [('duplicate', 'Shared with another contact')]

# Reported so you can see them, but never counted against a contact. A walk-in
# customer with no email and no phone is normal data, not a defect, and a tool
# that says otherwise gets ignored. Same lesson as services and barcodes in
# Miko Catalog Health.
INFORMATIONAL_FIELDS = [
    ('email', 'Email'),
    ('phone', 'Phone'),
    ('street', 'Street'),
    ('city', 'City'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ch_email_status = fields.Selection(
        PARTNER_EMAIL_STATUS, string='Email Check', compute='_compute_contact_health',
        store=True, index=True,
        help="Result of validating the email address. Checked offline: this module "
             "never contacts a mail server or any outside service.")
    ch_email_detail = fields.Char(
        string='What is wrong', compute='_compute_contact_health', store=True,
        help="Plain explanation of the fault, so it can be corrected without guessing.")
    ch_missing = fields.Char(
        string='Not filled in', compute='_compute_contact_health', store=True,
        help="Fields with no value. Informational: these are never counted as issues.")
    ch_issue_count = fields.Integer(
        string='Issues', compute='_compute_contact_health', store=True, index=True)
    ch_is_healthy = fields.Boolean(
        string='Contact OK', compute='_compute_contact_health', store=True, index=True)

    @api.depends('email', 'phone', 'street', 'city', 'country_id', 'is_company', 'active')
    def _compute_contact_health(self):
        # Duplicate emails have to be resolved across the whole database, not just
        # the records being recomputed, so one query answers it for the batch.
        #
        # Deliberately raw SQL: matching must be case and whitespace insensitive
        # ("Bob@X.com" and "bob@x.com " are the same mailbox), and the ORM cannot
        # express lower(trim(email)) in a domain. It is a read-only SELECT.
        wanted = {}
        for rec in self:
            key = (rec.email or '').strip().lower()
            if key:
                wanted.setdefault(key, []).append(rec.id)

        shared = set()
        if wanted:
            self.env['res.partner'].flush_model() if hasattr(
                self.env['res.partner'], 'flush_model') else self.env['res.partner'].flush()
            self.env.cr.execute("""
                SELECT lower(btrim(email)) AS key, count(*)
                  FROM res_partner
                 WHERE active = true
                   AND email IS NOT NULL
                   AND btrim(email) <> ''
                   AND lower(btrim(email)) IN %s
              GROUP BY lower(btrim(email))
                HAVING count(*) > 1
            """, (tuple(wanted.keys()),))
            shared = {row[0] for row in self.env.cr.fetchall()}

        for partner in self:
            key = (partner.email or '').strip().lower()
            status, detail = validate_email(partner.email)

            # A shared mailbox is reported ahead of anything else, because two
            # contacts on one address is what makes statements go to the wrong
            # person even when the address itself is perfectly valid.
            if key and key in shared:
                status, detail = 'duplicate', _('Another contact uses this same address')

            missing = [label for fname, label in INFORMATIONAL_FIELDS
                       if not partner[fname]]

            # Only genuine breakage counts. An invalid or shared address is
            # unambiguous. A company with no country is too, because it drives
            # tax and reporting. Everything else is informational.
            counted = 0
            if status not in ('ok', 'missing'):
                counted += 1
            if partner.is_company and not partner.country_id:
                counted += 1
                missing.append(_('Country'))

            partner.ch_email_status = status
            partner.ch_email_detail = detail or False
            partner.ch_missing = ', '.join(missing) if missing else False
            partner.ch_issue_count = counted
            partner.ch_is_healthy = counted == 0

    def action_normalise_emails(self):
        """Trim stray spaces and lowercase the domain on the selected contacts.

        Only ever touches whitespace and the domain's case, both of which are
        safe: the local part is left exactly as typed because it is case
        sensitive per the RFC and changing it could route mail elsewhere.
        """
        changed = 0
        for partner in self:
            if not partner.email:
                continue
            tidy = normalise_email(partner.email)
            if tidy != partner.email:
                partner.email = tidy
                changed += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Addresses tidied'),
                'message': _('%(n)s of %(total)s contacts updated.') % {
                    'n': changed, 'total': len(self)},
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def action_contact_health_rescan(self):
        """Recompute across every contact.

        Stored computes only refresh when a dependency changes, so contacts that
        existed before this module was installed need one explicit pass.
        """
        partners = self.search([])
        # Recompute in chunks. Odoo batches its own computes, but this action
        # calls the compute directly on every contact at once, which would put one
        # IN clause the size of the whole address book into Postgres. On a large
        # database that is slow at best and hits the parameter limit at worst.
        CHUNK = 2000
        for start in range(0, len(partners), CHUNK):
            partners[start:start + CHUNK]._compute_contact_health()
        if hasattr(partners, 'flush_recordset'):
            partners.flush_recordset()
        else:  # Odoo 15 and older
            partners.flush()
        bad = len(partners.filtered(lambda p: not p.ch_is_healthy))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contacts scanned'),
                'message': _('%(total)s contacts checked, %(bad)s with issues.') % {
                    'total': len(partners), 'bad': bad},
                'type': 'success',
                'sticky': False,
            },
        }
