# Fresh support queue analysis

**Fictional sample.** No customer-performance claim.

**Queue to review: Email.**

Rule: review the channel queue with the highest average time to resolve closed tickets.

| Queue | Tickets | Average resolution time (hours) |
| --- | --- | --- |
| Email | 8 | 12 |
| Chat | 8 | 3.5 |
| Phone | 8 | 2 |

## Supporting tickets

| Ticket | Queue | Resolution time (hours) |
| --- | --- | --- |
| S3-E01 | Email | 9 |
| S3-E02 | Email | 11 |
| S3-E03 | Email | 13 |
| S3-E04 | Email | 12 |
| S3-E05 | Email | 14 |
| S3-E06 | Email | 10 |
| S3-E07 | Email | 15 |
| S3-E08 | Email | 12 |

## Checked findings

- Email has the highest mean.
- Group Email mean is 12.
- Email has 8 records.

## Limits

- These are fictional closed tickets, not measured customer performance.
- The review rule uses observed resolution times for this sample.
- Text interpretation, prediction, and the autonomous agent were not run.

Source: [input.csv](input.csv). Details: [report.json](report.json).
Input SHA-256: `b19bc97f78f66e1d32ee519d0f743b783a9d7c3d16034381efda5e38471309f4`.
Calculation evidence: `322740e832e38077da5dd43a97e239bca63cbd8aa3059887ed2efb281ca2d873`.
