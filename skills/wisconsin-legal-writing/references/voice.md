# Voice: writing that reads as written by the signer

A hybrid of the general `humanizer` skill and this skill's legal conventions. The
two conflict in specific places, and applying the humanizer straight to a brief
produces a worse filing. This file says which of its rules apply, which change, and
which are off.

These are editable style defaults. Follow the user's requested voice and supplied
examples where they are consistent with the law, accuracy, and the intended
audience. Do not infer the signer's identity, role, or personal writing habits from
this repository. Style markers are not reliable proof of who or what wrote a text.

---

## 1. What the goal is, and what it is not

**The goal:** a filing that reads as though the person signing it wrote it. That is
a credibility question with a real audience. A judge who feels a brief was
assembled rather than written discounts it, the same way a judge discounts a
kitchen-sink argument or an overclaimed case.

**Not the goal: beating an AI detector.** Chasing a detector score is the wrong
target for three reasons.

1. **Detectors are unreliable on legal writing specifically.** Briefs are formulaic
   by design. Fixed openers, statutory recitals, parallel headings, standard relief
   language, and a controlled vocabulary are what the genre requires. Those are the
   same features detectors score as machine-generated, so a well-drafted human brief
   often scores high. A score is not evidence.
2. **Optimizing against a detector damages the writing.** The edits that lower a
   score, breaking up parallel structure, varying formulas for the sake of variety,
   introducing casual register, all make a brief worse on the dimension that
   actually matters.
3. **It aims at the wrong problem.** The reason AI-drafted legal writing gets
   noticed is rarely a stylistic tell. It is a fabricated citation, a case that does
   not say what it is cited for, a rule that was repealed, or a fact with no record
   support. Those are caught by cite-checking, not by editing prose. See Rule zero
   in SKILL.md.

So: write in the signer's voice because it makes the filing better. Do not edit to
defeat a tool.

## 2. Disclosure, which is a separate question

Whether AI assistance must be disclosed is not a style question and is not answered
by how the prose reads.

The [official docket for petition 26-02](https://www.wicourts.gov/scrules/pending/2602.htm)
listed the proposed AI rule as pending when checked September 20, 2026. As checked
October 12, 2026, the docket lists a letter from the petitioner requesting withdrawal,
dated September 28 and received September 30, 2026, and its court orders section
shows no order. A petition is not an adopted rule. This file does not maintain a
verified statewide or county
inventory of AI disclosure requirements. Check current court rules, any effective
orders, and the actual judge's requirements; do not infer an exemption from an
omitted county or from the pending status of one proposal.
<!-- DRAFT FOR LEGAL REVIEW (2026-10-12), L-009: Rule Petition 26-02 docket, https://www.wicourts.gov/scrules/pending/2602.htm (entry "Sep 30, 2026, Letter from Petitioner Withdrawing Petition"; no entry under court orders), and the letter, https://www.wicourts.gov/supreme/docs/2602petitionerletter.pdf, p. 1 (dated September 28, 2026; clerk's received stamp September 30, 2026); read 2026-10-12. -->

**What to do:**

- **Check the current local rules and the judge's standing order before filing**, in
  any county. This belongs in the same check as page limits. A disclosure rule you
  did not know about is not excused by not knowing.
- **The certification does not change either way.** Wis. Stat. § 802.05(2) says that
  by presenting a paper, the signer certifies that the legal contentions are
  warranted and the factual contentions have evidentiary support, after an inquiry
  reasonable under the circumstances. That obligation attaches to the signer
  regardless of what drafted it, and it is the reason cite-checking is not optional.
  Subsections (1) to (3) of § 802.05 do not apply to disclosures and discovery
  requests, responses, objections, and motions that are subject to ss. 804.01 to
  804.12. § 802.05(5).
  <!-- DRAFT FOR LEGAL REVIEW (2026-10-12), L-011: Wis. Stat. § 802.05(5), https://docs.legis.wisconsin.gov/document/statutes/802.05, read 2026-10-12. -->
- **If asked, answer honestly.** Do not construct a filing so as to make a truthful
  answer harder to give.

## 3. What actually makes legal writing read as machine-generated

These are the legal-specific tells. The general humanizer list does not catch most
of them.

**Uniformity where a human would be uneven.**
- Every paragraph the same length. Real briefs have a two-line paragraph next to a
  twelve-line one, because some points need more room than others.
- Every argument section the same shape and roughly the same size, when the
  arguments are not equally strong. A human spends four pages on the winner and half
  a page on the fallback.
- Every case given the same treatment: cite, parenthetical, one sentence of
  application. A human quotes one case at length because it is the case, and
  disposes of three others in a single string.

**Over-signposting.** "First... Second... Third..." applied to everything, including
lists that do not need enumerating. Roadmap paragraphs announcing what the brief
will argue before arguing it. "As discussed above" and "as set forth below" on every
cross-reference. One roadmap in a long brief is useful; four is a tell.

**Symmetry that the record does not support.** Two arguments given equal weight when
one is much stronger. A "on the other hand" for every "on the one hand." Balanced
treatment of the opponent's position where the actual answer is that it fails.

**Hedged conclusions.** "Plaintiff respectfully submits that it would appear that
the better view may be that..." A brief asserts. Hedge the standard, not the
conclusion.

**Absent procedural texture.** (**Read Rule zero in SKILL.md before acting on this
one. Keeping the user's real dates and document numbers is the point; inventing
plausible ones is the worst thing this skill could cause.** If the detail is not in
front of you, leave a bracket.) Real filings are full of specific, slightly awkward
particulars: a document number, an exact date, the name of the person who sent an
email, the fact that a response was served at 4:52 p.m. Generated prose smooths
these away into "Defendant subsequently responded." The texture is what makes a
brief sound like it came from a case rather than from a template.

**A vocabulary that is too even.** No writer uses a perfectly controlled register
for nine pages. Real briefs have a blunt sentence in the middle of a formal
paragraph, because the writer got to the point that annoys them.

**Generic parentheticals.** `(holding that joinder was improper)` for every case,
where a human writes `(sexual assault joined with the defendant's attempt to bribe
the same victim into dropping that charge)` because the facts are the point.

**Missing a supplied writer's familiar formulas.** Section 7 explains how to
preserve them when useful and legally accurate.

## 4. General de-AI editing that applies to legal writing unchanged

These overlap with the `humanizer` skill. Section numbers there move between
versions, so they are described rather than cross-referenced:

- **Inflated claims about importance.** "This case presents a pivotal question"
  is as bad in a brief as anywhere.
- **Shallow -ing phrases.** "...thereby demonstrating the impropriety of joinder"
  is padding. Say it.
- **Vague sources.** In a brief this is worse than vague, it is unsupported. Every
  proposition needs a citation or a record cite.
- **Stock words used as padding.** Review *crucial, key, pivotal, underscore,
  highlight, delve, landscape, interplay, testament, robust, nuanced* in context.
  Retain an accurate word when it does useful work, especially in a quotation.
- **Avoiding *is* and *are*.** "The complaint serves as the charging document" should
  be "the complaint is the charging document."
- **False "from X to Y" ranges.**
- **No em dashes.** Already the default style.
- **Chatbot text left in the answer.** Obviously.
- **Filler phrases.** "In order to" → "to." "Due to the fact that" → "because."
  **"It is important to note that"** is a common filler phrase in
  legal writing. Usually cut it; if the point is important, its position in the
  paragraph shows that.
- **Pretending to reveal a deeper truth.** "The real question is" and "at its
  core" are argument-shaped noise.
- **Announcing the next point.**
- **Answering objections no one raised**, where the objection is invented. This
  is distinct from answering the opponent's actual best argument, which is required.
  The test: would a competent opponent make it? If yes, answer it. If you invented
  it to knock it down, cut it.
- **Rejecting fake alternatives.**

## 5. Rules that change in legal writing

**Forced groups of three.** Modified, not off. Reflexive tricolons are a tell.
But a deliberate parallel triple is a legitimate and effective device in a brief:
"The two sets of charges share no date, no location, and no complainant." The test
is whether the three items are really parallel and really the point. Three because
there are three: keep. Three because three sounds complete: cut to the two that
matter.

**Passive voice.** Modified. Prefer active for your own actor. But the passive
is correct where the actor is unknown, irrelevant, or deliberately de-emphasized:
"the motion was served on February 20" is better than naming yourself again, and
"Counts 1 through 4 were joined" is appropriate when who joined them is not the
issue. Do not hunt passives in procedural recitals.

**Too many qualifiers.** Modified. Piled-up hedging in an argument is weakness.
But legal writing has *precision* qualifiers that may carry necessary meaning:
"to the extent that," "on the face of the complaint," "without prejudice," and
"in the alternative." Retain them when accurate. A phrase such as "subject to and
without waiving" does not itself preserve every objection; state the actual scope
and basis of the response. Cut empty hedging without deleting real legal limits.

**Dramatic fragments.** Modified. A row of fragments is a tell. **One** short
sentence after several long ones is one of the strongest moves in brief writing:
"This record makes that showing." "Nothing like that is alleged here." Keep those;
they are earned by contrast.

**Repeated sentence openings.** Modified. Do not cycle synonyms for a party, and
do not rename a case. But repeated openings are sometimes the correct structure, as
when walking a factor list where each sentence starts with the factor.

## 6. Rules that are OFF in legal writing

Applying these to a filing makes it worse. The humanizer's own instruction covers
this: "Keep reference, technical, legal, and factual text neutral."

- **"Too much bold."** Off. Point headings are bold by convention, and the
  builder's `h2` and `h3` blocks produce bold headings on purpose.
- **"Lists with bold mini-headings."** Off. Numbered relief paragraphs and
  enumerated ordered items are the required form.
- **"Title case in headings."** Off. Generic section labels may be ALL CAPS and
  centered; substantive point headings use the bold, flush-left, sentence-case
  `I. / A. / 1.` hierarchy in `circuit-court.md`.
- **"Curly quotation marks."** Off. Word curls them, courts do not care, and
  changing them risks corrupting a quotation.
- **"Too many hyphenated word pairs."** Off. Legal compounds are fixed terms:
  *cross-admissibility, other-acts evidence, self-represented, non-privileged,
  post-conviction*. Do not de-hyphenate a term of art.
- **"Add personality."** Off entirely. No first person beyond what the form requires,
  no asides, no humor, no expressed feelings. A brief is not personal writing, and
  indignation reads as weakness. See `argument.md` § 9.
- **Deliberate informality of any kind.** Off.

## 7. Writing in this signer's voice

When the user supplies prior filings and wants continuity, preserve useful
formulas from those examples. The examples below are optional pro se plaintiff
language, not evidence of the current signer's voice or role. Adapt the party
designation, representation status, pronouns, and relief to the supplied facts.

**Openers.**
- `NOW COMES Plaintiff [NAME], pro se, and for [his/her/their] Answer to...`
- `Plaintiff [NAME], pro se, moves the Court for an Order...`
- `Plaintiff [NAME], pro se, submits this Brief in Opposition to...`

**Discovery response examples**, to use only when true and legally appropriate:
- `Subject to and without waiving those objections, Plaintiff states that...`
- `after a reasonable search, he has identified no responsive documents`
- `already provided, identified, filed in the court record, or otherwise equally
  available to Defendant`
- `Plaintiff reserves the right to supplement this response if additional responsive
  materials are later identified or later come into Plaintiff's possession, custody,
  or control.`

**Framing moves.**
- `The relief requested is narrow and enforceable.`
- `Plaintiff respectfully requests that the Court deny [X].`

**Closers.**
- `WHEREFORE, Plaintiff respectfully requests that the Court enter an order [specific
  relief], and granting such other and further relief as the Court deems just and
  proper.`

**Structural habits.** Roman-numeral section headings with periods. INTRODUCTION as
the first heading in a brief. A short second paragraph in the introduction stating
what is being asked for. Statutory citations in-line rather than in footnotes.

**Preserve useful supplied language without freezing defects.** Do not insert
`Subject to and without waiving` automatically: specify what is objected to and
what is answered or withheld. Equal availability alone does not establish a valid
objection, and a reservation does not replace the actual supplementation duties.
See `circuit-court.md` on objections and discovery responses.

**When drafting for an attorney signer**, the voice is that attorney's, not this
one. Ask for a prior filing and match it.

## 8. The pass to run

After the draft is written and before the review in `review.md`:

1. **Read it aloud.** Anything you stumble on is a candidate.
2. **Check paragraph lengths.** If they are all within two lines of each other, the
   argument is probably being padded to fill a shape. Let the strong point run long
   and the weak one stay short.
3. **Search for the stock phrases:** *it is important to note, crucial, key, pivotal,
   underscore, highlight, delve, landscape, robust, nuanced, in order to, due to the
   fact that, the real question is, at its core.* Cut padding; retain necessary
   legal terms, accurate quotations, and the user's deliberate wording.
4. **Count the tricolons.** More than one or two in a filing means they are a habit,
   not a device.
5. **Look for missing texture.** Every "subsequently," "thereafter," and
   "Defendant responded" that could carry a date, a document number, or a name
   should carry one.
6. **Compare with supplied examples, if any.** Preserve useful continuity; do not
   force the stock formulas in § 7 into every document.
7. **Confirm the register fits the user and audience.** The default is formal and
   restrained, without needless rhetorical questions, exclamations, or personal
   attacks. Do not alter quotations or factual testimony to enforce that default.

Then run `review.md`, which checks the things that actually get filings rejected.
