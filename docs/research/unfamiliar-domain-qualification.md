# Unfamiliar-domain data qualification

Prepared 2026-11-13 UTC for INT-440 / INT-441, from main `51846a4`.
This is an evaluator-owned preparation artifact, not a model-performance result.

## Question and decision

Which three real, non-retail sources can support BackIntel's next cold-start analysis
benchmark, without competition notebooks, hidden answers or unqualified source rights?
The decision is which exact files and task boundaries to prepare for v0.0.2. It does not
authorize live scoring, a model change, a larger compute allocation or deployment.

## Conclusion

The bounded source package is acquired, checksum-pinned and profiled. Transportation and
household energy are development domains. Weather is reserved as an entire domain, with
its seven precise questions and profile kept under ignored evaluator-only storage.
There are 21 specified tasks: six challenges and one discovery report per domain.

The package has **18 independently cross-checked fixed challenge references**, with
[raw-file packaging and mapped grading integrated](unfamiliar-package-integration.md);
see the [reference handoff](unfamiliar-reference-handoff.md).
It is not ready to claim successful domain transfer. No live model or judge was invoked;
the subsequent execution check uses a fake scripted model.
INT-440 also requires a source supporting the real large-data target: these acquired files
do not complete the exact >=10 GiB corpus qualification, which remains open under INT-446.

## Confirmed source facts

| Domain / split | Frozen selection | Measured size and grain | Rights and source |
| --- | --- | --- | --- |
| Transportation / development | NYC TLC green taxi, January 2023; zone lookup | 68,211 trip rows / 20 columns; 265 zone rows / 4 columns. Parquet 1,427,002 bytes, lookup 12,331 bytes; Parquet uncompressed column chunks 2,136,114 bytes | [Official TLC source](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), [NYC Open Data use FAQ](https://www.nyc.gov/opendata/get-started/FAQs), [NYC terms](https://www.nyc.gov/main/terms-of-use). AWS's [dataset registry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/) explicitly names TLC as manager and those terms as the license. |
| Household energy / development | UCI Individual Household Electric Power Consumption | 2,075,259 minute rows / 9 columns, one household in France; ZIP 20,640,916 bytes; extracted text 132,960,755 bytes | [UCI dataset and CC BY 4.0 declaration](https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption). Credit Hebrail and Berard, DOI 10.24432/C58K54; preserve the license link and note extraction/other transformations. |
| Weather / reserved | NOAA GSOD 2023, US station IDs 74486094789, 72509014739, 72278023183 | 1,093 station-day rows / 28 columns across three files; 266,542 bytes total | [NCEI C00516 metadata](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C00516/html), [GSOD README](https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt), [NOAA use guidance](https://www.noaa.gov/office-education/outreach-communication/faq). Credit NOAA/NCEI and identify the subset/access date. |

Exact URLs, acquisition timestamps, HTTP revision metadata, byte lengths and SHA-256 values
are in [sources.json](../../benchmarks/unfamiliar/unfamiliar-v1/sources.json). Original files
are retained byte-for-byte. The only transformation so far is extraction of the single
declared energy ZIP member; its separate hash is pinned. No imputation, resampling, row
replication or learned/synthetic generation is used.

The NOAA README specifically restricts commercial re-export of **non-US** locations.
This selection contains only US stations. Its station names were checked for the published
US designation. Do not extend this permission conclusion to other countries or a global
GSOD mirror. The standard NOAA no-endorsement condition and source-quality disclaimer apply.
NYC's general site copyright notice is not a CC0 declaration; the package records the actual
Open Data use statement and terms instead of assigning an invented license.

## Technology and provider provenance

Source access is through NYC government and its official Amazon CloudFront download links,
the University of California Irvine repository, and NOAA/NCEI. The [TLC registry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/)
identifies the managed AWS source; [Amazon](https://www.aboutamazon.com/about-us) identifies
its cloud-computing business. [UCI's repository page](https://archive.ics.uci.edu/about)
identifies the university research archive and NSF support. [NOAA](https://www.noaa.gov/about-our-agency)
is a US Department of Commerce agency headquartered in Washington, DC.

These are recorded observations distributed by US government/university publishers, not
model-generated datasets. No model lineage is introduced, no Chinese vendor service is
selected, and no new SDK, framework or package is installed. Profiling reuses the project's
existing DuckDB, PyArrow and HTTPX dependencies. This conclusion concerns the selected
publishers/download services and declared generation provenance; it is not a certification
of every historic measuring instrument or each upstream taxi vendor's entire supply chain.

## Material quality findings and consequences

| Observation on the frozen development files | Consequence for the task contract |
| --- | --- |
| Four taxi pickups lie outside January 2023; the range starts in 2009 and extends into February 2023 | The monthly filename is not a validated observation cutoff. Apply the question's explicit pickup window. |
| 61 trips have nonpositive recorded duration; 179 have negative total amounts | Duration questions explicitly define eligible records. Signed monetary totals remain signed; negative amounts are not silently deleted as universal corruption. |
| 4,324 trips lack payment type/passenger count; `ehail_fee` is entirely null | Preserve an unknown payment group. Do not infer missing passenger counts or fees as zero. |
| No exact duplicate trip rows; both zone joins cover all trip IDs; lookup keys are unique | Zone enrichment can preserve trip grain. Do not invent a unique trip/business identity or infer repeated customers from these rows. |
| 25,979 energy active-power values are `?`; matching submeter values can be blank | A plain SQL NULL count misses missing measurements. Normalize declared sentinels for each calculation, without imputing energy. |
| Energy timestamps are unique and span 2006-12-16 17:24 to 2010-11-26 21:02 | Restrict acceptance questions to the declared periods; record coverage separately from the availability of timestamp rows. Timezone is not established. |

Taxi quantities use recorded miles, timestamps and USD amounts. The [green-trip dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_green.pdf)
warns that cash tips are absent from recorded tips/totals. Its current 2025 schema includes
later fields; the actual 2023 schema, not the current dictionary's column count, controls.
TLC does not warrant that submitted trips are complete or accurate. No driver expenses or
profit ledger is supplied.

The energy source distinguishes minute-averaged kW from submeter Wh. Its narrative describes
missing measurements, although its variable table marks individual fields as having none.
Observed bytes take precedence for missing-value handling. A single household is not a
building portfolio or representative estimate of all households. Tariffs and causal controls
are absent. These limits shape the refusal case and permitted descriptive claims.

Weather quality/flag counts remain in the evaluator-only profile. The ordinary source
documentation explains per-field sentinels, precipitation flags, observation counts and
observation-period limitations. Do not replace missing precipitation with zero or assert
that every daily extreme/total is an exact local-calendar-day value. The task contract uses
the supplied date labels and specified flags; it makes no unsupported calendar conversion.

## Inferences and alternatives

These sources cover different failure mechanisms: event/lookup joins and signed payments;
power-versus-energy units and missing minute measurements; and daily environmental summaries
with sentinel/flag semantics. That is why they were selected, rather than maximizing rows.
This is a proposed coverage rationale, not evidence that BackIntel transfers across domains.

UCI household energy replaces the **candidate** ASHRAE competition source for this first
bounded package because its reusable source terms are explicit and no competition account,
rules acceptance or solution notebook is needed. No claim is made that ASHRAE terms were
violated or that the alternative duplicates ASHRAE's building-portfolio scope. The initially
examined UCI Appliances dataset was not selected; its mixed weather covariates would blur the
cleaner separation chosen here between development energy and reserved weather.

## Reproduction and outstanding work

From this checkout and its existing environment:

```bash
uv run python scripts/qualify_unfamiliar_data.py \
  --download --output data/unfamiliar-v1/evaluator/profile-new.json
```

The command fetches missing pinned files, refuses changed size/checksum, extracts only the
declared member, and writes a new profile. Omit `--download` for offline verification.
Downloads total 22,358,079 bytes including the weather README. Raw data, acquisition receipts
and profiles stay in ignored `data/unfamiliar-v1/`; do not mount the evaluator directory into
an analyst. The retained manifest-bound profile is `data/unfamiliar-v1/evaluator/profile-v3.json`;
earlier profiles remain available with their corrections recorded in the reference handoff.

Remaining acceptance work:

1. Finish independent discovery-claim and refusal-explanation verification under INT-443.
   Mapped fixed-reference grading is implemented; generic narrative scoring remains incomplete.
2. Use the qualified per-file package path under INT-442; the development packages and one
   scripted real-source SmolVM run are retained. Do not give the analyst this qualification
   report, profiles, references or evaluator code.
3. Freeze the executable graders, model/candidate identities and separately authorized
   finite allowance before live evaluation. Follow the [task contract](../../benchmarks/unfamiliar/unfamiliar-v1/task-contract.md).
4. Freeze a natural >=10 GiB corpus and compatible runtime under INT-446. NOAA's [ISD source
   overview](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)
   documents a much larger source family, and TLC offers many monthly partitions. Neither
   fact replaces an exact eligible selection, measured bytes, hashes and large-data execution.

Sources and terms above were retrieved on 2026-11-13. This report preserves their use-specific
interpretation; source permissions or revisions must be rechecked if the selection changes.
