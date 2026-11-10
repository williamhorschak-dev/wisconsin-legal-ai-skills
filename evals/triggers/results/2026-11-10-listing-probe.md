# Trigger evaluation note: 2026-11-10, what the host showed the model

No trigger runs were made on this date. This note records why, and what it means for reading
trigger results from this host.

## What was planned

The writing skill ships a letter template, and its one letter query (a validation query) was
missed on 2026-10-24 in round 3 and in 0 of 3 round-4 repeats. The plan was to add a letter
query to the train split, measure the current description three times per query, then measure
a candidate description that names letters to the court.

## What the probe found

Before any run, one fresh subagent (claude-sonnet-5-5, Claude Code desktop 2.1.321, Windows 11)
was asked to copy out what its own skill listing showed for the three skills, without calling
a tool. It reported about 550 listed skills and these entries:

| Entry | Description shown to the model |
|---|---|
| `wisconsin-legal-interpretation` | Yes, in full |
| `wisconsin-legal-writing` | No, name only |
| `cite-check` | No, name only |
| `anthropic-skills:wisconsin-legal-interpretation` | No, name only |
| `anthropic-skills:wisconsin-legal-writing` | Yes, in full (the description of release 2026.11.10.2) |
| `anthropic-skills:cite-check` | No, name only |

The coordinating session's own listing showed the same pattern. This is one model's report of
its own context plus one matching observation, not a reading of the host's source.

## What follows

- **A candidate description cannot be measured on this host as configured.** The copy of the
  writing skill that the project installs was listed by name only. The description the model
  could read belonged to a second copy that the project's install step does not write. Changing
  the installed description would not have changed what the model saw.
- **For cite-check the model saw no description at all** in either copy. A trigger run here
  would measure whether the name alone prompts loading.
- **Whether this affected the 2026-10-24 rounds is not known.** That record does not say how
  many skills were installed or which descriptions the model was shown. Its cite-check misses
  and the two rejected cite-check candidates should be read with that gap in mind. They are not
  shown to be artifacts, and they are not shown to be measurements of the description.
- **The description is unchanged.** A candidate that adds letters to the court could also pull
  in the near-miss queries about a cover letter and a demand letter. It should not ship
  unmeasured.

## What a valid run needs

A host profile with only the three skills installed, a check that each description is shown
(the probe above, repeated), the dataset version recorded with the result, and three runs per
query. Dataset version 2, added with this note, holds the new train query:
[datasets.json](../datasets.json).

No model output in this note was adopted or approved by the maintainer. Not attorney-reviewed.
