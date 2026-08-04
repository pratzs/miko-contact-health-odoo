# Miko Contact Health for Odoo

Audits contacts for the data faults that silently break invoicing and follow up:
email addresses that cannot receive mail, one mailbox shared by two contacts, and
the fields an invoice cannot be issued without.

| | |
|---|---|
| Series | 16.0, 17.0, 18.0, 19.0 (20.0 on release) |
| Price | USD 19, licence OPL-1 |
| Depends | `base` only |
| Tests | 13 per series, 4/4 certified |
| Category | Sales/CRM |
| Colour | Miko mark in wine `#C0708C` to `#8E2F4F` |

## Why it exists

Odoo will store `john@@gmail,com` without a word of complaint. Nothing warns you,
the invoice sends, the log says sent, and the customer never hears from you.

## What makes it trustworthy

Flagging a working address is the failure that would sink this, so the checks are
biased hard against it. The shipped test suite proves it: **11 awkward but valid
addresses produce zero false positives** (plus addressing, apostrophes, two-part
country domains, long modern TLDs, hyphens and subdomains), and **15 broken ones
each return the correct specific reason**.

Deliberately never counted, following the services-and-barcodes lesson from Catalog
Health: a contact with no email, no phone or no address. A walk-in customer is
normal data, not a defect.

**No network access of any kind.** No DNS, no test message, no verification service,
no API key. Validation is arithmetic on a string, so it works on an Odoo with no
outbound internet at all.

## Layout and release cycle

Identical to `Apps/miko-catalog-health-odoo`. Source of truth is
`miko_contact_health/`; `build/` and `publish-repo/` are generated.

```bash
cd _dev && python3 build_versions.py     # regenerate all series
```

Certify every series before pushing, never after. See
`Apps/miko-catalog-health-odoo/PUBLISHING.md` for the full store runbook: it
applies unchanged.

## The demo GIF

`_dev/render/make_gif.py` drives headless Chrome over CDP and captures real frames
of the real module: audit, filter to unusable addresses, correct one through the
ORM, watch it leave the list. Nothing is mocked. It restores the demo data
afterwards so it can be rebuilt identically.

```bash
CH_ACTION=<action id> ~/.claude/skills/.imgvenv/bin/python3 _dev/render/make_gif.py
```

Keep it small. It is palette-quantised to 128 colours at 900px wide, which lands
around 160 KB.

## Gotchas specific to this app

- **Both apps' `_dev` folders make the same Docker project name**, so they share one
  Postgres. With many databases present Odoo serves the browser whichever it likes,
  which once produced screenshots of Units & Packagings. Run the screenshot
  container with `--db-filter='^shots$'` to pin it.
- **A reload resets the search facets** back to the action default. The GIF script
  re-applies the filter after the reload, or the "it left the list" frame shows the
  whole audit instead.
