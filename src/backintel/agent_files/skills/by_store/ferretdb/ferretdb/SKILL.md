---
name: ferretdb
description: Analyze a MongoDB-compatible document database through FerretDB.
---

Use list_tables and describe_table to discover collections and sample documents.
run_query accepts a JSON string with collection and pipeline keys. Common stages are
$match, $group, $project, $sort, $limit, $unwind and $lookup. Use $sum:1 for counts;
$count returns no document for an empty input. Dates are ISO strings. Null and missing
fields need explicit treatment. Pipelines are read-only; JavaScript is disabled.

FerretDB implements a subset of MongoDB. If an operator is unsupported, use run_python
to fetch the needed fields through pymongo and calculate with polars or pandas.
Do not silently replace a failed query with a claim. For joins, fetch only relevant
fields and join by the discovered keys. Client access is read-only and there are no
local dataset files. Cite the exact JSON pipeline (evidence kind query) or Python code.
