# Standard court forms come first

Before drafting a circuit court document from a template in this skill, find out whether the
Wisconsin court system publishes a standard form for that filing. This file gives the statutory
text, where the forms are published, and what to do in a session. It lists no forms: the court's
own index is the list, and it changes.

## What the statutes say

<!-- SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED (coordinator check 2026-11-10), U-09: Wis. Stat. § 807.001(1)-(4), https://docs.legis.wisconsin.gov/document/statutes/807.001, and Wis. Stat. § 758.18(1)-(2), https://docs.legis.wisconsin.gov/document/statutes/758.18, both read 2026-11-10 (page banner: updated through 2025 Wis. Act 247). No decision applying either section was read. Second AI review pending. -->

Wis. Stat. § 807.001, quoted in full:

> **(1)** In all civil actions and proceedings in circuit court, the parties and court officials
> shall use the standard court forms adopted by the judicial conference under s. 758.18 (1),
> commencing the date on which the forms are adopted. If an applicable court form has been
> adopted under s. 758.18 (2), that form may be used in lieu of the standard court form.
>
> **(2)** A party or court official may supplement a court form with additional material.
>
> **(3)** A court may not dismiss a case, refuse a filing or strike a pleading for failure of a
> party to use a standard court form under sub. (1) or to follow format rules but shall require
> the party to submit, within 10 days, a corrected form and may impose statutory fees or costs
> or both.
>
> **(4)** If the judicial conference does not create a standard court form for an action or
> pleading undertaken by a party or court official, the party or court official may use a format
> consistent with any statutory or court requirement for the action or pleading.

Wis. Stat. § 758.18(1) directs the judicial conference to adopt the standard forms. Section
758.18(2) lets it adopt forms "created for voluntary use by self-represented litigants in the
circuit court" and requires it to "identify which forms are intended for voluntary use."

Section 807.001 covers civil actions and proceedings in circuit court. Section 758.18(1) points
to s. 971.025(1) for criminal actions; that section was not read for this file.

## Where the forms are published

<!-- SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED (coordinator check 2026-11-10), U-09: the Wisconsin Court System pages "Circuit court forms" (https://www.wicourts.gov/forms1/circuit/index.htm, page dated "Updated: December 19, 2025"), "Mandatory use of court forms" (https://www.wicourts.gov/forms1/circuit/mandatory.htm) and "Self-help law center" (https://www.wicourts.gov/services/public/selfhelp/index.htm, page dated "Updated: September 08, 2026"), each read once on 2026-11-10. These are the court system's descriptions, not statutes or rules. Second AI review pending. -->

- **Circuit court forms:** <https://www.wicourts.gov/forms1/circuit/index.htm>. The page groups
  forms as general, civil, conservatorship, criminal, family, guardianship, juvenile, mental
  commitments, probate, self representation and small claims, and offers a search. It describes
  the statewide forms as required in all circuit courts for civil, criminal, family,
  guardianship, juvenile, mental commitment, probate and small claims cases.
- **Mandatory use of court forms:** <https://www.wicourts.gov/forms1/circuit/mandatory.htm>. The
  court system's answers there say that standard forms cannot be modified, that additional
  pages may be attached, and that the forms indexes show each form's number, revision date,
  statutes, name and a short description.
- **Self-help law center:** <https://www.wicourts.gov/services/public/selfhelp/index.htm>, with
  pages on divorce and family law, small claims, name change, juvenile, probate, restraining
  orders, how the courts work, representing yourself, and appeals. The page says its
  information is not a substitute for legal advice.
- **County forms.** The forms page says county-specific forms may be on a county court's
  website or available from the clerk of circuit court. This skill has no list of them.

In the self representation list read on 2026-11-10, entries for voluntary forms carry the
words "Voluntary form."

## What to do in a session

1. **Ask before drafting.** Ask whether the user has looked for a standard form for this filing.
   If the session can read wicourts.gov, look in the forms index by category or with the
   page's search, and report the form number and revision date exactly as the index shows
   them.
2. **If a standard form exists,** say so and give the page. Do not rebuild the form with
   `build_filing.py`, and do not imitate its layout. Offer to help with the material the user
   will attach to it under § 807.001(2), under a heading that names the form it supplements.
3. **If the index shows no standard form** for the action or pleading, § 807.001(4) is the
   provision that permits "a format consistent with any statutory or court requirement." The
   templates in this skill are for that case.
4. **If nobody has checked,** say in the delivery status that the forms index was not checked.
   Do not say that no form exists.
5. **Never name a form, a form number or a revision date from memory.** Read the index.

## What this file does not do

- It does not choose a form for a person's situation. Which form fits a particular matter can
  be a legal judgment, and nothing here makes it.
- It does not fill in, alter or reproduce a court form.
- It does not say what a court will do when a standard form is not used. Subsection (3) is
  quoted above; no decision applying it was read.
- It does not cover the Court of Appeals, municipal courts or federal courts.
- The builder does not check for a standard form. It builds what its specification describes.
