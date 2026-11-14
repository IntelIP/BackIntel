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

Offline verification passed 262 tests with 15 optional skips, including a real installed
graph that rejects an omitted conversion and then accepts corrected SQL. Additional
tests cover SQL and Python mismatches, printed versus unprinted values, display rounding
and notation. Ruff, Vulture, diff and Gitleaks checks passed. This is implementation
evidence, not live qualification of the revised candidate.

The consumed acceptance-v1 reserved worlds cannot qualify a revision as unseen. The
evaluator builder therefore supports an explicit `reserved_generation=2` for the
acceptance split only. Generation 1 remains the default and reproduces its original
identities/data. Generation 2 uses distinct world IDs, periods, financial values,
report distributions and price/delivery inputs. Thirteen answerable references are
independently checked by SQL; four cases require refusal. Its 17 worlds are controlled
variants, not new customer domains. Old manifests and database files remain intact.

The prepared follow-up uses 63 new responses: 12 candidate original regressions, 17
candidate development responses, and 34 fresh reserved baseline/candidate responses.
The 29 original/development baseline records retain their actual unchanged source and
data/evaluator identities; they are reused rather than relabeled or regenerated.
Models, scoring rules and tolerances remain fixed. The proposed additional allocation
is $2.15, subject to the cumulative allowance: the existing $5 authorization does not
cover the full proposed envelope. No additional spending is approved by this document.

Local freeze: `data/output/reliability-native-refresh-20261114/proposal.json` in the
canonical operator checkout. It retains source/manifest/policy/data/reference hashes and
the proposed caps. No live revised-candidate result or v0.0.1 release is claimed.
