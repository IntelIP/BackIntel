# Analysis artifact contract

`backintel.artifacts` turns a JSON analysis specification into a self-contained report bundle.
It uses Matplotlib for PNG/SVG, Plotly for interactive HTML, and openpyxl for workbooks.
No browser, remote font, CDN, map service or rendering service is required.

The module is installed in the sandbox image. Call it from an analysis program:

```python
import json
from backintel.artifacts import render_report

spec = json.load(open('/workspace/report-spec.json'))
manifest = render_report(spec, '/artifacts/report')
print(json.dumps(manifest))
```

The output directory must not already exist. For a revision, use a fresh directory or let
the orchestrator replace the exact previous sandbox output. Existing user files are not
overwritten. The default bundle limit is 64 MiB, within the sandbox's separate storage quota.

See `examples/analysis-report.json` for a complete **synthetic** example. It is authoring
guidance, not a benchmark answer or a measurement of customer outcomes.

## Specification

The canonical schema and analytical instructions are in
[`artifact-contract.md`](../src/backintel/agent_files/docs/artifact-contract.md), packaged
in the sandbox and available through the analyst's instruction filesystem. It documents
source/evidence bindings, table-backed metrics, the five supported chart families and
bounds. Python table evidence must print one JSON object containing `columns` and `rows`;
SQL/native-query evidence must reproduce the same table. The host owns run/source identity.

## Output and trust

The bundle contains `report.html`, `report.json`, `supporting.xlsx`, table CSVs, chart
PNG/SVG/interactive HTML files, and `manifest.json`. The manifest records run identity,
sources, metric definitions/bindings, evidence IDs, MIME types, byte counts and SHA-256 hashes.

The report is responsive, printable and uses local system fonts. Interactive files embed
the installed Plotly JavaScript and declare `connect-src 'none'`; no external resource is
needed. Supporting exact values remain readable below each interactive chart.

Excel cells containing text are forced to text, never formulas. Formula-like CSV text is
prefixed with an apostrophe; the unchanged value remains in JSON and Excel text cells.
Numeric values remain numeric. HTML and script payloads in data are escaped.

`validate_report` checks schema, references, grain, units, finite values and bounds.
`verify_bundle` checks exact file inventory, path/symlink restrictions, hashes, canonical
report HTML and supporting CSV consistency. These checks do **not** prove the supplied
calculation or narrative is true and are not a signature on untrusted files.

The delivery boundary must regenerate the normalized specification using the trusted
renderer in a fresh sandbox after the analyst stops. Do not serve arbitrary HTML or an
agent-edited manifest directly from its writable working directory. Independent source
calculations and benchmark references remain the evaluation harness's responsibility.

## Package sources

New renderer versions were checked on 2026-11-11: Matplotlib 3.11.2, Plotly 7.1.0 and
the existing openpyxl 3.1.5. The sandbox dependency lock supplies exact transitive versions.

- [Matplotlib governance](https://github.com/matplotlib/governance/blob/main/governance.md)
  describes community governance and NumFOCUS affiliation; the
  [license](https://matplotlib.org/stable/project/license.html) records shared development-team copyright.
- [Plotly's company page](https://plotly.com/about-us/) identifies the company maintaining
  its open-source libraries. Its [registry-validated LEI](https://lei.bloomberg.com/leis/view/549300IQLNOF8XICEZ30)
  identifies Technologies Plotly Inc., Canadian legal/headquarters addresses, and natural-person
  direct/ultimate parents. [Real Ventures](https://realventures.com/portfolio/) lists its investment.
  These are documented ownership/control signals; a complete private beneficial-ownership register
  is not published by those sources.
- [openpyxl](https://openpyxl.readthedocs.io/en/stable/) identifies its independent authors,
  volunteer maintenance, license and professional support organizations.

Relevant APIs: [Plotly offline HTML](https://plotly.com/python/interactive-html-export/),
[Matplotlib export](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html),
and [openpyxl formatting](https://openpyxl.readthedocs.io/en/stable/styles.html).
