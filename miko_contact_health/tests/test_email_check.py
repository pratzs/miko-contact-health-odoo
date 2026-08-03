# -*- coding: utf-8 -*-
"""Contact Health tests.

The failure that would sink this module is flagging an address that works, so the
first class exists purely to prove we do not.
"""
from odoo.tests import TransactionCase, tagged

from ..models.email_check import validate_email, normalise_email


@tagged('post_install', '-at_install')
class TestEmailCheck(TransactionCase):

    # Awkward but entirely valid. Every one of these is a real-world shape.
    VALID = [
        'john@example.com',
        'j@a.co',
        'first.last@example.co.nz',
        'user+tag@gmail.com',
        'user_name@sub.domain.example.org',
        'a1@mail-server.example.com',
        'x@example.technology',
        "o'brien@example.ie",
        "test!#$%&'*+-/=?^_`{|}~@example.com",
        'long.name.with.many.dots@a.b.c.example.museum',
        'IT.Support@Example.COM',
    ]

    INVALID = [
        ('john@@gmail.com', 'multi_at'),
        ('john at example.com', 'whitespace'),
        ('john@example,com', 'comma_domain'),
        ('johnexample.com', 'no_at'),
        ('john@localhost', 'no_domain_dot'),
        ('john@example.c', 'bad_tld'),
        ('john@example.co1', 'bad_tld'),
        ('.john@example.com', 'bad_dots'),
        ('john.@example.com', 'bad_dots'),
        ('john..doe@example.com', 'bad_dots'),
        ('john@-example.com', 'bad_chars'),
        ('john@example..com', 'bad_dots'),
        ('@example.com', 'bad_chars'),
        ('john@', 'bad_chars'),
        ('john doe@example.com', 'whitespace'),
    ]

    def test_working_addresses_are_never_flagged(self):
        for address in self.VALID:
            status, _detail = validate_email(address)
            self.assertEqual(status, 'ok',
                             '%s is a valid address and must not be flagged' % address)

    def test_broken_addresses_are_caught_with_the_right_reason(self):
        for address, expected in self.INVALID:
            status, detail = validate_email(address)
            self.assertEqual(status, expected, 'wrong status for %s' % address)
            self.assertTrue(detail, 'no explanation given for %s' % address)

    def test_empty_is_missing_not_broken(self):
        for value in ('', '   ', False, None):
            self.assertEqual(validate_email(value)[0], 'missing')

    def test_normalise_never_touches_the_local_part(self):
        # The local part is case sensitive per the RFC, so altering it could send
        # mail to a different mailbox.
        self.assertEqual(normalise_email('  John.Doe@EXAMPLE.COM  '), 'John.Doe@example.com')
        self.assertEqual(normalise_email('nonsense'), 'nonsense')


@tagged('post_install', '-at_install')
class TestContactHealth(TransactionCase):

    def _partner(self, name, **vals):
        return self.env['res.partner'].create(dict(name=name, **vals))

    def test_broken_address_is_flagged_and_explained(self):
        p = self._partner('Broken', email='bob@example,com')
        self.assertEqual(p.ch_email_status, 'comma_domain')
        self.assertTrue(p.ch_email_detail)
        self.assertFalse(p.ch_is_healthy)

    def test_good_address_passes(self):
        p = self._partner('Fine', email='bob@example.com')
        self.assertEqual(p.ch_email_status, 'ok')

    def test_no_email_is_reported_but_not_counted(self):
        """A walk-in customer with no email is normal data, not a defect."""
        p = self._partner('Walk in')
        self.assertEqual(p.ch_email_status, 'missing')
        self.assertEqual(p.ch_issue_count, 0)
        self.assertTrue(p.ch_is_healthy)
        self.assertIn('Email', p.ch_missing)

    def test_shared_address_is_flagged_on_both(self):
        a = self._partner('Alice', email='shared@example.com')
        b = self._partner('Bob', email='SHARED@Example.com  ')
        (a | b)._compute_contact_health()
        self.assertEqual(a.ch_email_status, 'duplicate')
        self.assertEqual(b.ch_email_status, 'duplicate',
                         'matching must ignore case and surrounding spaces')

    def test_company_without_country_is_counted(self):
        c = self._partner('Acme Ltd', is_company=True, email='hi@acme.com')
        self.assertFalse(c.ch_is_healthy)
        self.assertIn('Country', c.ch_missing)

    def test_person_without_country_is_not_counted(self):
        p = self._partner('A Person', is_company=False, email='hi@example.com')
        self.assertTrue(p.ch_is_healthy)

    def test_status_clears_when_the_address_is_corrected(self):
        p = self._partner('Fixable', email='bob@example,com')
        self.assertEqual(p.ch_email_status, 'comma_domain')
        p.email = 'bob@example.com'
        self.assertEqual(p.ch_email_status, 'ok')
        self.assertTrue(p.ch_is_healthy)

    def test_tidy_action_only_changes_whitespace_and_domain_case(self):
        p = self._partner('Messy', email='  Bob.Smith@EXAMPLE.COM ')
        p.action_normalise_emails()
        self.assertEqual(p.email, 'Bob.Smith@example.com')

    def test_rescan_returns_a_notification(self):
        action = self.env['res.partner'].action_contact_health_rescan()
        self.assertEqual(action['tag'], 'display_notification')
