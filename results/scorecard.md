# BackIntel v2 scorecard

## Coverage: largest observed cohort per dataset, store and level

Levels: 1 single table, 2 joins/multi-step, 3 messy data, 4 cross-store, 5 standing problems, 6 ambient replay with planted changes, 7 scale. Stores named `multi:` connect two stores at once.
For each level the largest observed cohort is used, then the latest such experiment. Subset probes stay in the experiment list. Legacy and revised judges have different versions; their method scores are not directly comparable. Cost is provider-reported analyst cost only; JSON also records runs with incomplete cost telemetry. Subset probes are not full suites.

| dataset | store | level | n | fully supported | correct | evidence | judge | median s | cost USD |
|---|---|---|---|---|---|---|---|---|---|
| olist | clickhouse | 1 | 8 | 100% | 100% | 100% | 0.844 | 17.3 | 0.0093 |
| olist | clickhouse | 2 | 8 | 100% | 100% | 100% | 0.766 | 21.7 | 0.0125 |
| olist | clickhouse | 3 | 8 | 100% | 100% | 100% | 0.781 | 20.5 | 0.0112 |
| olist | ferretdb | 1 | 8 | 100% | 100% | 100% | 0.75 | 15.4 | 0.0090 |
| olist | ferretdb | 2 | 8 | 100% | 100% | 100% | 0.75 | 27.9 | 0.0137 |
| olist | ferretdb | 3 | 8 | 88% | 88% | 86% | 0.667 | 19.8 | 0.0162 |
| olist | files | 1 | 8 | 100% | 100% | 100% | 0.727 | 11.9 | 0.0076 |
| olist | files | 2 | 8 | 100% | 100% | 100% | 0.686 | 18.4 | 0.0126 |
| olist | files | 3 | 8 | 100% | 100% | 100% | 0.748 | 15.6 | 0.0091 |
| olist | files-mixed | 1 | 1 | 100% | 100% | 100% | 0.875 | 15.0 | 0.0009 |
| olist | files-mixed | 2 | 1 | 100% | 100% | 100% | 0.875 | 18.4 | 0.0012 |
| olist | files-mixed | 3 | 1 | 100% | 100% | 100% | 0.875 | 16.6 | 0.0015 |
| olist | lake-iceberg | 1 | 8 | 100% | 100% | 100% | 0.844 | 15.4 | 0.0077 |
| olist | lake-iceberg | 2 | 8 | 100% | 100% | 100% | 0.797 | 23.6 | 0.0104 |
| olist | lake-iceberg | 3 | 8 | 100% | 100% | 100% | 0.75 | 20.1 | 0.0094 |
| olist | lake-parquet | 1 | 8 | 100% | 100% | 100% | 0.716 | 13.7 | 0.0075 |
| olist | lake-parquet | 2 | 8 | 100% | 100% | 100% | 0.662 | 18.2 | 0.0110 |
| olist | lake-parquet | 3 | 8 | 100% | 100% | 100% | 0.721 | 13.9 | 0.0083 |
| olist | multi | 4 | 6 | 100% | 100% | 100% | 0.671 | 22.8 | 0.0116 |
| olist | postgres | 1 | 8 | 100% | 100% | 100% | 0.712 | 14.5 | 0.0080 |
| olist | postgres | 2 | 8 | 100% | 100% | 100% | 0.699 | 16.5 | 0.0101 |
| olist | postgres | 3 | 8 | 100% | 100% | 100% | 0.761 | 13.8 | 0.0092 |
| olist | sqlite | 1 | 8 | 100% | 100% | 100% | 0.717 | 25.8 | 0.0091 |
| olist | sqlite | 2 | 8 | 100% | 100% | 100% | 0.674 | 38.7 | 0.0152 |
| olist | sqlite | 3 | 8 | 100% | 100% | 100% | 0.727 | 31.5 | 0.0105 |
| olist | sqlite | 5 | 3 | 100% | 100% | 100% | 0.792 | 57.2 | 0.0119 |
| olist | sqlite | 6 | 14 | 86% | 93% | 93% | 0.723 | 50.1 | 0.0573 |
| online_retail_ii | files | 1 | 8 | 100% | 100% | 100% | 0.667 | 22.2 | 0.0121 |
| online_retail_ii | files | 2 | 3 | 100% | 100% | 100% | 0.671 | 19.0 | 0.0037 |
| online_retail_ii | files | 3 | 9 | 100% | 100% | 100% | 0.735 | 22.3 | 0.0149 |
| online_retail_ii | lake-parquet | 1 | 8 | 100% | 100% | 100% | 0.781 | 17.0 | 0.0089 |
| online_retail_ii | lake-parquet | 2 | 3 | 100% | 100% | 100% | 0.75 | 15.1 | 0.0031 |
| online_retail_ii | lake-parquet | 3 | 9 | 100% | 100% | 100% | 0.796 | 20.3 | 0.0123 |
| online_retail_ii | postgres | 1 | 8 | 100% | 100% | 100% | 0.72 | 18.3 | 0.0083 |
| online_retail_ii | postgres | 2 | 3 | 100% | 100% | 100% | 0.688 | 21.3 | 0.0037 |
| online_retail_ii | postgres | 3 | 9 | 100% | 100% | 100% | 0.761 | 17.9 | 0.0126 |
| online_retail_ii | sqlite | 1 | 8 | 100% | 100% | 100% | 0.699 | 29.0 | 0.0071 |
| online_retail_ii | sqlite | 2 | 3 | 100% | 100% | 100% | 0.725 | 17.9 | 0.0030 |
| online_retail_ii | sqlite | 3 | 9 | 100% | 100% | 100% | 0.752 | 22.2 | 0.0095 |
| tpch_sf1 | lake-parquet | 7 | 6 | 100% | 100% | 100% | 0.721 | 15.1 | 0.0077 |

## All experiments

Scores are means over scenarios. `correct` compares the answer with the independently computed reference within tolerance; `evidence` re-executes the cited queries and checks they produce the answered value; `abstention` checks the agent answered when it could and declined when it could not; `judge` is an LLM rubric on method and caveats (0–1); `fully supported` requires correct + evidence + abstention.

| experiment | level | n | correct | evidence | abstention | judge | fully supported | errors | median s | cost USD | tool calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| olist-clickhouse-gpt-6-luna-L123-20261110-0152-62911294 | 1 | 8 | 100% | 100% | 100% | 0.844 | 100% | 0 | 17.3 | 0.0093 | 8.5 |
| olist-clickhouse-gpt-6-luna-L123-20261110-0152-62911294 | 2 | 8 | 100% | 100% | 100% | 0.766 | 100% | 0 | 21.7 | 0.0125 | 10.125 |
| olist-clickhouse-gpt-6-luna-L123-20261110-0152-62911294 | 3 | 8 | 100% | 100% | 100% | 0.781 | 100% | 0 | 20.5 | 0.0112 | 9.5 |
| olist-ferretdb-gpt-6-luna-L123-20261110-0159-9f804e28 | 1 | 8 | 100% | 100% | 100% | 0.75 | 100% | 0 | 15.4 | 0.0090 | 7.75 |
| olist-ferretdb-gpt-6-luna-L123-20261110-0159-9f804e28 | 2 | 8 | 100% | 100% | 100% | 0.75 | 100% | 0 | 27.9 | 0.0137 | 9.25 |
| olist-ferretdb-gpt-6-luna-L123-20261110-0159-9f804e28 | 3 | 8 | 88% | 86% | 88% | 0.667 | 88% | 1 | 19.8 | 0.0162 | 10.625 |
| olist-files-gpt-6-luna-L123-20261110-0127-240c2aa3 | 1 | 8 | 100% | 100% | 100% | 0.727 | 100% | 0 | 11.9 | 0.0076 | 6.5 |
| olist-files-gpt-6-luna-L123-20261110-0127-240c2aa3 | 2 | 8 | 100% | 100% | 100% | 0.686 | 100% | 0 | 18.4 | 0.0126 | 8.125 |
| olist-files-gpt-6-luna-L123-20261110-0127-240c2aa3 | 3 | 8 | 100% | 100% | 100% | 0.748 | 100% | 0 | 15.6 | 0.0091 | 7.375 |
| olist-files-gpt-6-luna-L123-20261110-0213-b3df2153 | 1 | 1 | 0% | 0% | 0% | 0.0 | 0% | 1 | 0.6 | 0.0000 | 0.0 |
| olist-files-gpt-6-luna-L123-20261110-0213-b3df2153 | 2 | 1 | 0% | 0% | 0% | 0.0 | 0% | 1 | 20.2 | 0.0016 | 0.0 |
| olist-files-gpt-6-luna-L123-20261110-0213-b3df2153 | 3 | 1 | 0% | 0% | 0% | 0.0 | 0% | 1 | 0.7 | 0.0000 | 0.0 |
| olist-files-gpt-6-luna-L123-20261110-0218-d42e11ba | 1 | 1 | 100% | 100% | 100% | 0.875 | 100% | 0 | 15.0 | 0.0009 | 6.0 |
| olist-files-gpt-6-luna-L123-20261110-0218-d42e11ba | 2 | 1 | 100% | 100% | 100% | 0.875 | 100% | 0 | 18.4 | 0.0012 | 7.0 |
| olist-files-gpt-6-luna-L123-20261110-0218-d42e11ba | 3 | 1 | 100% | 100% | 100% | 0.875 | 100% | 0 | 16.6 | 0.0015 | 8.0 |
| olist-lake-iceberg-gpt-6-luna-L123-20261110-0202-d7b5fda6 | 1 | 8 | 100% | 100% | 100% | 0.844 | 100% | 0 | 15.4 | 0.0077 | 7.5 |
| olist-lake-iceberg-gpt-6-luna-L123-20261110-0202-d7b5fda6 | 2 | 8 | 100% | 100% | 100% | 0.797 | 100% | 0 | 23.6 | 0.0104 | 8.625 |
| olist-lake-iceberg-gpt-6-luna-L123-20261110-0202-d7b5fda6 | 3 | 8 | 100% | 100% | 100% | 0.75 | 100% | 0 | 20.1 | 0.0094 | 8.0 |
| olist-lake-parquet-gpt-6-luna-L123-20261110-0120-bd57ec84 | 1 | 8 | 100% | 100% | 100% | 0.716 | 100% | 0 | 13.7 | 0.0075 | 7.75 |
| olist-lake-parquet-gpt-6-luna-L123-20261110-0120-bd57ec84 | 2 | 8 | 100% | 100% | 100% | 0.662 | 100% | 0 | 18.2 | 0.0110 | 9.5 |
| olist-lake-parquet-gpt-6-luna-L123-20261110-0120-bd57ec84 | 3 | 8 | 100% | 100% | 100% | 0.721 | 100% | 0 | 13.9 | 0.0083 | 8.75 |
| olist-multi-gpt-6-luna-L4-20261110-0130-84ecd951 | 4 | 6 | 100% | 100% | 100% | 0.671 | 100% | 0 | 22.8 | 0.0116 | 10.0 |
| olist-postgres-gpt-6-luna-L123-20261110-0107-9ffa089e | 1 | 8 | 100% | 100% | 100% | 0.712 | 100% | 0 | 14.5 | 0.0080 | 7.625 |
| olist-postgres-gpt-6-luna-L123-20261110-0107-9ffa089e | 2 | 8 | 100% | 100% | 100% | 0.699 | 100% | 0 | 16.5 | 0.0101 | 8.875 |
| olist-postgres-gpt-6-luna-L123-20261110-0107-9ffa089e | 3 | 8 | 100% | 100% | 100% | 0.761 | 100% | 0 | 13.8 | 0.0092 | 9.125 |
| olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8 | 1 | 8 | 100% | 88% | 100% | 0.706 | 88% | 0 | 10.6 | 0.0062 | 6.875 |
| olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8 | 2 | 8 | 62% | 50% | 62% | 0.436 | 50% | 3 | 21.1 | 0.0086 | 7.875 |
| olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8 | 3 | 8 | 88% | 83% | 88% | 0.641 | 88% | 1 | 10.9 | 0.0064 | 7.0 |
| olist-sqlite-gpt-6-luna-L123-20261110-0054-10696f07 | 1 | 8 | 100% | 100% | 100% | 0.717 | 100% | 0 | 25.8 | 0.0091 | 8.625 |
| olist-sqlite-gpt-6-luna-L123-20261110-0054-10696f07 | 2 | 8 | 100% | 100% | 100% | 0.674 | 100% | 0 | 38.7 | 0.0152 | 10.75 |
| olist-sqlite-gpt-6-luna-L123-20261110-0054-10696f07 | 3 | 8 | 100% | 100% | 100% | 0.727 | 100% | 0 | 31.5 | 0.0105 | 9.0 |
| olist-sqlite-gpt-6-luna-L13-20261110-0041-e694c237 | 1 | 1 | 100% | 100% | 100% | 0.662 | 100% | 0 | 12.7 | 0.0008 | 7.0 |
| olist-sqlite-gpt-6-luna-L13-20261110-0041-e694c237 | 3 | 1 | 100% | – | 100% | 0.525 | 100% | 0 | 16.5 | 0.0016 | 8.0 |
| olist-sqlite-gpt-6-luna-L5-20261110-0100-d92cefa5 | 5 | 3 | 100% | 100% | 100% | 0.729 | 100% | 0 | 57.0 | 0.0122 | 15.333 |
| olist-sqlite-gpt-6-luna-L56-20261110-0200-4a67b0ab | 5 | 3 | 100% | 100% | 100% | 0.792 | 100% | 0 | 57.2 | 0.0119 | 15.333 |
| olist-sqlite-gpt-6-luna-L56-20261110-0200-4a67b0ab | 6 | 14 | 93% | 93% | 100% | 0.723 | 86% | 0 | 50.1 | 0.0573 | 13.214 |
| olist-sqlite-gpt-6-luna-L6-20261110-0104-e7d9b926 | 6 | 8 | 100% | 100% | 100% | 0.691 | 100% | 0 | 64.1 | 0.0415 | 12.875 |
| online_retail_ii-files-gpt-6-luna-L123-20261110-0123-14e63e92 | 1 | 8 | 100% | 100% | 100% | 0.667 | 100% | 0 | 22.2 | 0.0121 | 7.5 |
| online_retail_ii-files-gpt-6-luna-L123-20261110-0123-14e63e92 | 2 | 3 | 100% | 100% | 100% | 0.671 | 100% | 0 | 19.0 | 0.0037 | 6.333 |
| online_retail_ii-files-gpt-6-luna-L123-20261110-0123-14e63e92 | 3 | 9 | 100% | 100% | 100% | 0.735 | 100% | 0 | 22.3 | 0.0149 | 8.556 |
| online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0116-2206350b | 1 | 8 | 100% | 100% | 100% | 0.706 | 100% | 0 | 17.2 | 0.0086 | 8.375 |
| online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0116-2206350b | 2 | 3 | 100% | 100% | 100% | 0.7 | 100% | 0 | 19.8 | 0.0037 | 8.333 |
| online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0116-2206350b | 3 | 9 | 78% | 71% | 100% | 0.77 | 78% | 0 | 17.4 | 0.0132 | 9.444 |
| online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0209-2368f83f | 1 | 8 | 100% | 100% | 100% | 0.781 | 100% | 0 | 17.0 | 0.0089 | 8.5 |
| online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0209-2368f83f | 2 | 3 | 100% | 100% | 100% | 0.75 | 100% | 0 | 15.1 | 0.0031 | 8.0 |
| online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0209-2368f83f | 3 | 9 | 100% | 100% | 100% | 0.796 | 100% | 0 | 20.3 | 0.0123 | 9.111 |
| online_retail_ii-postgres-gpt-6-luna-L123-20261110-0103-2476b1cb | 1 | 8 | 100% | 100% | 100% | 0.72 | 100% | 0 | 18.3 | 0.0083 | 7.75 |
| online_retail_ii-postgres-gpt-6-luna-L123-20261110-0103-2476b1cb | 2 | 3 | 100% | 100% | 100% | 0.688 | 100% | 0 | 21.3 | 0.0037 | 8.333 |
| online_retail_ii-postgres-gpt-6-luna-L123-20261110-0103-2476b1cb | 3 | 9 | 100% | 100% | 100% | 0.761 | 100% | 0 | 17.9 | 0.0126 | 8.889 |
| online_retail_ii-sqlite-gpt-6-luna-L123-20261110-0049-44f91d72 | 1 | 8 | 100% | 100% | 100% | 0.699 | 100% | 0 | 29.0 | 0.0071 | 7.125 |
| online_retail_ii-sqlite-gpt-6-luna-L123-20261110-0049-44f91d72 | 2 | 3 | 100% | 100% | 100% | 0.725 | 100% | 0 | 17.9 | 0.0030 | 6.667 |
| online_retail_ii-sqlite-gpt-6-luna-L123-20261110-0049-44f91d72 | 3 | 9 | 100% | 100% | 100% | 0.752 | 100% | 0 | 22.2 | 0.0095 | 7.111 |
| tpch_sf1-lake-parquet-gpt-6-luna-L7-20261110-0132-bc9f6278 | 7 | 6 | 100% | 100% | 100% | 0.721 | 100% | 0 | 15.1 | 0.0077 | 8.833 |

## Experiments

- **olist-clickhouse-gpt-6-luna-L123-20261110-0152-62911294**: dataset=olist, store=clickhouse:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=f4af5b40a93b, source_version=e8fb1c055a85f6b7, reference_version=bfec586d7f5cbcc4, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **olist-ferretdb-gpt-6-luna-L123-20261110-0159-9f804e28**: dataset=olist, store=ferretdb:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=f4af5b40a93b, source_version=e83a928861fcfa4a, reference_version=bfec586d7f5cbcc4, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **olist-files-gpt-6-luna-L123-20261110-0127-240c2aa3**: dataset=olist, store=files:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-files-gpt-6-luna-L123-20261110-0213-b3df2153**: dataset=olist, store=files-mixed:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=3ae47ed328d2, source_version=af9aa40fa92deabe, reference_version=bfec586d7f5cbcc4, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **olist-files-gpt-6-luna-L123-20261110-0218-d42e11ba**: dataset=olist, store=files-mixed:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=3ae47ed328d2, source_version=fb9819937249cd84, reference_version=bfec586d7f5cbcc4, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **olist-lake-iceberg-gpt-6-luna-L123-20261110-0202-d7b5fda6**: dataset=olist, store=lake-iceberg:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=f4af5b40a93b, source_version=6395695d60b0c2f3, reference_version=bfec586d7f5cbcc4, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **olist-lake-parquet-gpt-6-luna-L123-20261110-0120-bd57ec84**: dataset=olist, store=lake-parquet:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-multi-gpt-6-luna-L4-20261110-0130-84ecd951**: dataset=olist, store=multi:postgres:olist_orders+sqlite:olist_catalog, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-postgres-gpt-6-luna-L123-20261110-0107-9ffa089e**: dataset=olist, store=postgres:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8**: dataset=olist, store=sqlite:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=061c84afe601, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-sqlite-gpt-6-luna-L123-20261110-0054-10696f07**: dataset=olist, store=sqlite:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=d9cc38a83a90, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-sqlite-gpt-6-luna-L13-20261110-0041-e694c237**: dataset=olist, store=sqlite:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=061c84afe601, source_version=None, reference_version=None, judge_version=None, sandbox=docker, git_sha=c6de6ae
- **olist-sqlite-gpt-6-luna-L5-20261110-0100-d92cefa5**: dataset=olist, store=sqlite:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **olist-sqlite-gpt-6-luna-L56-20261110-0200-4a67b0ab**: dataset=olist, store=sqlite:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=f4af5b40a93b, source_version=7513f1ae1389c364, reference_version=bfec586d7f5cbcc4, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **olist-sqlite-gpt-6-luna-L6-20261110-0104-e7d9b926**: dataset=olist, store=sqlite:olist, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **online_retail_ii-files-gpt-6-luna-L123-20261110-0123-14e63e92**: dataset=online_retail_ii, store=files:online_retail_ii, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0116-2206350b**: dataset=online_retail_ii, store=lake-parquet:online_retail_ii, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0209-2368f83f**: dataset=online_retail_ii, store=lake-parquet:online_retail_ii, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=3ae47ed328d2, source_version=b4d986340c3219ad, reference_version=7e239104047c9ec2, judge_version=fca43a717d4f, sandbox=docker, git_sha=c6de6ae
- **online_retail_ii-postgres-gpt-6-luna-L123-20261110-0103-2476b1cb**: dataset=online_retail_ii, store=postgres:online_retail_ii, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **online_retail_ii-sqlite-gpt-6-luna-L123-20261110-0049-44f91d72**: dataset=online_retail_ii, store=sqlite:online_retail_ii, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=061c84afe601, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae
- **tpch_sf1-lake-parquet-gpt-6-luna-L7-20261110-0132-bc9f6278**: dataset=tpch_sf1, store=lake-parquet:tpch_sf1, model=openrouter/openai/gpt-6-luna, judge_model=openrouter/anthropic/claude-haiku-5.5, method_version=44b3b721dc63, source_version=None, reference_version=None, judge_version=00977b601516, sandbox=docker, git_sha=c6de6ae

## Failures and partial results (14)

- `olist-l3-07` (L3, olist-ferretdb-gpt-6-luna-L123-20261110-0159-9f804e28; agent execution limit): GraphRecursionError: Recursion limit of 80 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.
For
- `olist-l2-04` (L2, olist-files-gpt-6-luna-L123-20261110-0213-b3df2153; infrastructure): ValueError: {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', '
- `olist-l3-05` (L3, olist-files-gpt-6-luna-L123-20261110-0213-b3df2153; infrastructure): ValueError: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add c
- `olist-l1-01` (L1, olist-files-gpt-6-luna-L123-20261110-0213-b3df2153; infrastructure): ValueError: {'message': 'This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add c
- `olist-l2-04` (L2, olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8; historical harness error): ToolException: Query exceeded 60s and was stopped.
- `olist-l3-05` (L3, olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8; historical harness error): ToolException: Query exceeded 60s and was stopped.
- `olist-l2-03` (L2, olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8; evidence): answered ['SP', 'PR', 'MG', 'RJ', 'SC'] (derived from rows), expected ['SP', 'PR', 'MG', 'RJ', 'SC'] | evidence: 1 evidence item(s) re-executed; value not found in output
- `olist-l2-08` (L2, olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8; historical harness error): ToolException: Query exceeded 60s and was stopped.
- `olist-l2-05` (L2, olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8; historical harness error): ToolException: Query exceeded 60s and was stopped.
- `olist-l1-05` (L1, olist-sqlite-gpt-6-luna-L123-20261110-0042-19bac9b8; evidence): answered ['SP', 'RJ', 'MG'] (derived from rows), expected ['SP', 'RJ', 'MG'] | evidence: 1 evidence item(s) re-executed; value not found in output
- `olist-l6-repeat-2017-09` (L6, olist-sqlite-gpt-6-luna-L56-20261110-0200-4a67b0ab; evidence): 4/4 facts present
- `olist-l6-2018-03` (L6, olist-sqlite-gpt-6-luna-L56-20261110-0200-4a67b0ab; answer/format): 12/12 facts present; missing, duplicate or unexpected metric identifiers
- `orii-l3-01` (L3, online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0116-2206350b; answer/format): answered 12133.0, expected 34335.0 (tol {'abs': 0.0}) | evidence: 2 evidence item(s) re-executed; value not found in output; query failed on re-execution: DuckDB error: Binder Error: Ref
- `orii-l3-02` (L3, online_retail_ii-lake-parquet-gpt-6-luna-L123-20261110-0116-2206350b; answer/format): answered 1259083.75, expected 821452.7299999999 (tol {'rel': 0.002}) | evidence: 1 evidence item(s) re-executed; value not found in output; query failed on re-execution: DuckDB error: Binder Error: Ref
