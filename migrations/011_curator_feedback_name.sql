-- Migration 011: optional curator name on curator_feedback
-- Curators may now optionally identify themselves when submitting feedback —
-- some prefer to attribute their suggestions, others want to stay anonymous.

alter table public.curator_feedback
  add column if not exists submitted_by text null;
