# Apothecary's Glossary of Information Retrieval

*A guide for scholars and seekers to understand the arcane metrics and techniques of Candlekeep.*

---

## 📜 Retrieval Metrics

### The Oracle's Promptness (MRR)
**Technical Name:** Mean Reciprocal Rank
**The Lore:** When thou asketh a question, how quickly doth the Oracle present the correct scroll? If the truth is the very first scroll given to thee, the score is 1. If it is the second, it is 1/2. MRR is the average of these fractions across many queries. A high MRR means the library is decisive and accurate.

### The Quality of the Tome's Arrangement (nDCG@K)
**Technical Name:** Normalized Discounted Cumulative Gain
**The Lore:** It is not enough to find the truth; it must be presented in its proper order. This metric rewards the library for placing the most relevant scrolls at the very top and penalizes it for burying them beneath less useful information. The "K" (usually 5) denotes that we only judge the top 5 scrolls.

### The Success of the Scry (Hit Rate@K)
**Technical Name:** Recall@K / Hit Rate
**The Lore:** Out of a set of five scrolls, did the library manage to find at least one that contains the answer? If yes, the scry is a success. This is a measure of the library's reach — its ability to find the relevant knowledge somewhere in the stacks, even if it is not at the very top.

---

## 🧪 Arcane Techniques

### Lexical Matching (BM25)
**The Lore:** A technique that looks for exact symbols and sigils. If thou seeketh "v3.4.1", BM25 will look for exactly those characters. It is immune to the "vibes" of semantic search and focuses strictly on the literal word.

### Semantic Search (Dense Retrieval)
**The Lore:** Searching by meaning rather than by word. This technique understands that "caching" and "buffer" are related, even if the words are different. It uses high-dimensional vector spaces to find concepts.

### Rank Fusion (RRF)
**Technical Name:** Reciprocal Rank Fusion
**The Lore:** When two different roads lead to two different sets of scrolls (one via Lexical Matching and one via Semantic Search), RRF is the ritual that merges them. It gives higher priority to scrolls that appeared near the top of *both* lists, creating a unified and more accurate collection.

### Cross-Encoder Reranking
**The Lore:** A slow but incredibly thorough study of the candidate scrolls. While the initial search is fast and broad, the reranker takes each scroll and compares it word-for-word against thy query, re-ordering them with divine precision.

---

## 🏰 Library Terms

### Arcane Recall
**Technical Name:** Parent Document Retrieval / Contextual Pruning
**The Lore:** Returning a single torn page is often useless, but returning an entire chapter is wasteful. Arcane Recall now intelligently expands matching fragments. It merges overlapping pages into a single cohesive window and uses similarity-weighting to only include neighboring text that is truly relevant to thy query, reducing token waste by 22%.

### Bardic Knowledge
**Technical Name:** Contextual Chunk Embeddings
**The Lore:** Every fragment of knowledge in the library is etched with the name and description of the document it came from. This ensures that even the smallest chunk remembers its heritage and purpose.

### The Relevance Ward
**Technical Name:** Cosine Similarity Thresholding
**The Lore:** A protective barrier that prevents the library from guessing. If no scrolls are found with enough confidence to be considered true, the library remains silent rather than presenting false or irrelevant information.
