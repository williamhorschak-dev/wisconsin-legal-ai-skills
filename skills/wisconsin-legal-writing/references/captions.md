# Captions

Use the geometry below when building this repository's default caption. It is a
style template, not a statewide mandate to replace an otherwise compliant caption.
Confirm the actual court, county, party designations, and case number from supplied
records. Required court forms, applicable local rules, and case-specific orders
take precedence; do not assume La Crosse County or a pro se plaintiff.

## Statutory basis

- **Wis. Stat. § 801.09(1)**: the title of the cause must specify the name of the
  court, the county designated as the place of trial, the standardized case
  classification type and code number, and the names and addresses of the parties.
  In practice, after the summons and complaint, filings carry the court/county line,
  the party block, and the case number; the classification code lives on the
  initiating documents and the electronic cover sheet.
- **Wis. Stat. § 802.01(2)(d)**: *every written motion* must include in its caption
  the name of the party seeking relief and a brief description of the type of relief
  sought. `PLAINTIFF'S MOTION TO COMPEL`, not `MOTION TO COMPEL`.
- **Wis. Stat. § 809.81(9)**: appellate captions must carry the full name of each
  party as in the circuit court and designate each party's status in *both* courts
  (`Plaintiff-Appellant`, `Defendant-Respondent`).

---

## A. Default caption, circuit court, pro se (DEFAULT)

This is the default circuit court form. Adapt it to the actual case and signer;
the sample county and parties are illustrative.

```
STATE OF WISCONSIN            CIRCUIT COURT →                LA CROSSE COUNTY
______________________________________________________________________________

JANE Q. EXAMPLE,

                    Plaintiff
                                        Case No. 2025-CV-000123
v.

ACME DEBT BUYER, LLC,

                    Defendant
______________________________________________________________________________

              PLAINTIFF'S BRIEF IN SUPPORT OF MOTION TO COMPEL
______________________________________________________________________________
```

### The file-stamp square

Before the geometry: **page 1 needs a blank 2″ × 2″ square at the top right** for
the court's file stamp, and every page needs a blank ½″ top margin for the
court-applied header. Director of State Courts technical requirements;
Wis. Stat. § 801.18(8), and § 809.801(8)(h) on appeal.

The court line below runs to a **right tab at 6.5″**, so the county text lands
inside that square if the caption starts at the top of the page. The builder
resolves this by setting a ½″ top margin and clearing a 2″ band across the top of
page 1, which is what these documents look like in the filed record once the stamp
is applied. **If you build a caption by hand, leave that space.**

### Exact geometry

| Element | Specification |
|---|---|
| Page | 8.5″ × 11″; left/right margins 1.0″; top/bottom margins 0.95″ |
| Typeface | **Century Schoolbook** (default) or **Times New Roman**, 12 pt (24 half-points). Other rule-compliant user or court styles may be used. |
| Court line | One paragraph. Right tab stop at **9360 twips (6.5″)**. Text: `STATE OF WISCONSIN` + literal spaces + `CIRCUIT COURT` + TAB + `<COUNTY> COUNTY`. Bold is optional; the discovery-response example bolds it, the motions do not. Pick one and keep it consistent within a document. |
| Underline rule | A paragraph with the same right tab at 9360, containing **a single tab character in an underlined run**. This produces a full-width rule. Three of these per caption: under the court line, under the party block, under the title. |
| Party name | Flush left, ALL CAPS, trailing comma: `JANE Q. EXAMPLE,` |
| Party designation | `Plaintiff` / `Defendant`: first-line indent **2160 twips (1.5″)**, initial cap only, no trailing comma |
| Case number | Its own paragraph, first-line indent **5040 twips (3.5″)**: `Case No. 2025-CV-000123`. Placed between the plaintiff designation and the `v.` |
| `v.` | Flush left, lowercase, with the period |
| Blank lines | One empty paragraph after each **party name**. None after a designation line: `Plaintiff` is followed directly by the case-number line, and `Defendant` by the underline rule. Match the diagram above, which is what the builder emits. |
| Title | Centered, **bold**, **14 pt (28 half-points)**, same face as the body, ALL CAPS |
| Body | Justified (`w:jc="both"`), line spacing **360 (1.5 lines)** |

### Case-number format

Both `2025-CV-000123` and `2025CV000123` appear in the corpus. **Prefer
`2025-CV-000123`** in the caption of the body of the document, that is the current
default form. Use the unhyphenated `2025CV000123` when quoting a court-generated
header, an eFiling reference, or another party's document title.

### Counties and courts

| County | Circuit Court | Court of Appeals district |
|---|---|---|
| La Crosse | La Crosse County | **District IV** (Madison) |
| Trempealeau | Trempealeau County | **District III** (Wausau) |
| Jackson | Jackson County | District IV |
| Monroe | Monroe County | District IV |
| Vernon | Vernon County | District IV |
| Buffalo | Buffalo County | District III |
| Eau Claire | Eau Claire County | District III |

Wis. Stat. § 752.11(1). Note the split: La Crosse, Monroe, Vernon, and Jackson go
to Madison; adjacent Trempealeau, Buffalo, and Eau Claire go to Wausau.

### Branches and judges

Use the current docket and assignment order for the assigned judge or branch.
Terms and assignments change, so this template does not maintain a judge roster.
The default caption omits a branch line; retain or include one when a required
form, applicable rule, order, or the user's compliant case caption calls for it.

### Party designation variants

- Civil action: `Plaintiff` / `Defendant`
- Open-records or certiorari proceeding: `Petitioner` / `Respondent`: this is the
  form used in a public-records mandamus action.
- Multiple respondents: `EXAMPLE COUNTY, et al,` then `Respondents`
- **Official-capacity respondents**, the form a public records mandamus takes when
  the custodians are named individually. Each custodian gets a line naming the
  office; the designation line comes after the last one:

```
JANE Q. EXAMPLE,

                    Petitioner
                                        Case No. 2025-CV-000789
v.

EXAMPLE COUNTY,
A. CUSTODIAN, in her official capacity as Records Custodian for the
     Corporation Counsel for Example County,
B. CUSTODIAN, in his official capacity as Records Custodian for the
     Example County Sheriff's Office,
C. CUSTODIAN, in her official capacity as Records Custodian for the Clerk of
     Circuit Court for Example County,

                    Respondents
```

  Name the custodian, not just the authority, when the relief runs against a
  specific custodian's decision. Once the caption is long, later filings in the same
  case may shorten to `EXAMPLE COUNTY, et al,`: but the initiating document
  carries the full list.
- Criminal: `STATE OF WISCONSIN,` / `Plaintiff`: `v.`: `<NAME>,` / `Defendant`

---

## B. Branch line omitted by default

The default template omits a branch number. A branch assignment may change with
reassignment or visiting judges. If a required form, local rule, order, or supplied
compliant caption calls for one, use the current docket assignment; do not remove
it merely to match this template.

The court line goes straight to the rule:

```
STATE OF WISCONSIN            CIRCUIT COURT                 LA CROSSE COUNTY
______________________________________________________________________________
```

Confirm the assigned branch and judge for scheduling and standing orders.
`circuit-court.md` § 11 has county examples that must be checked for the live matter.

---

## C. Attorney/firm caption, two-column table (use only on request)

Firm-standard filings use a borderless 1-row × 2-column table for the party block
instead of the tab-indented block. Left cell holds the parties, right cell holds
the case number.

```
STATE OF WISCONSIN            CIRCUIT COURT               LA CROSSE COUNTY

┌────────────────────────────────────┬──────────────────────────┐
│ STATE OF WISCONSIN,                │ Case No. [CASE NO.]      │
│              Plaintiff,            │                          │
│      v.                            │                          │
│ JOHN A. DOE,                       │                          │
│              Defendant.            │                          │
└────────────────────────────────────┴──────────────────────────┘

     DEFENDANT'S MOTION TO SEVER COUNTS 1–4 AND FOR RELIEF FROM
                        PREJUDICIAL JOINDER
```

Table has no visible borders. Note that in this variant the designations carry a
**trailing comma** (`Plaintiff,`) and the last one carries a period
(`Defendant.`). The title is centered and bold but not underlined; the section
headings below it are centered, bold, and underlined.

Use this only when the user asks for an attorney-signed firm filing.

---

## D. Legacy caption, do not use

Filings through about October 2025 used a right-hand column of close parentheses
beside the party block. Recognize it when reading the old record; do not produce it.

## E. Appellate caption, Court of Appeals

Rule 809.81(9): full circuit court party names, dual designation. Use the caption
**exactly as issued in the Court of Appeals' official notice**: the clerk sets it,
and briefs must match.

```
                    STATE OF WISCONSIN
                    COURT OF APPEALS
                    DISTRICT IV

                    Appeal No. 2026AP000123

JANE Q. EXAMPLE,

                    Petitioner-Appellant,

     v.

EXAMPLE COUNTY,

                    Respondent-Respondent.
```

The cover page adds: the circuit court case number, the circuit court and the name
of the judge appealed from, the title of the document (`BRIEF OF APPELLANT`), and
the name, address, and telephone number of the person filing. Rule 809.19(9). All
Court of Appeals covers are **white**: the old color scheme (blue appellant, red
respondent, gray reply) is obsolete.

---

## F. Letters to the court

Letters take no caption. See `references/letters.md`.
