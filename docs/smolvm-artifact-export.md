# SmolVM artifact export fix — INT-498

Large binary reads and report exports now use SmolVM's native stdin/stdout pipes
(`-i`, without a pseudo-terminal) rather than its capped `--stream` command-output
path. Stdin is explicitly closed for downloads. The trusted guest wrapper still
applies the same analyst UID, read-only root and process limits. Existing archive
validation, file/byte limits, deadlines and partial-output cleanup are unchanged.
Ordinary shell/Python command output retains its existing caps.

## Confirmed cause

SmolVM 1.31.1 limits cumulative streaming-exec output to **11 MiB**. BackIntel permits
artifact payloads up to **128 MiB**, so valid report bundles could be truncated before
Python finished reading their tar archive. Extending a timeout cannot fix that cap.

A minimal real-VM reproduction wrote a 25 MiB artifact. The original exporter failed
with `ReadError: unexpected end of data` in 0.233 seconds and removed partial output.
Capturing the underlying command separately returned exit code 1, 11,536,384 bytes
(the cap plus one frame), and this stderr:

```text
streaming output exceeded 11534336 byte cap; exec terminated (output truncated)
```

The same native pipe path transferred a 26,224,640-byte tar containing a 25 MiB binary
payload intact in 0.470 seconds. This discriminates the transport cap from timeout,
tar parsing and artifact quota failures.

Pinned upstream source inspected at `e6ec9b5338145c92efb8073c207f8f3c43812573`
(tag `v1.31.1`):

- [Streaming-exec cap and collection](https://github.com/smol-machines/smolvm/blob/e6ec9b5338145c92efb8073c207f8f3c43812573/src/agent/client.rs#L3840).
- [Native pipe versus streaming CLI dispatch](https://github.com/smol-machines/smolvm/blob/e6ec9b5338145c92efb8073c207f8f3c43812573/src/cli/machine.rs#L4070).

The existing pipe mode keeps tar execution inside the constrained guest wrapper.
It requires no guest archive staging, host mount, network, extra dependency or
privileged direct-file copy. Both `read_bytes` and `export_artifacts` use it.

## Direct verification

| Check | Observed result |
| --- | --- |
| Simulated capped CLI, public read/export methods | Both failed before the fix; both pass after it, including binary bytes and EOF on stdin |
| Real SmolVM 25 MiB binary | Read and exported bytes match SHA-256 |
| Real SmolVM three 8 MiB files | Combined 24 MiB export preserves every byte |
| Normal PNG/SVG/offline HTML/XLSX output | Existing real-VM acceptance passes |
| Source/root writes, symlink export and bounded single-file read | Existing denial checks pass; rejected export is removed |
| Sparse 65 MiB artifact under a 64 MiB test profile | Explicit quota rejection; partial host directory removed |
| Retained normal service report | 10 files / 4,947,856 bytes; all source manifest hashes match |
| Retained three-report combined payload | 32 files / 19,769,798 bytes; all source manifest hashes match |

The retained reports are the original INT-498 design-review artifacts, copied into a
read-only mounted source and exported without rerendering or changing their contents.
Local reproduction receipts and exported bundles are in the canonical checkout at
`data/output/int498-export-fix-20261114/`. No model calls were made.

Run the portable regression and opt-in real-VM checks:

```sh
uv run pytest tests/test_analysis_sandbox.py -k binary_transfer_outgrows -q
BACKINTEL_SMOLVM_TESTS=1 uv run pytest tests/test_analysis_sandbox.py \
  -k 'real_large_binary_read_and_aggregate_export or real_persistent_workspace_boundary_and_export' -q
```

This fixes transport. It does not relabel the earlier taxi attempt as successful or
recover its deleted HTML/workbook output; those historical records remain unchanged.
