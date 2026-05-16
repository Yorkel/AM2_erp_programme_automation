# Curator Feedback Loop and Concept Drift

Decision date: 2026-05-16

## Decision

The curator dashboard must write curator decisions back into Supabase. The repo will then run a weekly analysis job after the newsletter is finalised, using only finalised decisions to measure correction rates and concept drift.

## Why

Curators may change their minds during the week while building the newsletter. We do not want temporary edits to count as model errors. Concept drift should be measured from the final editorial decision, not from every intermediate click.

## Flow

```text
Classifier API
  -> classify_newsletter table
  -> Next.js dashboard
  -> curator edits during the week
  -> Supabase stores current draft decision
  -> newsletter is finalised
  -> decisions are marked final
  -> weekly monitoring job analyses final decisions only
```

## Decision Types

For each article, record the final curator outcome:

- `accepted_top1`
- `changed_to_top2`
- `changed_to_other`
- `marked_irrelevant`
- `marked_unsure`

Use `decision_status` to separate working state from final state:

- `draft`
- `final`

## Proposed Tables

`curator_decisions` stores the current decision state for each article/newsletter week.

Key fields:

- `article_id`
- `newsletter_week`
- `model_run_id`
- `predicted_top1`
- `predicted_top1_confidence`
- `predicted_top2`
- `predicted_top2_confidence`
- `curator_label`
- `decision_type`
- `decision_status`
- `curator_id`
- `updated_at`
- `finalised_at`

`curator_decision_events` optionally stores the audit trail of every change.

Key fields:

- `article_id`
- `newsletter_week`
- `old_label`
- `new_label`
- `old_decision_type`
- `new_decision_type`
- `changed_by`
- `changed_at`

## Weekly Monitoring

The weekly monitoring job should read finalised decisions from Supabase and calculate:

- reviewed article count
- accepted top-1 rate
- changed-to-top-2 rate
- changed-to-other rate
- irrelevant rate
- unsure rate
- overall correction rate
- correction rate by predicted category
- common confusion pairs, such as `edtech -> policy_practice_research`

Concept drift is indicated when curator correction rates rise over time, especially within specific categories or repeated confusion pairs.

## Retraining Loop

Final curator decisions become labelled data for future retraining:

```text
model predicts
  -> curator corrects
  -> final decisions are monitored
  -> correction patterns indicate drift
  -> final labels are added to training data
  -> new model version is trained
  -> active.txt points production to the new version
```

This creates a human-in-the-loop ML system rather than a one-way classifier.
