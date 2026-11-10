# Signature blocks

## Requirements

**Wis. Stat. § 802.05(1)**: every pleading, written motion, and other paper must
be signed by an attorney of record in the attorney's individual name or, if
unrepresented, by the party, and must state the signer's **address, telephone
number, electronic mail address, and state bar number, if any**. An unsigned paper
is stricken unless the omission is corrected promptly after being called to
attention.

**Wis. Stat. § 801.18(12)(a)** (circuit court) and **§ 809.801(12)(a)**
(appellate): an eFiled document requiring the user's signature may bear either
`Electronically signed by [NAME]` or a handwritten signature applied before the
document is imaged. The electronic form belongs where the signature would appear.
For paper parties, § 801.18(12)(h) and § 809.801(12)(h) require a **handwritten
signature**. A typed `/s/` alone is not a substitute. Follow the applicable rules
for third-party signatures and notarization; do not sign for another person.

**Wis. Stat. § 801.18(12)(c)**: each electronically filed document shall bear the
person's name, mailing address, electronic mail address, telephone number, and
state bar number if applicable.

**A draft that is not signed.** `Electronically signed by [NAME]` is one of the two
forms a signature takes on an eFiled document, as stated above. When the supplied draft
or the user says the document is unsigned, or the signer has not yet adopted the text,
do not write a person's name on that line in the text you return. Leave a bracketed
placeholder such as `[signature line: NAME signs here]`, keep any statement of the
draft's unsigned status, and say in the delivery note that only the signer can add the
signature. The builder prints the line from the specification because it cannot know
whether the signer has adopted the text; a file it builds is a draft for the signer to
read and adopt, and the delivery note says so.

---

Sources: [ch. 801](https://docs.legis.wisconsin.gov/statutes/statutes/801.pdf),
[ch. 802](https://docs.legis.wisconsin.gov/statutes/statutes/802.pdf), and
[ch. 809](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf), checked
September 20, 2026. Verify current requirements before filing.

## Default signature-line styling

**`Electronically signed by [Name]` is set in italics.** It stands in for the
handwritten signature, and italicizing it is what distinguishes the signature from
the typed name printed underneath. This is the template's style preference, not a
statutory requirement or a reason by itself to reject another compliant block.

- Italic: the whole line, `Electronically signed by` **and** the name that follows.
- Roman: the typed name on the next line (bold in the attorney block, plain in the
  pro se block), the role line, the bar number, the address, the phone, the email.
- A paper filing needs the actual handwritten signature required above.

The builder does this automatically for both signature styles. If you are hand-
building a document, italicize that one line and nothing else in the block.

---

## Pro se block, when the signer is self-represented

Confirm the actual signer's role before selecting a block. Neither a pro se role
nor attorney status follows from the user's request to draft a document.

Right half of the page, indented **3.0″**. That is what the builder uses; it is the widest indent that holds "Electronically signed by Jane Q. Example" on one line at 12 pt in Century Schoolbook.

```
Dated: March 2, 2026            Electronically signed by Jane Q. Example   <- ITALIC
                                Jane Q. Example
                                Plaintiff, pro se
                                [STREET ADDRESS], [CITY], WI [ZIP]
                                [PHONE]
                                [email@example.com]
```

Variants in the corpus:

- `Dated this ____ day of __________, 2026.` on its own line above
  `Respectfully submitted,`: the more formal shape, used in longer briefs.
- `Petitioner, Pro Se` where the case designates the parties Petitioner and
  Respondent.
- Some older examples use `/s/ [NAME]`; do not copy that into a paper filing as
  a substitute for the required handwritten signature.

Include the telephone number and the other contact information required by
§ 802.05(1). Use placeholders when the user has not supplied those details.

---

## Attorney block, USE ONLY WHEN EXPLICITLY REQUESTED

Do not add an attorney signature block on your own initiative. Do not convert a pro
se filing into an attorney filing. Ask if it is ambiguous who is signing.

**Example firm block:**

**The examples below use placeholder names, bar numbers, addresses, and contact
details. They are illustrations of form, not fill-in values.** Never file a document carrying another lawyer's name,
bar number, or firm; the shipped template `assets/11-motion-attorney-signed` uses
placeholders for exactly that reason. A State Bar number identifies a specific
licensed person and signing with one that is not yours is a serious problem
independent of anything in this skill.

Like the pro se block, the attorney block sits on the **right half of the page**.
The date line is flush left; `Respectfully submitted,` follows it (on the same line
where the date is short enough to leave room, otherwise on its own line, which is
what the builder produces with the long blank-form date); everything below is
indented to **2.75″**.

```
Dated this ____ day of __________, 2026.

Respectfully submitted,

                                     EXAMPLE LAW OFFICE, LLC
                                     d/b/a Example Law

                                     Electronically signed by Alex R. Attorney   <- ITALIC
                                     Alex R. Attorney                             <- bold
                                     State Bar No. 1000000
                                     Attorney for the Defendant, John A. Doe

                                     123 Main Street, Suite 100
                                     Anytown, Wisconsin 54000
                                     (555) 555-0100
                                     attorney@examplefirm.com
```

Order: date line, `Respectfully submitted,`, blank, firm name in **bold caps**,
d/b/a line if applicable, blank, `Electronically signed by [Name]`, name in
**bold**, `State Bar No. [number]`, `Attorney for the [role], [client name]`,
blank, street address, city/state/zip, phone, email. The `Electronically signed by`
line is italic; nothing else in the block is.

**Indent.** The `"indent"` key is honoured for the **attorney** style only; the pro
se block is fixed at 3.0″. 2.75″ is the attorney default because it holds the longest line in the block,
`Attorney for the Defendant, [Client Name]`, on a single line at 12 pt. Pass
`"indent": 3.25` in the signature spec to push it further right when the names are
short. A wrapped `Attorney for` line looks wrong; move the indent rather than
leaving the wrap.

**Spec:**

```json
"signature": {
  "style": "attorney",
  "date": "Dated this ____ day of __________, 2026.",
  "firm": "Example Law Office, LLC",
  "dba": "d/b/a Example Law",
  "name": "Alex R. Attorney",
  "bar_no": "1000000",
  "for_party": "Attorney for the Defendant, John A. Doe",
  "address": "123 Main Street, Suite 100",
  "city_state_zip": "Anytown, Wisconsin 54000",
  "phone": "(555) 555-0100",
  "email": "attorney@examplefirm.com"
}
```

Omit `"date"` and the builder writes `Dated this ____ day of __________, [year].`
from the optional `"year"` key.

**Opposing-counsel form for reference** (a collection firm's block), same
right-side placement, with the firm name above the date line rather than below
`Respectfully submitted,`:

```
                                OPPOSING COUNSEL, P.C.

Dated this ____ day of __________, 2026.
                                Electronically signed by Pat R. Counsel   <- ITALIC
                                Pat R. Counsel, State Bar No. 1000001
                                Attorneys for Defendant, Acme Debt Buyer, LLC
                                456 Example Avenue, Suite 200
                                Anytown, WI 54000
                                Phone No. (555) 555-0200
                                counsel@examplefirm.com
```

---

## What never gets a signature block

**Proposed orders.** "Do not include signature blocks for court officials on your
document. The court will apply it." No `BY THE COURT`, no judge name line, no date
line. Leave a 3-inch blank top margin on page 1 instead.
