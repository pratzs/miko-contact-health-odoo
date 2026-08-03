# -*- coding: utf-8 -*-
"""Email address validation, done offline and biased against false positives.

An address that cannot receive mail is invisible until an invoice bounces, and by
then the customer is already annoyed and the ledger already says "sent". Odoo does
almost no validation here: it will store `john@@gmail,com` without complaint.

Two rules shape everything below.

**Never touch the network.** No DNS, no SMTP probe, no third-party API. A module
that phones out is a module nobody can install on a locked-down ERP, and it turns
a data audit into a data leak. Everything here is arithmetic on a string.

**A false positive is worse than a miss.** Flagging a working address makes the
merchant distrust the whole audit, and they only have to catch us wrong once.
So anything merely unusual is allowed: plus addressing, subdomains, long modern
TLDs, underscores, hyphens, and single-character local parts are all valid and
are deliberately not reported.
"""

# Longest real TLD in use is well under this; the cap only stops absurd input.
MAX_LOCAL = 64
MAX_TOTAL = 254

EMAIL_STATUS = [
    ('ok', 'Valid'),
    ('missing', 'Missing'),
    ('no_at', 'No @ sign'),
    ('multi_at', 'More than one @'),
    ('whitespace', 'Contains a space'),
    ('comma_domain', 'Comma instead of a dot'),
    ('no_domain_dot', 'Domain has no dot'),
    ('bad_dots', 'Misplaced dots'),
    ('bad_tld', 'Suspicious ending'),
    ('bad_chars', 'Illegal characters'),
    ('too_long', 'Too long'),
]

# Characters RFC 5322 permits unquoted in the local part. Deliberately generous.
LOCAL_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "!#$%&'*+-/=?^_`{|}~."
)
DOMAIN_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-."
)


def validate_email(address):
    """Validate an email address.

    Returns (status, detail) where status is one of EMAIL_STATUS and detail is a
    short human explanation, or None when there is nothing to add.
    """
    if not address:
        return 'missing', None

    raw = address
    value = raw.strip()
    if not value:
        return 'missing', None

    # A leading or trailing space is a paste artefact, not a fault in the address
    # itself, so it is corrected silently rather than reported.
    if len(value) > MAX_TOTAL:
        return 'too_long', 'Longer than %d characters' % MAX_TOTAL

    if any(ch.isspace() for ch in value):
        return 'whitespace', 'An address cannot contain a space'

    at_count = value.count('@')
    if at_count == 0:
        return 'no_at', 'No @ sign'
    if at_count > 1:
        return 'multi_at', 'Contains %d @ signs' % at_count

    local, domain = value.rsplit('@', 1)

    if not local:
        return 'bad_chars', 'Nothing before the @'
    if len(local) > MAX_LOCAL:
        return 'too_long', 'The part before the @ is longer than %d characters' % MAX_LOCAL
    if not domain:
        return 'bad_chars', 'Nothing after the @'

    # A comma where the dot should be is one of the most common real typos and
    # would otherwise be reported only as "no dot", which hides the actual fix.
    if ',' in domain:
        return 'comma_domain', 'Looks like a comma was typed instead of a dot'

    bad_local = set(local) - LOCAL_ALLOWED
    if bad_local:
        return 'bad_chars', 'Illegal character before the @: %s' % ''.join(sorted(bad_local))
    if local.startswith('.') or local.endswith('.') or '..' in local:
        return 'bad_dots', 'Misplaced dot before the @'

    bad_domain = set(domain) - DOMAIN_ALLOWED
    if bad_domain:
        return 'bad_chars', 'Illegal character in the domain: %s' % ''.join(sorted(bad_domain))

    if '.' not in domain:
        return 'no_domain_dot', 'The domain has no dot, so it cannot resolve'
    if domain.startswith('.') or domain.endswith('.') or '..' in domain:
        return 'bad_dots', 'Misplaced dot in the domain'
    if domain.startswith('-') or domain.endswith('-'):
        return 'bad_chars', 'The domain cannot start or end with a hyphen'

    labels = domain.split('.')
    for label in labels:
        if not label:
            return 'bad_dots', 'Empty part in the domain'
        if label.startswith('-') or label.endswith('-'):
            return 'bad_chars', 'A domain part cannot start or end with a hyphen'

    tld = labels[-1]
    # Every real TLD is at least two letters and contains no digits. This is the
    # check that catches "example.c" and "example.co1".
    if len(tld) < 2:
        return 'bad_tld', 'The ending "%s" is too short to be a real domain' % tld
    if not tld.isalpha():
        return 'bad_tld', 'The ending "%s" is not a real domain ending' % tld

    return 'ok', None


def normalise_email(address):
    """The address as it should be stored: trimmed, domain lowercased.

    The local part is left alone on purpose. It is case sensitive per the RFC, and
    silently altering it could route mail somewhere else.
    """
    if not address:
        return address
    value = address.strip()
    if value.count('@') != 1:
        return value
    local, domain = value.rsplit('@', 1)
    return '%s@%s' % (local, domain.lower())
