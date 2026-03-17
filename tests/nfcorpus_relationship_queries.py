"""NFCorpus benchmark queries for graph augmentation.

Two query sets:

1. EXPANSION_QUERIES (scenario 1): Query names entity A only. Ground truth =
   B-only docs (contain B but not A). Derived at fixture time from ChromaDB
   entity metadata. Tests the graph's ability to surface docs invisible to
   vector search.

2. RELATIONSHIP_QUERIES (scenario 3): Query names both entities. Ground truth =
   co-occurrence docs. Scored with graded NDCG@5 using Jaccard as relevance.
"""

# ── Scenario 1: Entity expansion ─────────────────────────────────────────────
# Each entry: query mentioning entity_a only, entity_b is the expansion target.
# Ground truth (b_only_doc_ids) is derived at fixture time — not hardcoded —
# because it depends on which docs the extractor tags with each entity.

EXPANSION_QUERIES = [
    {
        "query": "what are the health benefits of curcumin supplementation?",
        "entity_a": "curcumin",
        "entity_b": "turmeric",
    },
    {
        "query": "how do carotenoids protect against oxidative damage?",
        "entity_a": "carotenoids",
        "entity_b": "lycopene",
    },
    {
        "query": "what is the role of folate in preventing neural tube defects?",
        "entity_a": "folate",
        "entity_b": "homocysteine",
    },
    {
        "query": "how does cholesterol affect cardiovascular disease risk?",
        "entity_a": "cholesterol",
        "entity_b": "triglycerides",
    },
    {
        "query": "what causes myocardial infarction in young adults?",
        "entity_a": "myocardial",
        "entity_b": "stroke",
    },
    {
        "query": "what triggers apoptosis in tumor cells?",
        "entity_a": "apoptosis",
        "entity_b": "proliferation",
    },
    {
        "query": "what are the dietary sources and benefits of magnesium?",
        "entity_a": "magnesium",
        "entity_b": "zinc",
    },
    {
        "query": "how do prebiotics improve gut microbiome health?",
        "entity_a": "prebiotics",
        "entity_b": "probiotics",
    },
    {
        "query": "what is the relationship between diabetes and metabolic syndrome?",
        "entity_a": "diabetes",
        "entity_b": "obesity",
    },
    {
        "query": "how does selenium deficiency affect immune function?",
        "entity_a": "selenium",
        "entity_b": "zinc",
    },
]


# ── Scenario 3: Relationship queries (graded NDCG@5) ─────────────────────────
# entity_pair used for Jaccard-based relevance scoring at test time.

RELATIONSHIP_QUERIES = [
    # ── cholesterol + breast ─────────────────────────────────────────────────
    {
        "query": "what is the connection between cholesterol metabolism and breast cancer prognosis?",
        "entity_pair": ("cholesterol", "breast"),
    },
    {
        "query": "how do cholesterol levels influence breast tumor development?",
        "entity_pair": ("cholesterol", "breast"),
    },

    # ── curcumin + inflammation ──────────────────────────────────────────────
    {
        "query": "how does curcumin affect inflammation in arthritis patients?",
        "entity_pair": ("curcumin", "inflammation"),
    },
    {
        "query": "what role does curcumin play in reducing inflammation and joint disease?",
        "entity_pair": ("curcumin", "inflammation"),
    },
    {
        "query": "curcumin and inflammation pathways in osteoarthritis treatment",
        "entity_pair": ("curcumin", "inflammation"),
    },

    # ── insulin + glucose ────────────────────────────────────────────────────
    {
        "query": "relationship between insulin resistance and glucose in type 2 diabetes",
        "entity_pair": ("insulin", "glucose"),
    },
    {
        "query": "how do insulin and glucose interact in diabetes pathogenesis?",
        "entity_pair": ("insulin", "glucose"),
    },
    {
        "query": "insulin glucose metabolism and diabetes risk factors",
        "entity_pair": ("insulin", "glucose"),
    },

    # ── homocysteine + folate ────────────────────────────────────────────────
    {
        "query": "does folate lower homocysteine and reduce cognitive decline?",
        "entity_pair": ("homocysteine", "folate"),
    },
    {
        "query": "homocysteine folate and brain atrophy in aging populations",
        "entity_pair": ("homocysteine", "folate"),
    },
    {
        "query": "relationship between homocysteine levels and folate supplementation",
        "entity_pair": ("homocysteine", "folate"),
    },

    # ── polyphenols + cardiovascular ─────────────────────────────────────────
    {
        "query": "how do polyphenols act as antioxidants in cardiovascular disease prevention?",
        "entity_pair": ("polyphenols", "cardiovascular"),
    },
    {
        "query": "polyphenol effects on cardiovascular risk markers and endothelial function",
        "entity_pair": ("polyphenols", "cardiovascular"),
    },

    # ── sulforaphane + cancer ────────────────────────────────────────────────
    {
        "query": "does sulforaphane induce apoptosis in cancer cells?",
        "entity_pair": ("sulforaphane", "cancer"),
    },
    {
        "query": "sulforaphane and cancer cell proliferation mechanisms",
        "entity_pair": ("sulforaphane", "cancer"),
    },

    # ── flavonoids + cancer ──────────────────────────────────────────────────
    {
        "query": "do flavonoids trigger apoptosis in cancer cells?",
        "entity_pair": ("flavonoids", "cancer"),
    },
    {
        "query": "flavonoid effects on cancer cell apoptosis and proliferation",
        "entity_pair": ("flavonoids", "cancer"),
    },

    # ── triglycerides + coronary ─────────────────────────────────────────────
    {
        "query": "how do triglycerides and cholesterol contribute to coronary heart disease?",
        "entity_pair": ("triglycerides", "coronary"),
    },
    {
        "query": "triglyceride levels and coronary artery disease risk factors",
        "entity_pair": ("triglycerides", "coronary"),
    },

    # ── obesity + diabetes ───────────────────────────────────────────────────
    {
        "query": "how does obesity affect insulin sensitivity and diabetes development?",
        "entity_pair": ("obesity", "diabetes"),
    },
    {
        "query": "obesity insulin resistance and type 2 diabetes pathways",
        "entity_pair": ("obesity", "diabetes"),
    },

    # ── mediterranean + cardiovascular ───────────────────────────────────────
    {
        "query": "how does the mediterranean diet affect cardiovascular disease risk?",
        "entity_pair": ("mediterranean", "cardiovascular"),
    },
    {
        "query": "mediterranean diet and cardiovascular health outcomes in clinical trials",
        "entity_pair": ("mediterranean", "cardiovascular"),
    },

    # ── curcumin + arthritis ─────────────────────────────────────────────────
    {
        "query": "curcumin supplementation for arthritis pain and joint stiffness",
        "entity_pair": ("curcumin", "arthritis"),
    },

    # ── antioxidant + cardiovascular ─────────────────────────────────────────
    {
        "query": "antioxidant intake and cardiovascular disease prevention mechanisms",
        "entity_pair": ("antioxidant", "cardiovascular"),
    },
]

assert len(EXPANSION_QUERIES) == 10
assert len(RELATIONSHIP_QUERIES) == 25
