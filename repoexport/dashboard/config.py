"""
Shared constants: category labels, colors, source labels, brand colors.

TEMPLATE: replace the placeholder CATEGORY_* and SOURCE_LABELS values below
with the new topic's category buckets and source-name labels.

The dashboard reads from Supabase `v_dashboard` view (see dashboard/data.py).
"""

# Category buckets the curator can assign articles to in the newsletter draft.
# If you keep this empty, dashboard pages that depend on categories (Organise,
# Draft) will need adapting — see docs/new_topic_template.md.
CATEGORY_LABELS: dict[str, str] = {
    # "bucket_key": "Bucket display label",
}

CATEGORY_ORDER: list[str] = [
    # Order in which buckets appear in dropdowns + draft sections
]

CATEGORY_COLORS: dict[str, str] = {
    # "bucket_key": "#hexcolor",
}

# Pretty labels for source IDs used in sources.yml. Falls back to the raw
# source ID if no label is set, so this is optional.
SOURCE_LABELS: dict[str, str] = {
    # "source_id": "Pretty Source Name",
}

# Brand colors. Override per topic if you like.
NAVY = "#0f1e3d"
TEAL = "#44b4a6"
LIGHT_BLUE = "#5b9bd5"
MID_BLUE = "#1d3461"
