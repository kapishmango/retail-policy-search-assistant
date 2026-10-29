# Evaluation and error analysis

## Scope

The checked corpus consists of four original fictional retail-policy/product-guide documents, two pages each. The text and PDF versions express the same policy facts. The second page of the PDF product guide is image-only, so its extraction exercises real OCR rather than a mocked text layer.

`python -m policy_search.cli evaluate` writes every question and answer to `reports/evaluation.json`. The fixed development set has ten answerable questions and four unsupported questions. It was used to diagnose behavior and refine retrieval, so the reported 100% rates are development-set outcomes, not generalization claims.

## Manual answer review

| Questions | Expected evidence | Review |
|---|---|---|
| Q01–Q02 | 30-day return window; refund within seven business days after inspection | Correct facts, returns pages 1 and 2 cited |
| Q03–Q04 | Standard delivery 3–5 business days; damaged delivery reported within 48 hours | Correct facts, shipping pages 1 and 2 cited |
| Q05–Q06 | Cotton washed at 30°C; lamp charged with 5V 2A adapter | Correct facts, product-guide pages 1 and 2 cited |
| Q07–Q08 | Discrepancy reported during the same shift; collection held five calendar days | Correct facts, operations pages 1 and 2 cited |
| Q09–Q10 | Defective personalised-item exception; collector's own photo ID and collection code | Correct facts and source pages cited |
| Q11–Q12 | Salary and current cricket result are absent | Correct abstention |
| Q13–Q14 | International delivery price and lamp warranty duration are absent | Correct abstention |

The offline answers quote source sentences. No new policy terms or numerical claims were introduced in the reviewed development answers. An excerpt can still be incomplete: surrounding qualifiers and item-specific rules must be checked on the original page. The keyword test only checks whether an expected phrase is present, not whether all qualifications are correct.

## Failure found and corrected

The first lexical retrieval implementation returned domestic delivery text for an international-price question, and lamp charging instructions for a warranty question. Both retrieved related material without answering the question. It also missed the nominated-collector question due to weak lexical matching.

The revised local encoder stems word forms. A conservative query-concept coverage check refuses offline answers when substantive query concepts are absent from the corpus. This corrected the recorded development examples. It also deliberately increases abstentions for synonyms and paraphrases absent from the small alias list. The threshold and coverage heuristic must be re-evaluated on a separate, larger question set before wider use.

## API mode

The HTTP adapter, embedding result ordering, chat JSON handling, citation validation and error redaction are tested with mocked responses. A fabricated citation label causes abstention. No live provider calls were made; generated-answer accuracy, costs, latency and prompt-injection resistance have not been measured.

Citation-label validation does not verify semantic entailment. A model can return a valid page label with an unsupported claim. Passage-as-data instructions and evidence display are useful controls, not a complete solution.

## Known limitations

- No conflict resolution across document versions or policy effective dates.
- OCR can misread numbers, table structure and footnotes. The sample scan is clean; it is not a stress test for poor photography or handwriting.
- Short page fragments and chunk boundaries can separate an exception from a general rule.
- The local embeddings are lexical. A semantic provider may improve recall, but needs its own evaluation and threshold calibration.
- The extractive overview takes one sentence from successive chunks, so it is not a comprehensive summary.
- A local in-memory index is rebuilt after source changes. There is no persistent vector database, authentication or multi-user isolation.
- English OCR and token handling only; multilingual documents need separate testing.

## Next evaluation

Create a held-out set with paraphrases, conflicting policy versions, numeric exceptions, adversarial instructions in documents, unrelated questions sharing keywords, noisy scans, and multi-page answers. Have a reviewer score source relevance, answer completeness, groundedness and correct abstention separately. Report errors rather than only a single aggregate score.
