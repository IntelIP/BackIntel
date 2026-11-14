# Numeric evidence at structured completion

The first native reliability campaign found a reserved-case evidence regression:
the candidate reported the correct profit in major currency units, but both cited SQL
queries returned only minor units. The conversion appeared in the prose, not executable
output. The independent evidence evaluator correctly rejected the answer; its score and
the original candidate remain unchanged.

Previously, runtime finalization re-executed every evidence item and rejected execution
errors, but it did not check the reported number against the output. The revised numeric
completion check collects native query cells and successful Python stdout, and requires
the scalar answer to appear in that output. It accepts scientific notation, grouped
numeric text and the existing display-rounding allowance. Booleans and nonfinite values
do not establish a numeric answer. A number in a note or unprinted program source is not
output. Every cited program still runs and any execution failure rejects finalization.

The existing Pydantic/ToolStrategy retry returns a specific error to the analyst, asking
it to put conversion or rounding into the executable evidence and output the final
number. The host does not guess a currency conversion or rewrite the answer. The check
uses no question-specific expected value, oracle, grading reference or hidden data.
Independent correctness, report, refusal and evidence scoring remain unchanged. Numeric
presence is not proof of correctness or full data lineage.

The same reserved batch exposed an answered report with unavailable required metrics:
its current-period mean and change were null even though the method explained that the
comparison could not be calculated. Runtime report finalization now rejects null metric
values and asks the analyst to decline with the missing-information reason. It does not
infer answerability from hidden references or fabricate a complete report. Historical
records remain parseable by the permissive persisted contract.

The initial implementation's offline verification included a real installed
graph that rejects an omitted conversion and then accepts corrected SQL. Additional
tests cover SQL and Python mismatches, printed versus unprinted values, display rounding
and notation, plus partial-report rejection followed by a proper refusal. Ruff, Vulture,
diff and Gitleaks checks passed. This is implementation
evidence, not live qualification of the revised candidate.

The consumed acceptance-v1 reserved worlds cannot qualify a revision as unseen. The
evaluator builder therefore supports an explicit `reserved_generation=2` for the
acceptance split only. Generation 1 remains the default and reproduces its original
identities/data. Generation 2 uses distinct world IDs, periods, financial values,
report distributions and price/delivery inputs. Thirteen answerable references are
independently checked by SQL; four cases require refusal. Its 17 worlds are controlled
variants, not new customer domains. Old manifests and database files remain intact.

The initial prepared follow-up used 63 new responses: 12 candidate original regressions, 17
candidate development responses, and 34 fresh reserved baseline/candidate responses.
The 29 original/development baseline records retain their actual unchanged source and
data/evaluator identities; they are reused rather than relabeled or regenerated.
Models, scoring rules and tolerances remained fixed. Its initial proposed additional
allocation was $2.15, subject to the cumulative allowance. Later staged execution used
the existing allowance as recorded below; no additional spending is approved here.

Local freeze: `data/output/reliability-native-refresh-20261114-r2/proposal.json` in the
canonical operator checkout. It retains source/manifest/policy/data/reference hashes and
the proposed caps. It superseded the first zero-call preparation, which preceded the
second observed failure; both remain retained. The following checkpoint supersedes
the preparation-only state. No v0.0.1 release is claimed.

## Generation-2 result and report-binding revision

The d0d476e04fc7f378 candidate passed 12/12 original and 17/17 development responses,
then 16/17 fresh reserved candidate responses. The generation-2 baseline arm did not
run. All 46 new records are valid; one mandatory reserved result failed evidence
reproduction even though its reported facts were correct. The status label was in the
SQL unit column while the explicitly named metric's value was numeric. The original
data, score and rejected result remain unchanged.

Runtime finalization now also checks explicit report metric/value associations in SQL
and structured Python JSON/JSON-lines output. A label in a unit column or a matching
value under another metric does not repair a contradictory binding. A second query
with the correct value cannot erase a contradictory cited result. Single wide rows
are recognized; several wide population rows are not arbitrarily mapped to one global
metric. Unstructured Python output still has independent evidence grading. No runtime
code imports oracle answers or the benchmark scorer.

The existing finalization feedback asks the analyst to repair its executable output.
Real installed-graph regression checks exercise this repair with unrelated local data.
The current code passes 275 tests with 15 optional skips, plus Ruff/Vulture/secret checks.
The scalar-output and unavailable-metric guards remain in place. The frozen independent
evaluator and tolerances are unchanged; output consistency is not full data lineage or
an independent correctness proof.

Generation 2 is consumed regression evidence. Explicit generation 3 supplies 17 distinct
reserved worlds for the next frozen candidate, preserving both earlier generations and
all old manifests. Thirteen numerical references are independently checked by SQL;
four scenarios require refusal. No generation-3 model inference has run.

The completed revised inference used $1.413655 in conservative estimates. Cumulative
goal usage and retained reservations is $4.92681681225 of the existing $5 authorization.
The next full qualification requires 63 new responses and can reuse 29 unchanged
baseline records. A proposed shared $2.05 cap would keep the total below $7, subject
to owner approval; it supersedes the earlier $6 request because another candidate
revision and fresh reserved generation are now required. No new allowance is implied
by this document, and no release acceptance is claimed.
