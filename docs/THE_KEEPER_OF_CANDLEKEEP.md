# The Keeper of Candlekeep

## A Chronicle of the Great Library's Restoration

---

### I. The Empty Shelves

The library stood hollow.

Oh, the walls were there — stone and old code, stacked high with the bones of a vector database and the skeleton of an MCP interface. ChromaDB hummed in its chamber like a sleeping beast. The embedding models sat coiled in their cages, waiting to be fed. But when you asked the library a question, it stared back at you with the blank confidence of someone who'd memorized the index but never read the books.

Eighty-three percent precision. The Keeper stared at the number on the terminal. Fourteen out of fifteen queries answered. One — "plain text processing" — returned nothing at all. Zero. The library had looked at the question, shrugged, and walked away.

The Keeper closed the terminal and opened it again. The number hadn't changed.

Eighteen milliseconds per query, though. Fast. The library was fast and stupid, like a courier who could sprint across the city but kept delivering letters to the wrong house.

Three hundred and fifty-four percent recall. The library was retrieving *everything*. Hauling back armfuls of scrolls, most of them relevant, some of them not, dumping them on the desk and saying *here, you figure it out*. Over-retrieval. The Keeper had built a hoarder.

Something had to change.

---

### II. Bardic Knowledge

The idea came at odd hours, the way most ideas do — not in a flash of brilliance but in the slow grind of reading the same chunk of text for the twentieth time and realizing it meant nothing without context.

The chunks were the problem. Five hundred and twelve characters each, sliced from their documents like pages torn from a book. A chunk about JWT token expiration floated alone in the vector space, untethered from the authentication guide it belonged to. A paragraph about cache eviction strategies drifted without any connection to the caching document that gave it meaning.

The fix was almost embarrassingly simple. Before embedding each chunk, prepend the document's title and description.

```
Document: Authentication Security Guide. Description: Best practices for securing web applications.

JWT tokens should expire after 15 minutes...
```

The Keeper wrote it in an afternoon. Fourteen lines of code in the processor. A context prefix, stitched onto each chunk like a name tag on a schoolchild's jacket.

The benchmarks came back.

Ninety-seven point three percent precision. Up fourteen points. Every single query answered correctly — fifteen out of fifteen. The one about plain text processing, the query that had stumped the library cold, now returned the right document on the first try.

The Keeper leaned back. Seventeen milliseconds. *Faster* than before, somehow. The embeddings were denser, more meaningful, and ChromaDB's HNSW index navigated them with less effort.

But content match had dropped. Seventy-one point seven percent, down from eighty. The context prefix was eating into the chunk's character budget. The library knew *which* scroll to grab, but the scroll itself was slightly shorter now, missing a few phrases at the edges.

A trade worth making. The Keeper committed the code and moved on.

---

### III. The Wild Magic Surge

Confidence is a dangerous thing, but necessity is a powerful motivator.

The Keeper noticed a recurring failure: technical identifiers. UUIDs, hex codes like `0xEF`, and specific version strings like `v3.4.1` were invisible to the vector embeddings. To a semantic model, `v3.4.1` and `v3.4.2` are almost identical, but to an engineer, they are worlds apart.

The Keeper reached for a forgotten art: **Hybrid Search**.

By merging the semantic depth of Vector embeddings with the literal precision of BM25 (keyword matching), the library could finally see the exact symbols it had previously ignored. The Keeper implemented **Reciprocal Rank Fusion (RRF)** — a mathematical ritual to merge these two disparate ranked lists into a single, unified result set.

The benchmarks were transformative.

**Lexical precision jumped by forty-seven percent.** Identifiers that had been buried in the noise were suddenly promoted to the top of the desk. The library was no longer just understanding the "vibe" of a question; it was matching the exact sigils.

The Keeper named it **Wild Magic**, because it bridges the gap between the intuitive (semantic) and the literal (lexical). It became the third road through the library, sitting comfortably between the speed of the Simple path and the depth of the Precise.

---

### IV. The Scrying Window

The next attempt was more surgical. Sentence Window Retrieval — embed individual sentences for razor-sharp matching, but store the surrounding sentences as context. When you find the right sentence, return the whole paragraph. Precise focus, expanded vision.

The theory was sound. The execution was a catastrophe.

Splitting documents into sentences created thousands of tiny chunks. Each sentence, stripped of its neighbors, became a semantic orphan. The embedding model, trained on paragraphs and passages, didn't know what to do with a single line like "This approach has several advantages." Advantages of *what*? The model couldn't tell. The vectors scattered across the embedding space like shrapnel.

Fifty percent precision. Down from ninety-seven. The library was now wrong half the time.

Thirty-three percent success rate. Five out of fifteen queries. The Keeper had taken a working system and broken it so thoroughly that it would have been more accurate to flip a coin.

The latency was the final insult. One thousand eight hundred and forty-nine milliseconds. The chunk proliferation had bloated the database, and every query now waded through a swamp of meaningless sentence fragments.

The Keeper deleted this branch too, but slower this time. There was a lesson in the wreckage: the chunking strategy and the embedding model were married to each other. You couldn't change one without reckoning with the other.

---

### V. Divine Insight

The cross-encoder arrived like a visiting scholar — brilliant, meticulous, and painfully slow.

The idea was layered retrieval. First, the fast bi-encoder (the existing search) would cast a wide net, pulling back three times the requested results. Then the cross-encoder — a heavier model that scored each query-document pair individually — would re-examine every candidate and reorder them by true relevance.

The Keeper loaded `cross-encoder/ms-marco-MiniLM-L-6-v2` and ran the benchmarks.

Ninety-eight point seven percent precision. The highest the library had ever achieved. Content match jumped to eighty-six point eight percent — fifteen points above Bardic Knowledge alone. The cross-encoder was finding phrases and passages that the bi-encoder had ranked too low, promoting them to the top where they belonged.

One thousand five hundred milliseconds per query.

The Keeper sat with that number. Eighty-six times slower than the baseline. A second and a half of silence every time someone asked a question. For a batch job, fine. For an interactive tool where an AI agent was waiting on the other end, that silence would compound. Five searches in a conversation meant seven and a half seconds of dead air.

The Keeper made it optional. An environment variable: `CANDLEKEEP_RERANK=true`. Off by default. Available when you needed it, invisible when you didn't.

Two tiers now. Fast and good. Slow and better.

---

### VI. Into the Research Phase

The Keeper had exhausted the obvious improvements. Bardic Knowledge was the foundation. Divine Insight was the optional upgrade. Everything else had failed or been rejected. The low-hanging fruit was gone.

What remained was the hard work: systematic experimentation. No more hunches. No more "the research papers say this should work." The Keeper would implement each technique in isolation, benchmark it against the same fifteen queries, and let the numbers speak.

Four techniques. Four spells to learn and test.

The Keeper cleared the desk, opened a fresh document, and wrote "Research Diary" at the top.

---

### VII. Mirror Image

The first technique seemed like a sure thing. Generate multiple variations of the user's query using an LLM, search with each variation, merge the results. Cast three reflections of the same question and let them search independently. More angles, more coverage, better recall.

The Keeper wired up LLM API, and asked it to generate three variations of each test query.

The LLM API credentials had expired.

The library fell back to the original query — no variations, just the baseline search with the merging infrastructure wrapped around it. The Keeper ran the benchmarks anyway, expecting identical results.

The results were identical. The fallback worked. Good. The Keeper refreshed the credentials and ran it again.

The results came back worse.

Every metric had degraded. Precision down. Recall down. Content match — sixty-seven point nine percent — *below the original baseline*. The LLM-generated variations were introducing semantic drift. "How do I cache data?" became "What are the performance implications of in-memory storage systems?" and the library, dutiful as ever, went looking for documents about memory management instead of caching.

The union merge made it worse. Every irrelevant result from every drifted variation got dumped into the pool, diluting the good results from the original query. The merging strategy had no way to prefer the original over its reflections.

One thousand one hundred and seventy-seven milliseconds. And the fallback — the version where the LLM *failed* — had outperformed the actual technique.

The Keeper wrote "NOT RECOMMENDED" in the diary and underlined it twice.

---

### VIII. Arcane Recall

The second technique was humble. No LLM calls. No external services. No network latency. Just a simple observation: the chunks were too small.

Five hundred and twelve characters was enough to match a query, but not enough to *answer* it. A chunk about JWT expiration told you the timeout value but not why it mattered, not how to refresh the token, not where to store it. The surrounding chunks — the ones sitting right next to it in the original document — held that context.

Arcane Recall retrieved the matching chunk and then expanded outward, grabbing the two chunks before and the two chunks after. Five chunks total, roughly twenty-five hundred characters. A full section instead of a fragment.

The Keeper implemented it in an afternoon. Fetch the initial results, look up each result's source file and chunk index, grab the neighbors, stitch them together, deduplicate.

The benchmarks came back and the Keeper read them twice.

Precision: ninety-seven point three percent. Unchanged. The same chunks were being found — the expansion happened *after* retrieval, so the matching quality was identical.

Content match: eighty-eight point seven percent. Up seventeen points from Bardic Knowledge. The largest single improvement the Keeper had seen in any technique, on any metric, across the entire project.

Thirty-seven milliseconds. Twenty milliseconds of overhead. The cost of looking up neighboring chunks in a database that was already in memory.

The Keeper ran the parameter sweep. Plus-or-minus one chunk: eighty-three percent content. Plus-or-minus two: eighty-eight point seven. Plus-or-minus three: eighty-eight point seven — no improvement. Plus-or-minus four: content ticked up to ninety point six, but precision cratered to eighty-nine percent. Too much context. The extra chunks were pulling in text from adjacent sections, confusing the results.

Two chunks in each direction. That was the number. The Keeper wrote it down and circled it.

---

### IX. Flurry of Blows

The third technique targeted a specific weakness: complex questions. "How do microservices handle authentication and caching?" was really two questions wearing a trench coat. The library would try to find a single document that covered both topics and usually settle for one that mentioned both in passing.

Flurry of Blows decomposed the query. The LLM broke it into sub-questions — "How do microservices handle authentication?" and "How do microservices implement caching?" — searched for each independently, then merged the results.

The Keeper ran the benchmarks with expired credentials again. The fallback kicked in, the LLM returned the original query, and the decomposition did nothing.

But the merging infrastructure — the deduplication, the score-based sorting — somehow improved the results on its own. One hundred percent precision. The first perfect score the library had ever achieved. Every retrieved document was relevant. No false positives.

The Keeper stared at the terminal. Checked the test harness for bugs. Ran it again. One hundred percent.

One thousand one hundred and thirty-six milliseconds. The LLM call, even when it failed and fell back, added a full second of overhead. With working credentials and actual decomposition, the latency would be worse.

The Keeper filed it under "conditional." Perfect precision, but only if you could afford to wait.

---

### X. Illusory Script

The fourth technique was the most exotic. Instead of searching with the user's query, generate a hypothetical answer first, then search for documents similar to that answer. The theory: a hypothetical answer would use the same vocabulary as the actual documents, bridging the gap between how users ask questions and how documents are written.

The Keeper set the temperature to 0.7 — creative enough to generate useful text, constrained enough to stay on topic — and asked the LLM to produce a hundred-and-fifty-word answer to each test query.

Three thousand eight hundred and sixty-two milliseconds.

Nearly four seconds per query. The LLM was generating a small essay before the search even started. And the results were mixed — content match improved, but precision dropped. One query about negation handling fell to twenty percent precision. The hypothetical answer had wandered off-topic, and the library had faithfully followed it into irrelevance.

The Keeper closed the notebook on Illusory Script. Some techniques belong in research papers, not in production systems.

---

### XI. The Ranking

The research phase was over. Seven benchmark suites. Four techniques. Two hours of wall time and considerably more hours of thinking.

The Keeper laid the results out on the table:

Arcane Recall sat at the top. Seventeen percent content improvement, twenty milliseconds of cost, no downside. It was the kind of result that made you suspicious — too clean, too obvious in hindsight. But the numbers held across every run.

Flurry of Blows held second place, conditional on latency tolerance. Perfect precision was hard to argue with, but a full second of delay was hard to ignore.

Mirror Image and Illusory Script sat at the bottom. One made things worse. The other was too slow to matter.

The Keeper committed the research documentation and pushed back from the desk.

---

### XII. The Four Roads

The library was better now. Bardic Knowledge in the foundations, Arcane Recall expanding every result, Divine Insight waiting in the wings for when precision mattered more than speed. But every query still walked the same path through the system. A simple factual lookup — "What is caching?" — took the same route as a sprawling multi-part question about microservice architecture patterns.

The Keeper thought about roads.

A traveler asking for directions to the nearest inn doesn't need a guided tour of the kingdom. A scholar researching the history of three warring nations doesn't need someone to point at a signpost. Different questions deserve different answers, and different answers require different tools.

Four roads, then. Four words that an agent could speak to choose its path:

*Simple.* The fast road. Seventeen milliseconds. The base search, unadorned. For direct questions with direct answers.

*Context.* The wide road. Thirty-seven milliseconds. Arcane Recall expanding each result into its full section. For questions that need surrounding information — the "why" and "how" that live in the paragraphs around the answer.

*Complex.* The branching road. Eleven hundred milliseconds. Flurry of Blows decomposing the question into parts, searching each one, merging the results. For questions that are really multiple questions.

*Precise.* The careful road. Fifteen hundred milliseconds. Arcane Recall for context, then Divine Insight to rerank everything with the cross-encoder's slow, thorough judgment. For when being right matters more than being fast.

The Keeper wrote the router in forty lines. A function that took a query type and called the right combination of techniques. No classifier, no heuristics, no rules engine. The agent on the other end of the MCP connection would read the tool description, understand the options, and choose.

The search tool gained a fourth parameter. `query_type`. Default: `"simple"`.

The Keeper ran the tests. Ten passed. The library compiled. The router imported cleanly.

---

### XIII. The Library, Restored

Candlekeep stood different now than it had at the beginning.

The same stone walls. The same ChromaDB humming in its chamber. The same embedding models, still coiled, still hungry. But the library had learned to read its own books. It knew that a chunk about JWT tokens belonged to the Authentication Security Guide, and it said so in every embedding. It knew that a matching fragment was just the beginning — that the real answer lived in the surrounding paragraphs. It knew that some questions needed to be broken apart before they could be answered, and that some answers needed to be checked twice.

Ninety-seven percent precision on the fast path. Eighty-eight percent content match with expansion. One hundred percent precision when it took its time.

The Keeper looked at the open research questions still listed in the diary. Local query expansion. Caching strategies for LLM calls. Technique combinations not yet tested. The adaptive router was a beginning, not an ending.

But the library was open. The shelves were full. And when you asked it a question, it no longer stared back blankly.

It answered.

---

### XIV. The Proving Grounds

The Keeper had built a library that worked. Now the question was whether it would hold.

Eighty documents arrived in a single afternoon. Networking protocols, Linux internals, database architectures, security frameworks, cloud patterns — a thousand pages of technical knowledge generated by a lesser oracle and fed into the ingestion pipeline. Two thousand seven hundred and seventy chunks. Fifteen times the original collection.

The Keeper ran the benchmarks and watched the numbers.

Twenty-six milliseconds. Three milliseconds slower than the small collection. The HNSW index barely noticed the difference — logarithmic scaling meant that ten times the data added almost nothing to the search time. The per-document chunk lookup held. The expansion still ran in single-digit milliseconds. The library was fast at nine documents and fast at eighty.

The precise path — the slow, careful road through the cross-encoder — took just under two seconds. The bottleneck was the reranking model scoring fifteen candidates, not the search itself. Corpus size didn't matter. The cross-encoder would take the same time whether the library held a hundred documents or a hundred thousand.

The Keeper wrote "no bottlenecks identified" in the diary and moved on to harder questions.

---

### XV. The Questions That Need Two Books

Some questions can't be answered by a single scroll.

"How does mutual TLS authentication work in an Istio service mesh running rootless containers?" The answer lived in three different documents — the TLS reference, the service mesh guide, and the container security manual. No single search could retrieve all three. The library would find the most relevant document and return it faithfully, but the other two would sit on their shelves, unread.

The Keeper tested sixteen questions like this. Questions that spanned two documents, three documents, four. The library found the right content fifty-five percent of the time. Good for a single search. Not good enough for a real answer.

But the library wasn't meant to answer these questions alone.

The Keeper split each question by hand, the way an agent would. "How does mutual TLS work?" became three searches: one for TLS handshakes, one for Istio's sidecar proxy, one for rootless container security. Three searches, three sets of results, three documents found.

Ninety-two point five percent content match. Source coverage jumped from forty-four percent to ninety-three. The library hadn't changed. The questions had.

The lesson was simple and the Keeper had already learned it once before, when the complex path was removed from the router: don't make the tool do the agent's job. The library searches. The agent thinks. Each does what it's built for.

---

### XVI. The Fundamentals

With the architecture proven, the Keeper turned to the foundations. Two parameters had been chosen early and never questioned: chunk size and embedding model. Both had been set by intuition — five hundred and twelve characters because it felt right, bge-small because the benchmarks said so months ago. But intuition isn't evidence.

The chunk size test was quick and decisive. Two hundred and fifty-six characters, five hundred and twelve, seven hundred and sixty-eight, one thousand and twenty-four. The Keeper ingested the same documents four times, searched with the same queries, and compared.

The numbers barely moved. Content match ranged from eighty-six to eighty-seven percent across all four sizes. Arcane Recall's expansion was doing what it was designed to do — normalizing the context window regardless of how the text was sliced. Small chunks got expanded into full sections. Large chunks were already full sections. The result was the same.

Five hundred and twelve remained the default. Not because it was dramatically better, but because it wasn't dramatically worse, and changing it would mean re-ingesting every database in production.

The embedding model comparison was more interesting. Three models: MiniLM at twenty-two million parameters, bge-small at thirty-three million, and Nomic at a hundred and thirty-seven million.

MiniLM was the fastest — eighteen milliseconds per query — but it missed things. Two hundred and ninety-eight percent recall against bge-small's three hundred and eighty-four. Thirty percent fewer relevant chunks found. Speed without substance.

Nomic was the most precise. Ninety point four percent precision, the highest of the three. But it ran at forty-seven milliseconds — twice as slow — and took three times longer to ingest. A hundred and thirty-seven million parameters buying three percentage points of precision.

bge-small sat in the middle and won on the metric that mattered most: content match. Eighty-seven point three percent. The chunks it found contained more of the actual answer text than either competitor. For a RAG system, that was the number. Not precision, not recall, not F1. Content. The words the agent needed to answer the question.

---

### XVII. The Wards

The last work was defensive.

The Keeper had noticed that the library answered every question, even the ones it shouldn't. "Quantum entanglement in photosynthesis" returned five results with confident scores, none of them relevant. Vector search has no concept of "I don't know." Every query gets an answer. Every answer has a score. The scores mean nothing when the question has nothing to do with the collection.

The Keeper studied the score distributions. Twenty-three queries, each with a top-result score. The legitimate queries clustered between 0.75 and 1.22. The adversarial query — the quantum entanglement nonsense — scored 0.558. A gap of nearly two-tenths.

A threshold at 0.65. Below that line, the library would return nothing. Above it, results as normal. The Keeper tested it against every query in the benchmark. Zero false negatives. Two true negatives — the adversarial query and a gibberish string both returned empty. The library had learned to say "I don't know."

The second ward was subtler. When connecting to a remote database — a remote ChromaDB instance, populated by someone else — there was no guarantee that the embedding model matched. If the remote database held vectors from MiniLM and the local configuration said bge-small, the searches would return results. They would look normal. The scores would be plausible. And every single result would be wrong, because the vector spaces were incompatible.

The Keeper stored the model name in the collection metadata. On connection, the library checked. If the remote model didn't match the local configuration, it overrode the local setting and logged a warning. No silent failures. No wrong answers dressed in confident scores.

The third ward was the simplest. The embedding models were large — a hundred and thirty megabytes for bge-small alone. If the model wasn't cached locally, the SentenceTransformer library would try to download it. At startup. While the MCP client waited. A thirty-second delay that looked like a hang.

The Keeper added a check. If the model directory didn't exist in the local cache, exit immediately with a clear message. No downloads at startup. No mysterious delays. Run the setup script first, or don't run at all.

---

### XVIII. The Library, Complete

The Keeper closed the research diary at entry twenty-three and looked at what had been built.

Three roads through the library. The simple path at twenty-three milliseconds — Bardic Knowledge in the embeddings, Arcane Recall expanding every result, a relevance threshold filtering the noise. The hybrid road of Wild Magic, merging keywords and semantic meaning for technical precision. The precise path at fifteen hundred milliseconds — the same foundation, plus a cross-encoder examining every candidate with slow, thorough judgment.

Eighty-seven percent content match on the fast path. Ninety-two percent when the agent decomposed complex questions into focused searches. Twenty-six milliseconds at scale with nearly three thousand chunks. No bottlenecks. No silent failures. No wrong answers to wrong questions.

The fundamentals validated: bge-small for embeddings, five hundred and twelve characters for chunks, plus-or-minus two chunks for expansion. Each tested, each confirmed, each documented.

The Keeper set down the pen. The library stood quiet in the late afternoon, its vector spaces humming with the weight of indexed knowledge. Somewhere in those high-dimensional corridors, the answer to the next question was already waiting.

It just needed someone to ask.

---

From the Chronicles of Candlekeep, Volume I > Transcribed by Ran Algawi and his tireless AI Familiar

---

## Apothecary's Appendix

For those who seek the science behind the sorcery, here is the mapping of the library's "spells" to their technical implementations:

| Spell | Technical Implementation | File Path |
| :--- | :--- | :--- |
| **Bardic Knowledge** | Ingestion-time document context prefixing | `src/candlekeep/rag/processor.py` |
| **Bardic Inspiration** | Result-time metadata re-ranking (boosting) | `src/candlekeep/database/vector_store.py` |
| **Arcane Recall** | Intelligent contextual expansion | `src/candlekeep/rag/arcane_recall.py` |
| **Arcane Coalescence** | Window merging of adjacent fragments | `src/candlekeep/rag/arcane_recall.py` |
| **Scholar's Discernment** | Similarity-weighted context pruning | `src/candlekeep/rag/arcane_recall.py` |
| **Divine Insight** | Cross-encoder reranking | `src/candlekeep/rag/reranker.py` |
| **Wild Magic** | Hybrid Search (Vector + BM25 Lexical) | `src/candlekeep/rag/hybrid.py` |
| **Arcane Attunement** | Model pre-loading at startup | `src/candlekeep/mcp/server.py` |
| **The Relevance Ward** | Score-based result filtering | `src/candlekeep/rag/router.py` |
| **Mirror Image** | Query expansion variations (Research only) | `tests/test_mirror_image.py` |
| **Flurry of Blows** | Query decomposition into sub-questions | `tests/test_flurry_of_blows.py` |
| **Illusory Script** | Hypothetical Document Embeddings (HyDE) | `tests/test_illusory_script.py` |
| **The Scrying Window** | Sentence Window Retrieval (Deleted) | `docs/RESEARCH_DIARY.md` (Entry 4) |
| **Embedding Protection** | Model mismatch detection on connection | `src/candlekeep/database/vector_store.py` |
| **Search Router** | Adaptive routing between search paths | `src/candlekeep/rag/router.py` |
