# Circuit court filings: structure, placement, timing

Where things go, in order, for each document type. Wisconsin circuit courts impose
**no statutory page limit** on briefs, limits come from local rules and from the
§ 802.10 scheduling order, and § 801.18(8)(c) makes those binding on eFiled
documents. Check the county's local rules and the judge's scheduling order before
assuming there is no cap.

---

## 1. Motion

Keep it short. The motion states what you want and why you are entitled to ask;
the argument lives in the accompanying brief.

```
[CAPTION]
[TITLE, party + relief, per § 802.01(2)(d)]

Plaintiff Jane Q. Example, pro se, moves the Court for an Order compelling
Defendant Acme Debt Buyer, LLC ("Acme") to provide complete discovery responses and
production, and for Plaintiff's reasonable expenses incurred in making this
motion, pursuant to Wis. Stat. §§ 804.09 and 804.12(1)(a)–(c), with sanctions
available for noncompliance under Wis. Stat. § 804.12(2). Plaintiff files
contemporaneously a Brief in Support and supporting exhibits identifying the
specific deficiencies, the controlling legal standards, and the relief requested.

[If more than one form of relief, break it out:]
1. [First form of relief, stated as an order the court can sign];
2. In addition or in the alternative, [second form];
3. Granting whatever other relief justice requires. Wis. Stat. § ___.

[Optional, procedural posture / timeliness paragraph, where timing is contested:]
This motion is timely. [Facts establishing timeliness, tied to the deadline that
applies.] The grounds for the motion are set out in the Brief in Support, which is
incorporated into this motion.

[In a CRIMINAL case the equivalent paragraph adds the § 971.31 hooks: "This motion
can be decided without a trial of the general issue. Wis. Stat. § 971.31(1)." Do
not carry those citations into a civil filing; § 971.31 is the criminal
pretrial-motion statute and citing it in a consumer case is a visible error.]

[WHEREFORE clause if the motion stands alone without a brief]

Dated: [date]                   Electronically signed by [NAME]
                                [NAME]
                                Plaintiff, pro se
                                [STREET ADDRESS], [CITY], WI [ZIP]
                                [email@example.com]
```

**Requirements.** Wis. Stat. § 802.01(2)(a): in writing, grounds stated **with
particularity**, and **the relief or order sought**. § 802.01(2)(b): copies of the
records the motion is founded on are served with the notice of motion, except
papers already filed or served, which are referred to by reference.

**Where the argument does NOT go.** Do not put the legal argument in the motion
when a supporting brief accompanies it. One sentence incorporating the brief is
correct. A motion filed without a brief may carry a short ARGUMENT section.

---

## 2. Brief in support / in opposition

```
[CAPTION]
[TITLE]

                            INTRODUCTION
[What this motion is, in two to four paragraphs. First paragraph frames the
dispute in a sentence. Second paragraph states, concretely, the relief requested
and why it is narrow and enforceable. Do not open with a recitation of procedural
history.]

                             BACKGROUND
[or STATEMENT OF FACTS. Chronological, with record cites, (Doc. 43:2). Only the
facts that bear on the issues.]

                          LEGAL STANDARD
[Include only where the standard is contested or non-obvious, summary judgment,
severance, reconsideration, a discretionary standard. Skip it where the standard is
plain from the argument.]

                             ARGUMENT

     I. [Full-sentence proposition, flush left and bold]

          A. [Sub-proposition, flush left, bold, complete sentence.]

               1. [Sub-sub-proposition, flush left, bold.]

     II. [NEXT PROPOSITION]

                            CONCLUSION
WHEREFORE, Plaintiff respectfully requests that the Court enter an order
[specific relief, matching the opening paragraph of the motion word for word
where possible], and granting such other and further relief as the Court deems
just and proper.

Dated: [date]                   [signature block]
```

### Point headings

Write them as **propositions the court could adopt**, not as topic labels.

- Bad: `A. Joinder.`
- Good: `A. Counts 1–4 are misjoined: on the face of the Amended Criminal
  Complaint they satisfy none of the statutory bases for joinder under Wis. Stat.
  § 971.12(1).`

`[DEFAULT STYLE]` Point headings at the `I.`, `A.`, and `1.` levels are flush left,
bold, and sentence case, consistent with the builder. Section labels such as
ARGUMENT are centered, bold, underlined, and capitalized.

### Argument paragraph shape

1. State the rule with its citation.
2. State the sub-rule or the factor list if there is one.
3. Apply it to the facts of this case, naming the record.
4. Deal with the best counter-argument.

Do not restate the standard of review in every section.

---

## 3. Declaration (preferred) or affidavit

**Since March 29, 2024, an unsworn declaration under penalty of false swearing does
the work of a notarized affidavit in Wisconsin.** 2023 Wis. Act 245 rewrote
Wis. Stat. § 887.015 from the *Uniform Unsworn Foreign Declarations Act* into the
*Uniform Unsworn Declarations Act*, and § 887.015(3) now reaches a declarant
"physically located **within or outside** the boundaries of the United States." The
pre-2024 requirement that the declarant affirm he was outside the United States is
gone.

**§ 887.015(4)(a):** "if a law of this state requires or permits use of a sworn
declaration, an unsworn declaration meeting the requirements of this section has the
same effect as a sworn declaration." § 887.015(2) defines "sworn declaration" to
include "a sworn statement, verification, certificate, or **affidavit**."

**Practical effect: no notary.** The circuit court eFiling system converted its
affidavit document types to declaration document types, and the court's own forms
were reissued with the notary block replaced by a § 887.015 declaration. For a pro
se litigant this removes the cost and the scheduling problem of notarization.
**Default to a declaration.**

### The statutory form, § 887.015(6)

The declaration shall be "in substantially the following form":

```
I declare under penalty of false swearing under the law of Wisconsin that the
foregoing is true and correct.

Signed on the ____ day of __________, ____ (year), at __________ (city or other
location, and state or country).

__________________________ (printed name)
__________________________ (signature)
```

Use the actual **city or other location, and state or country**, as the statutory
form provides. Do not copy the court's county as the place of execution.

### Where the declaration substitute does not apply, § 887.015(4)(b)

The declaration route does **not** reach:

1. a deposition;
2. an oath of office;
3. an oath required to be given before a specified official other than a notary;
4. a declaration to be recorded under § 706.06 or § 706.25 or ch. 140, i.e. deeds
   and other recordable real-estate instruments;
5. an oath required under § 853.04, the self-proving affidavit for a will.

These exceptions do not mean that a generic affidavit template satisfies each
listed procedure. Use the particular oath, deposition, instrument, or will form
required for that task. A user may still choose a properly sworn affidavit where
a declaration would also be permitted. Under § 887.015(5), preserve any medium
the governing law requires. The declarant must actually adopt and sign the
statement; a generated signature line is not proof of execution.

Source checked 2026-09-20: [§ 887.015(3)-(6)](https://docs.legis.wisconsin.gov/statutes/statutes/887.pdf).

**In federal court the governing provision is 28 U.S.C. § 1746, not § 887.015**, and
its form differs: "under penalty of perjury under the laws of the United States of
America." Do not carry the Wisconsin form into a federal filing.

### Structure

```
[CAPTION]
DECLARATION OF [NAME] IN SUPPORT OF PLAINTIFF'S MOTION TO COMPEL

Pursuant to Wis. Stat. § 887.015, I declare the following to be true under penalty
of false swearing under the law of Wisconsin.

1. I am the Plaintiff in this action and make this declaration on personal
   knowledge.
2. [One evidentiary fact per numbered paragraph. Facts only, no argument, no legal
   conclusions.]
3. Attached as Exhibit A is a true and correct copy of ___.

Signed on the ____ day of __________, 2026, at [CITY], Wisconsin.

Electronically signed by [NAME]
[NAME]
```

**Content requirements are unchanged.** Wis. Stat. § 802.08(3) still says
"affidavits," and requires personal knowledge and evidentiary facts admissible in
evidence. Copies of referenced papers must be attached and served **if not already
of record**; the current subsection does not say "sworn or certified copies."
§ 887.015(4)(a) is the bridge that
lets a declaration satisfy it. Note that § 802.08 itself was **not** amended, so do
not cite it for the proposition that declarations are allowed; cite § 887.015(4)(a).

**Generic affidavit form**, when a sworn affidavit is appropriate. It does not
replace the specialized forms or procedures covered by (4)(b):

```
STATE OF WISCONSIN    )
                      ) ss.
LA CROSSE COUNTY      )

[NAME], being first duly sworn on oath, deposes and states:
...
Subscribed and sworn to before me this ____ day of __________, 20__.
```

---

## 4. Discovery responses

```
[CAPTION]
PLAINTIFF'S RESPONSE TO DEFENDANT ACME DEBT BUYER, LLC FIRST SET OF DISCOVERY REQUESTS

NOW COMES Plaintiff Jane Q. Example, pro se, and for her Answer to Defendant
Acme Debt Buyer, LLC ("Acme") First set of Discovery Requests to Plaintiff Jane Q.
Example as follows:

                          INTERROGATORIES
                     [centered, bold, underlined]

[Request text, verbatim from the propounding party, as its own paragraph.]

          ANSWER: [tab-indented at 1.5″, bold "ANSWER:" label]

                     REQUESTS FOR PRODUCTION

[Same pattern.]

                    REQUESTS FOR ADMISSION

[Same pattern.]
```

### `[MANDATORY RULE]` Interrogatory answers must be under oath and signed by the person answering

**Wis. Stat. § 804.08(1)(b):**

> "Each interrogatory shall be answered separately and fully in writing under oath,
> unless it is objected to, in which event the reasons for objection shall be stated
> in lieu of an answer. **The answers are to be signed by the person making them, and
> the objections signed by the attorney making them.**"

The **person making the answers** signs and verifies them; counsel cannot verify
the client's facts merely by signing objections. An attorney making objections
signs those objections. For an unrepresented responding party, one properly
executed combined signature and verification can cover that person's responses;
the statute does not require inventing a second signer or an attorney role.

Answers served without the party's verification are defective and can be **stricken**,
with the claim they support dismissed and fees awarded. That is what happened in
*American Transmission Co. v. Ryan*, No. 2005AP1039 (Wis. Ct. App. Sept. 12, 2006),
where counsel filed interrogatory answers that "were not signed by [the party] as
required by statute." **`[NOT CITABLE]` That decision is unpublished and predates
July 1, 2009, so Rule 809.23(3)(a) bars citing it in any Wisconsin court, even for
persuasive value.** It is a cautionary example only. The authority is
§ 804.08(1)(b) itself.

**Since March 29, 2024 the verification needs no notary.** Wis. Stat. § 887.015(4)(a)
gives an unsworn declaration "the same effect as a sworn declaration," and (2)
defines that term to include a "verification." No § 887.015(4)(b) exclusion reaches
interrogatory answers; interrogatories are not depositions.

```
                              VERIFICATION

I, [NAME], am the [Plaintiff/Defendant] in this action. I have read the foregoing
Answers to [PARTY]'s [First] Set of Interrogatories. Pursuant to Wis. Stat.
§ 887.015, I declare under penalty of false swearing under the law of Wisconsin
that the foregoing answers are true and correct to the best of my knowledge,
information, and belief.

Signed on the ____ day of __________, [YEAR], at [CITY], [STATE].

________________________________
[NAME]
```

**Also from § 804.08:** answers or objections are due **30 days** after service, or
**45 days** after service of the summons and complaint on a defendant,
§ 804.08(1)(b); and a party is limited to **25 interrogatories including all
subparts** absent stipulation or court order, § 804.08(1)(am).

### `[MANDATORY RULE]` A timely specific objection is a response; silence is not

**§ 804.08(1)(b)** permits reasons for an interrogatory objection **in lieu of an
answer**. **§ 804.09(2)(b)1.** permits specific grounds for objecting to a production
request, identifying any part objected to. Respond to unobjectionable portions and
make the scope of any withholding clear. A timely objection does not automatically
require a protective-order motion; its sufficiency may be tested by a motion to
compel.

**§ 804.12(4)** addresses failures such as serving no answers **or objections** to
interrogatories, or no written response to a production request. Its final sentence
does not excuse that failure merely because the discovery was objectionable unless
a protective-order application was made. It does not erase the express right to
serve objections. Protective orders under § 804.01(3) remain available where
needed; evasive or incomplete answers are addressed by § 804.12(1)(b).

Sources checked 2026-09-20: [§§ 804.08, 804.09, and 804.12](https://docs.legis.wisconsin.gov/statutes/statutes/804.pdf).

**The objection formula.** Objections follow a fixed shape. **The adjective string in
the first sentence is the weakest part of it** and should be trimmed to the grounds
that actually apply, each tied to something specific about the request. A response
that recites six adjectives and stops is the boilerplate `practice-areas.md` teaches
you to attack:

> Plaintiff objects to Interrogatory No. 5 on the grounds that it is vague,
> ambiguous, grammatically defective, overbroad, compound, and unduly burdensome.
> [One or two sentences saying *why*, specific to this request.] Subject to and
> without waiving these objections, Plaintiff states that [the substantive
> response]. Plaintiff will supplement as required.

Do not force a "subject to and without waiving" formula into every response.
State the specific objection, identify the portion withheld, and answer any
unobjectionable portion. Do not disclose protected material merely to satisfy a
template. A bare refusal without grounds is not a sufficient objection.

Standard closers, used verbatim:
- "Plaintiff reserves the right to supplement this response if additional
  responsive materials are later identified or later come into Plaintiff's
  possession, custody, or control."
- "after a reasonable search, he has identified no responsive documents"
- "already provided, identified, filed in the court record, or otherwise equally
  available to Defendant"

---

## 5. Proposed order

```
[CAPTION]
ORDER GRANTING PETITIONER'S MOTION TO ENLARGE TIME TO RESPOND TO RESPONDENTS'
NOTICE OF MOTION AND MOTION TO CORRECT RECORD ON APPEAL

The Court has reviewed Petitioner Jane Q. Example's Motion to Enlarge Time to
Respond to Respondents' "NOTICE OF MOTION AND MOTION TO CORRECT RECORD ON APPEAL"
(Doc. __). The Court finds good cause shown.

IT IS ORDERED that:

     Petitioner's time to respond to Respondents' "NOTICE OF MOTION AND MOTION TO
     CORRECT RECORD ON APPEAL" (Doc. __) is enlarged.

     Petitioner's response shall be filed on or before [DATE].

[NOTHING FURTHER, no signature block, no date line, no "BY THE COURT"]
```

**Mechanics.**
- File as **.docx**, not PDF, so the court can edit it. Circuit court eFiling
  technical requirements.
- **Blank 3-inch top margin on page 1**, ½-inch on subsequent pages, to leave room
  for the court's signature and stamp.
- **Do not include a signature block for the judge.** "Do not include signature
  blocks for court officials on your document. The court will apply it."
- The system watermarks it "Proposed" on filing; all eNotice parties are notified.
- The title of a proposed order names the outcome, not the request:
  `ORDER GRANTING …`, not `PROPOSED ORDER ON …`.

**The five-day transmittal letter.** There is **no statewide five-day rule** for
submitting proposed orders after a decision, it is local and judge-specific
practice. In Trempealeau County one convention, used by county counsel in a
public-records matter, is a one-page cover letter transmitting the proposed
orders and asking the court to sign if no objection to the *form* is filed within
five days:

> Enclosed for the Court's review and signature are proposed orders for [parties].
> We respectfully request that if the Court approves the form of the orders and if
> [opposing party] does not file an objection to the form of the orders within five
> days, that the Court execute each order.

Two points that matter when you are on the receiving end. The window runs on the
**form** of the order, not its substance, an objection that reargues the merits is
not a form objection and will not be treated as one. And the five days is the
sender's proposal, not a rule; if it is too short, say so in writing immediately
rather than letting it run.
- Findings go in a short recital paragraph before `IT IS ORDERED that:`. Each
  ordered item is its own indented paragraph. Keep every ordered item something the
  clerk could docket without interpretation, dates, not "promptly."

---

## 6. Notice of hearing / notice of motion

Short. Names the motion, the judge, the date, time, and place, and the manner of
appearance. Serve it with the motion.

**In La Crosse County the notice must also state the length of time the court has
allotted, and the allotment must be obtained from the judge's judicial assistant
before the notice goes out. Local Rule 435: "If no length of time is included in the
notice, the matter will not be heard."** Build that call into the workflow: get the
allotment first, then draft. If a notice you receive allots too little time, Rule
435 requires contacting the court and opposing counsel immediately to reschedule.
Trempealeau has no equivalent rule.

**Timing, Wis. Stat. § 801.15(4).** A written motion and the notice of hearing
must be served **not later than 5 days before** the hearing. Supporting affidavits
are served **with** the motion; opposing affidavits may be served up to **one day
before** the hearing.

**Counting, § 801.15.** Count the notice period under (1), including its
short-period exclusions. For notice served by mail, *Strook v. Kedinger*, 2009 WI
App 31, ¶ 26 n.8, applies the three-day addition in (5)(a), producing **eight days
excluding weekends**, not eight calendar days. Also account for legal holidays
under (1) and any statute or order changing the notice period. Read the
[opinion's footnote](https://www.wicourts.gov/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo=35567)
and current rule before calculating the particular motion's deadline.

---

## 7. Certificate of service

Not strictly required for eNotice parties: under **Wis. Stat. § 801.14(4)**, filing
a paper that must be served *is itself* the certification that it was timely served
on all parties required to be served. Under § 801.18(6)(a), the system's notice of
activity is valid and effective service on other users.

Include a separate certificate whenever **any** party is a paper party
(§ 801.18(6)(c): paper parties must be served traditionally) or is served by mail
or email. The default form is a standalone document titled `Certificate of Service`
or `Certificate of Service by Mail`, identifying the documents served, the person
served, the address, the method, and the date.

---

## 8. Motions for reconsideration and relief from judgment

**`[MANDATORY RULE]` § 805.17(3) is NOT a general reconsideration statute. Never
cite it to reconsider a summary judgment ruling, a default judgment, or any
non-final order.** It sits inside § 805.17, captioned "Trial to the court," and
operates on the findings and conclusions § 805.17(2) requires "[i]n all actions
tried upon the facts without a jury." *Teff v. Unity Health Plans Ins. Corp.*, 2003
WI App 115, 265 Wis. 2d 703, 666 N.W.2d 38, following *Continental Casualty Co. v. Milwaukee Metropolitan Sewerage
District*, 175 Wis. 2d 527, 533-34, 499 N.W.2d 282 (Ct. App. 1993), holds that
§ 805.17(3) "did not apply to a motion for reconsideration of a summary judgment."

Three vehicles, and picking the wrong one is a visible error:

| What you are attacking | Vehicle | Deadline |
|---|---|---|
| A **non-final** order (denial of SJ, a discovery ruling, a ruling in limine) | The court's **inherent authority**. No statute. | None by statute: "any time prior to the entry of the final order or judgment." The practical limit is the § 802.10 scheduling order. |
| A **final** judgment or order | **§ 806.07** relief from judgment | Reasonable time; for (1)(a) or (c), **not more than one year** after entry |
| Findings after a **court trial** | **§ 805.17(3)** | **20 days** after entry; deemed denied at 90 days, and the appeal clock then starts at day 90 |

*Teff*, 2003 WI App 115, ¶ 57: a court "has the inherent authority to reconsider a
nonfinal ruling any time prior to the entry of the final order or judgment," citing
*Fritsche v. Ford Motor Credit Co.*, 171 Wis. 2d 280, 293-94, 491 N.W.2d 119
(Ct. App. 1992).

**§ 806.07(1) grounds:** (a) mistake, inadvertence, surprise, or excusable neglect;
(b) newly-discovered evidence entitling a party to a new trial under § 805.15(3);
(c) fraud, misrepresentation, or other misconduct of an adverse party; (d) the
judgment is void; (e) satisfied, released, or discharged; (f) a prior judgment it
rests on was reversed or vacated; (g) no longer equitable to apply prospectively;
(h) any other reason justifying relief.

The one-year outside limit is not universal: § 806.07(2) applies it to (1)(a)
and (c), and directs (1)(b) motions to § 805.16. Identify the asserted ground
before stating its deadline. See the [current § 806.07](https://docs.legis.wisconsin.gov/statutes/statutes/806.pdf).

**The standard for reconsidering a non-final order:** "the movant must present either
newly discovered evidence or establish a manifest error of law or fact."
*Koepsell's Olde Popcorn Wagons, Inc. v. Koepsell's Festival Popcorn Wagons, Ltd.*,
2004 WI App 129, ¶ 44, 275 Wis. 2d 397, 685 N.W.2d 853. Manifest error means "the wholesale disregard,
misapplication, or failure to recognize controlling precedent." Note the standard is
borrowed from federal law (*Oto v. Metropolitan Life Ins. Co.*, 224 F.3d 601, 606
(7th Cir. 2000)); say so when you cite it. And *Koepsell's* forecloses the obvious
misuse: "A party may not use a motion for reconsideration to introduce new evidence
that could have been introduced at the original summary judgment phase."
<!-- SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED (checked 2026-10-24), G-112: Teff reporter citation as printed in Parker v. Wisconsin Patients Compensation Fund, 2009 WI App 42, ¶ 10 (slip op. p. 6), https://www.wicourts.gov/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo=35927; Koepsell's reporter citation as printed in Santiago v. Didion Milling, Inc., No. 2023AP1045, unpublished per curiam, ¶ 18 (Ct. App. Oct. 10, 2024) (slip op. p. 10), https://www.wicourts.gov/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo=860610; both read 2026-10-24. No citator content. -->

**`[MANDATORY RULE]` A reconsideration motion that merely re-argues does not extend
the appeal deadline, and its denial is not separately appealable.** *Silverton
Enterprises, Inc. v. General Casualty Co.*, 143 Wis. 2d 661, 422 N.W.2d 154
(Ct. App. 1988): "No right of appeal exists from an order denying a motion to
reconsider which presents the same issues as those determined in the order or
judgment sought to be reconsidered." And § 806.07(2): a motion under that section
"does not affect the finality of a judgment or suspend its operation." Calendar the
appeal deadline from the original judgment, not from the reconsideration ruling.

A reconsideration brief must identify a **manifest error of law or fact or newly
discovered evidence**. Say which, in the first paragraph. Do not re-argue the
motion.

---

## 9. Enlargement of time

**§ 801.15(2)(a)** is two-tier and the tier drives the brief:

- Motion filed **before** the period expires → **"cause shown"** and just terms.
- Motion filed **after** the period expires → the court may not grant it unless it
  finds the failure to act was the result of **"excusable neglect."**

Say which tier you are in, in the first sentence. A pre-expiration motion that
argues excusable neglect concedes something it did not need to concede.

The 90-day period under § 801.02 for service of the authenticated summons and
complaint **may not be enlarged**. Also check the restrictions in § 801.15(2)(b)-(c)
and the statute governing the particular act; the cause/excusable-neglect tiers
are not permission to enlarge every deadline.

---

## 10. Summary judgment

- **§ 802.08(1)**: move within 8 months of the filing of the summons and
  complaint, or within the time set by the § 802.10 scheduling order.
- **§ 802.08(2)**: unless earlier times are specified in the scheduling order,
  motion served **at least 20 days** before the hearing and opposing affidavits
  served **at least 5 days** before. Apply the governing counting rules.
- Standard: no genuine issue of material fact and the moving party is entitled to
  judgment as a matter of law.
- **§ 802.08(3)**: the adverse party "may not rest upon the mere allegations or
  denials of the pleadings" and must set forth specific facts showing a genuine
  issue for trial.
- § 802.08 sets **no** briefing schedule and **no** page limits. Those come from
  the scheduling order or local rules.

---

## 11. Local rules: what is actually verified

Local rules bind eFiled documents through § 801.18(8)(c) ("including page limits"),
so they have to be checked, not assumed.

If offline PDF copies of the county rules are kept locally (for example the 2025 La
Crosse rules and the Consumer Credit Complaint Checklist), **that does not change
anything below** — they are convenience copies, not a re-verification. Do not treat the
existence of a local PDF as confirmation of anything stated here.

### Trempealeau County

**Source note.** The [county-hosted rules effective November 1, 2019](https://cms9files.revize.com/trempealeaucounty/Document%20Center/Department/Circuit%20Court/Tremp%20Co.%20Local%20Court%20Rules%20-%20Approved%20%28Effective%2011-1-19%29.pdf)
were checked on September 20, 2026 for the Rule 6 summary-judgment procedure,
including the record-supported factual submissions and default absence of oral
argument. This is a source-specific check, not a guarantee against later local
amendments or case-specific orders. Reconfirm the currently operative rules and
each other local proposition below before using it.

Rules effective **November 1, 2019**, seven rules: publication, civil practice,
small claims, family law, forfeitures, summary judgment, media coverage. Confirm
the assigned judge and branch from the current docket rather than a stored roster.

- **No page or word limits on briefs**, dispositive or non-dispositive.
- **No proposed-order deadline** by rule.
- **No meet-and-confer requirement** for discovery motions.
- **Rule 6 governs summary judgment and imposes real drafting requirements.** The
  movant files the motion **with numbered proposed findings of fact, each with
  record citations**, a statement of conclusions of law, and a supporting brief. The
  opponent files response materials with a brief in opposition; the movant **may**
  file a rebuttal brief. The court issues the briefing schedule after the motion and
  supporting brief are served and filed, unless one already exists.
- **Rule 6.VI:** "All motions for summary judgment shall be considered as submitted
  for ruling without oral argument, unless the Court directs otherwise." Do not
  assume a hearing.
- Noncompliance with Rule 6 is "cause for imposing sanctions which may include
  dismissal, contempt, costs, or such other sanctions as the Court may deem
  appropriate."
- **Rule 2:** telephone conferencing "is encouraged" for scheduling and for motions
  not involving evidence. Civil cases are reviewed for service and answer 90 days
  after filing. Continuances require good cause.

### La Crosse County

**Source note.** The content below was originally read off an accessibility
transcript of the county's rules PDF. **On 2026-08-29 a verification pass read
the official `local-court-rules-2025.pdf` (24 pages, complete) against this
section: 26 of 32 assertions confirmed verbatim, 5 corrected (the corrections are
applied below), 1 date left [VERIFY].** The
standing rule is unchanged — re-verify against the official PDF before relying on
any rule in a filing; verification ages.

The 2025 rules are signed "BY THE COURT" by all five La Crosse County circuit judges,
dated November 2025 with the day of the month handwritten, and marked "Approved" by
Scott L. Horne, Chief Judge, Seventh Judicial Administrative District (p. 24). Rule 104
(p. 1) provides that rules "shall be adopted by written order of a majority of La Crosse
County Circuit Judges, subject to approval of the Chief Judge." Official source: the clerk of
circuit court's copy on the county site,
<https://www.lacrossecounty.org/docs/default-source/clerk-of-courts/local-court-rules-2025.pdf>
(a 24-page scan with no text layer, so text search and copy do not work on it).
<!-- SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED (checked 2026-10-24), P-003 and A2-04: signature page p. 24 and Rule 104 p. 1 of the official PDF at the URL above, viewed 2026-10-24; the file fetched that day had the same SHA-256 as the assessment's archived copy. -->
**[VERIFY: the day is handwritten on the signature page and obscured by a
signature stroke; Rule 609(1) carries an internal date of 11/18/25, which post-dates
a November 7 signing. Confirm the operative date against a clean copy or the clerk's
transmittal before citing it.]** Thirteen parts. **Five branches:** Br. 1 Joseph G. Veenstra; Br. 2 Elliott M.
Levine; Br. 3 Mark A. Huesmann; Br. 4 Scott L. Horne (Chief Judge, Seventh Judicial
Administrative District); Br. 5 Gloria L. Doyle.

**Rule 107** sets the frame: the rules "are intended to supplement, not supersede,
state statutes and Supreme Court Rules," and a rule that conflicts "will not be
enforced except to the extent that their partial enforcement would not constitute a
conflict."

#### Rule 435: the notice of hearing must state the time allotted. This one bites.

> "All matters to be set on for any hearing before the court shall include in the
> Notice of Hearing the length of time the Court has allotted to hear the matter.
> This time frame will have been obtained from the appropriate Judge's judicial
> assistant prior to such notice being sent out. ... **If no length of time is
> included in the notice, the matter will not be heard.** Except in unusual
> circumstances no matter will be allowed to proceed past the final time frame
> allotted."

So the sequence is: call the judge's judicial assistant, get a time allotment, then
draft the notice with that allotment in it. A La Crosse notice of hearing that omits
the time is not a defective notice, it is a hearing that does not happen. If you
receive a notice whose allotment is too short, Rule 435 requires you to contact the
court and opposing counsel **immediately** to reschedule.

#### Rule 436: email goes to the judicial assistant, never the judge

> "In order to preserve impartiality and fairness in all judicial proceedings, all
> email correspondence regarding cases before the court shall be addressed and sent
> to the appropriate judge's judicial assistant, and not to the judge directly."

#### Rule 508: consumer credit complaints must follow the county Checklist

> "All complaints concerning consumer credit transactions must follow the guidelines
> and format set forth in the Consumer Credit Complaint Checklist document ... The
> headings and information within the consumer credit complaint **must be structured
> in accordance with the arrangement and organization of the Checklist**. The court
> will use this Checklist in its determination of the sufficiency of all consumer
> credit complaints."

Rule 702 imposes the same requirement in small claims. The Checklist is published at
`lacrossecounty.org/docs/default-source/clerk-of-courts/consumercreditcomplaintchecklist`.
**This is a sufficiency standard, not a formatting suggestion**: the rule says the
court uses the Checklist to decide whether a consumer credit complaint is
sufficient. Read `practice-areas.md` before drafting or attacking one.

#### Civil practice, Part 5

- **Rule 501:** civil cases are reviewed for service and answer **within 145 days**
  of filing; if the case has not reached issue the court initiates dismissal or
  default. (Trempealeau's equivalent is 90 days.)
- **Rule 502:** "A motion for summary judgment shall comply with Wisconsin Statutes
  Sec. 802.08 unless the court scheduling order provides differently." La Crosse has
  **no** local summary judgment procedure of its own, unlike Trempealeau Rule 6.
- **Rule 503:** except in mortgage foreclosures, no notice to defendant is required
  before entry of default judgment in large claims.
- **Rule 505:** at all pretrial matters, counsel must have settlement authority in
  the client's absence or immediate telephonic access to the client.
- **Rule 507:** requests for continuance must be in writing **with the signed
  consent of the parties, not the attorneys**, or made on the record with the
  parties present, and require good cause.

#### Case processing and assignment

**Rule 303:** on consolidation the cases "shall be heard by the judge with the lowest
case number." Note the conflict with Rule 601, the criminal consolidation rule, which
routes to the lowest numbered felony or earliest filing date. Read 303 as civil and
601 as criminal, and confirm before arguing either.

Rules 301 (case-processing time guidelines), 302 (review dates), and 304 (20-minute
attorney voir dire, extension by written motion 15 days before jury selection) exist
but change nothing about how a document is drafted.

#### Small claims, Part 7 (current version effective March 15, 2020)

Directly relevant to any La Crosse consumer collection case.

- **Rule 701:** service by registered, certified, or first class mail is authorized
  in lieu of personal **or substituted** service **within La Crosse County only**,
  except in eviction actions. A **non-resident defendant**, meaning an individual
  residing outside La Crosse County, must be served personally or by substituted
  service, **except in eviction actions**. A mailed summons to an out-of-county
  defendant does not satisfy this rule.
- **Rule 703:** both parties must appear on the return day or default judgment or
  **dismissal with prejudice** follows; if there is more than one plaintiff or
  defendant, **all of them must appear**. A party may appear by proxy under
  Rule 703A, and **a non-resident defendant may appear by answering by mail before
  the Return Date**.
- **Rule 703A:** who may appear — the named party; an attorney for the named party;
  one spouse for another where interests are not adverse; **a guardian for the
  ward**; an authorized employee for a person or corporation; and a person with
  written authorization signed by the named party and expressly referencing the case,
  **at the initial hearing only**. Who may **not**: one roommate for other roommates
  absent Rule 703A(7) written authorization; and **paralegals or other employees of a
  law firm in lieu of a party's attorney, unless the attorney or the law firm is a
  party**.
- **Rule 704:** a written answer is due by **10:00 a.m. on the Return Date** (4:30
  p.m. the Monday after the return date in evictions) or default with prejudice may
  be entered. An answer filed by mail is deemed filed when the clerk receives it,
  not when mailed.
- **Rule 706:** **mediation is required in all small claims cases before a trial
  will be scheduled.** Where both parties are pro se in person, and in all
  evictions, mediation happens on the return date. Otherwise the **plaintiff** must
  request it.
- **Rule 706A:** the plaintiff must schedule mediation within **10 business days**
  of the return day appearance or face dismissal with prejudice; mediation occurs
  within 60 days of the return date.

#### What La Crosse does NOT impose

Confirmed by reading the full rules:

- **No page or word limit on briefs**, dispositive or non-dispositive. The only page
  cap anywhere is Rule 1202's 15-page limit on **fax** filings, which is a
  transmission limit and largely vestigial under mandatory eFiling — **and if a fax
  exceeds 15 pages the party must certify that the assigned judge or court
  commissioner approved the exception**.
- **No briefing schedule by local rule.** It comes from the § 802.10 scheduling
  order.
- **No deadline for submitting a proposed order** after a decision **in civil
  cases**. Proposed-order duties do exist elsewhere and none carries a numeric
  deadline: Rule 605 (appointed criminal counsel prepares the appointment order
  "promptly"), Rule 902 (attorneys prepare and submit the mediation-fee judgment for
  docketing), Rule 905 (GAL fee order).
- **No meet-and-confer requirement** for discovery motions.
- **No courtesy copy requirement**, other than the optional fax courtesy copy under
  Rule 1204, which the judge destroys and does not file.

#### Rules § 11 previously did not mention (verified 2026-08-29 against the official PDF)

Fourteen drafting-relevant rules were absent from this section. The two that would
actually change a filing:

- **Rule 504A(1), p. 7** — *"If a Plaintiff moves for Default or Summary Judgment in
  an owner-occupied residential foreclosure, the supporting Affidavit shall include a
  statement indicating compliance with this rule."* Mandated affidavit content, and a
  defect a defendant can raise.
- **Rule 912, p. 19** — unrepresented parties in divorce **shall use the clerk's pro
  se forms or forms identical in content**. Aimed squarely at this skill's default pro
  se posture; § 11 was silent.

The rest, by part: **Rule 201** (p. 1 — motion to close proceedings requires
**written** notice to court and media coordinator ≥72 hours ahead); **Rule
504(3)–(5)** (p. 6 — foreclosure affidavits must set out the default period and full
amounts, attach the original note and mortgage, and state which of §§ 846.101/.102/
.103 applies); **Rule 601** (p. 8 — consolidation motions must use the county form or
a substantially consistent format); **Rule 608(C)** (p. 10 — remote-appearance
requests by email to the court's designated remote-appearance address); **Rule 609(1)(c)** (p. 10 — felony
substitution in writing within 10 days of arraignment and before any other motion);
**Rules 705/705A** (p. 12 — mediation authority; written authorization must expressly
reference the case to be mediated); **Rule 706** (p. 13 — failure to appear at
mediation: default against defendant, dismissal against plaintiff); **Rule 706A**
(p. 13 — mediation requests by mail deemed filed **on receipt**; "business day"
defined); **Rules 708/708A** (p. 13 — financial-disclosure OSCs, contempt motions and
garnishment objections to the intake judge; service cost added to judgment — live in
consumer collection); **Rule 904** (p. 14 — a verbatim clause required in all marital
settlement agreements and support judgments); **Rule 908(3)(a)** (p. 17 — CAT de novo
motions **must contain** specified verbatim language); **Rules 913/914** (pp. 20–21 —
de novo from the Family Court Commissioner: written motion within 30 days, served ≥5
days before); **Rules 1201/1203** (p. 22 — fax filings only for fee-free papers and
only to the clerk's designated fax number, anything else "will not be filed"; mandatory fax cover page
with five specified items); **Rule 1300** (p. 23 — pro se juvenile guardianship
service and the $350 GAL payment before the filing is accepted).

*Source: the official La Crosse County local court rules PDF (2025), pp. 1–24, read
complete 2026-08-29, at
<https://www.lacrossecounty.org/docs/default-source/clerk-of-courts/local-court-rules-2025.pdf>.*

#### Criminal, Part 6

Out of scope for this skill's default civil/consumer work. If a criminal matter
comes up, the rules that bear on drafting are 609 (case assignment and local
substitution deadlines), 606 (plea agreement cutoffs), 608 (remote appearance), and
601 (consolidation). Read them in the official rules rather than relying on a
summary here.

### Always also check

The § 802.10 scheduling order and the individual judge's standing order. Those set
briefing schedules and, in many courts, brief lengths, and they override the general
practice described here.

---

## How to count a deadline, Wis. Stat. § 801.15(1)

The add-ons get repeated all over this skill; the counting rules were missing. Both
are needed.

**§ 801.15(1)(b), the basic method:**
- **Exclude the day of the act or event** that starts the period. Count from the
  next day.
- **Include the last day**, unless it is a day the clerk of courts office is
  closed. Check the actual court calendar and governing rule, not only weekends.
- **When the period is less than 11 days, Saturdays, Sundays, and legal holidays are
  excluded from the count.** This is the rule most often missed, and it applies to
  the 5-day notice period under § 801.15(4).
- An eFiled document is considered filed on a particular day if the submission is
  completed by **11:59 p.m. central time**, as recorded by the electronic filing
  system, so long as the clerk of court later accepts it on review. That expanded
  time to file does not affect the calculation of time under other statutes, rules,
  and court orders. § 801.18(4)(am).
  <!-- SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED (checked 2026-10-12), L-010: Wis. Stat. § 801.18(4)(am), https://docs.legis.wisconsin.gov/document/statutes/801.18, read 2026-10-12. The former "close of business" gloss is not in § 801.15 and was removed. -->

**For an act due a prescribed period after service, check § 801.15(5):**
- Service by mail: **+3 days**.
- Service by fax, email, or the eFiling system completed **after 5 p.m.**: **+1 day**.

Do not add service days to deadlines triggered by entry of judgment or filing
merely because a related notice was mailed. Motion-hearing notice is a separate
application: *Strook*, ¶ 26 n.8, applies the mail addition to that notice period
as described in § 6 above. Special statutory procedures can supply different
counting rules. State the triggering event, service method and time, court-closure
days, governing case law, and any controlling order when calculating a date.

Source checked 2026-09-20: [§ 801.15](https://docs.legis.wisconsin.gov/statutes/statutes/801.pdf),
official statutes updated through September 4, 2026. Recheck for the live matter.

---

## Timing quick reference

| Event | Deadline | Authority |
|---|---|---|
| Serve motion + notice of hearing | 5 days before hearing | § 801.15(4) |
| Motion-hearing notice by mail | 8 days, applying short-period exclusions and any controlling statute/order | § 801.15(1), (4)-(5); *Strook*, ¶ 26 n.8 |
| Act due a prescribed period after service | Check +3 for mail or +1 for specified electronic service after 5 p.m.; do not apply to every deadline | § 801.15(5) |
| Supporting affidavits | with the motion | § 801.15(4) |
| Opposing affidavits | 1 day before hearing | § 801.15(4) |
| Summary judgment motion | At least 20 days before hearing, unless an earlier time is set by scheduling order | § 802.08(2) |
| SJ opposing affidavits | At least 5 days before hearing, unless an earlier time is set by scheduling order | § 802.08(2) |
| Amend findings **after a court trial** | 20 days after entry | § 805.17(3) |
| Reconsider a **non-final** order | no statutory deadline | inherent authority; *Teff* ¶ 57 |
| Relief from judgment, (1)(a) or (c) | Reasonable time and not more than 1 year; other grounds differ | § 806.07(2) |
| Notice of entry (to shorten appeal clock) | within 21 days of entry | § 806.06(5) |
| Ordinary civil notice of appeal | 90 days after entry; **45 days** if qualifying notice of entry is given within 21 days | § 808.04(1) |
| Cross-appeal | Later of ordinary appeal deadline or 30 days after filing notice of appeal | § 809.10(2)(b) |
| Filing date | filed that day if the eFiling system records the submission complete by 11:59 p.m. CT and the clerk later accepts it; other time-calculation rules unchanged | § 801.18(4)(am) |
