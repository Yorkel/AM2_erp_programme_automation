# Engineering decision & incident records

A running log of the design, modelling, operational, and governance decisions
behind the ERP newsletter automation. Each file is a point-in-time record of a
decision, a finding, or a production incident, with the reasoning and evidence.

New here? Start with the **Model card**, **Data layer design**, and the
**29 June incident** , they give the clearest picture of how the system is built
and how it's run in production.

## Model & evaluation
| Doc | What it covers |
|---|---|
| [model_card.md](model_card.md) | Model card: intended use, training data, performance, limitations |
| [model_lifecycle.md](model_lifecycle.md) | Versioning, retraining triggers, decommissioning |
| [evaluation_findings.md](evaluation_findings.md) | Held-out evaluation, the skew bug, held-out vs real-world gap |
| [model_redesign_and_retraining.md](model_redesign_and_retraining.md) | "If I were starting again" , redesign reflections |
| [model_v1_state_and_retraining_plan.md](model_v1_state_and_retraining_plan.md) | v1 state, drift findings, retraining plan |
| [embeddings_and_llm_post_model.md](embeddings_and_llm_post_model.md) | Taxonomy findings & transferable insights |
| [old_test_set_archived_2026_05_17.md](old_test_set_archived_2026_05_17.md) | Why the original test set was archived |

## Data
| Doc | What it covers |
|---|---|
| [data_layer_design.md](data_layer_design.md) | Three-table Supabase design + `v_dashboard` view |
| [datasheet.md](datasheet.md) | Datasheet for the training dataset |

## Monitoring & reliability
| Doc | What it covers |
|---|---|
| [monitoring_redesign_2026_06_11.md](monitoring_redesign_2026_06_11.md) | Quality gate at ingestion, weekly drift, monthly source review |
| [curator_feedback_loop.md](curator_feedback_loop.md) | Curator feedback loop and concept drift |
| [scrape_reliability_hardening_2026_05_28.md](scrape_reliability_hardening_2026_05_28.md) | Silent enrichment-failure hardening |

## Production incidents
| Doc | What it covers |
|---|---|
| [incident_2026_06_16_pipeline_failure.md](incident_2026_06_16_pipeline_failure.md) | Weekly pipeline failure |
| [incident_2026_06_22_classifier_cold_start.md](incident_2026_06_22_classifier_cold_start.md) | Classifier cold-start + blank-summary crash |
| [incident_2026_06_29_runner_claude_connectivity.md](incident_2026_06_29_runner_claude_connectivity.md) | GitHub runner cannot reach the Claude API |
| [render_free_tier_memory_limit.md](render_free_tier_memory_limit.md) | Render free-tier OOM diagnosis & mitigation |

## Sources
| Doc | What it covers |
|---|---|
| [source_roster_gaps_2026_05_17.md](source_roster_gaps_2026_05_17.md) | Gaps in the source roster |
| [disabled_sources.md](disabled_sources.md) | Sources disabled and why |

## Governance, ethics & security
| Doc | What it covers |
|---|---|
| [threat_model_and_security.md](threat_model_and_security.md) | Threat model & security frameworks |
| [sustainability_footprint.md](sustainability_footprint.md) | Environmental footprint & longevity |
