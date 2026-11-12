"""Raw files store: CSV files and nothing else. No query engine; the analyst must use Python.

This is what a shared folder export looks like: files with headers, no types, no catalog.
Online Retail II is provided as two CSVs, one per yearly sheet, overlapping for 1-9 Dec 2010
exactly as the source workbook does.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from backintel.stores.base import MAX_ROWS, ColumnInfo, QueryRefused, QueryResult, TableInfo, clip_cell


class FilesStore:
    kind = "files"
    query_language = "none: CSV and/or newline-delimited JSON files; use run_python"

    def __init__(self, directory: Path, *, dataset: str):
        self.dir = Path(directory)
        if not self.dir.exists():
            raise FileNotFoundError(f"Files directory not found: {self.dir}")
        self.dataset = dataset
        self.id = f"files:{dataset}"
        self.files = {p.name: p for p in sorted(self.dir.iterdir()) if p.suffix in (".csv", ".jsonl")}

    def close(self) -> None:
        return None

    def _frame(self, name: str) -> pl.LazyFrame:
        if name.endswith(".jsonl"):
            return pl.scan_ndjson(self.files[name], infer_schema_length=10_000)
        return pl.scan_csv(self.files[name], infer_schema_length=10_000, try_parse_dates=False)

    def list_tables(self) -> list[TableInfo]:
        out = []
        for name in self.files:
            frame = self._frame(name)
            count = frame.select(pl.len()).collect().item()
            cols = [ColumnInfo(name=c, type=str(t)) for c, t in frame.collect_schema().items()]
            out.append(TableInfo(name=name, row_count=count, columns=cols))
        return out

    def describe_table(self, name: str) -> TableInfo:
        if name not in self.files:
            raise QueryRefused(f"No file named {name!r}. Files: {', '.join(self.files)}")
        frame = self._frame(name)
        count = frame.select(pl.len()).collect().item()
        nulls = frame.null_count().collect().row(0)
        schema = frame.collect_schema()
        columns = [
            ColumnInfo(name=c, type=str(t), nulls=int(n))
            for (c, t), n in zip(schema.items(), nulls, strict=True)
        ]
        sample = [{k: clip_cell(v) for k, v in row.items()} for row in frame.head(3).collect().to_dicts()]
        return TableInfo(name=name, row_count=count, columns=columns, sample=sample)

    def query(self, text: str, *, max_rows: int = MAX_ROWS) -> QueryResult:
        raise NotImplementedError(
            "This store is a folder of files with no query engine. Use run_python (polars or pandas) "
            "to read the files named by list_tables."
        )

    def python_mounts(self) -> dict[str, str]:
        return {str(self.dir): str(self.dir)}

    def sandbox_network(self) -> str | None:
        return None

    def python_environment(self) -> dict[str, str]:
        return {
            "BACKINTEL_FILES_DIR": str(self.dir),
            "BACKINTEL_STORE_NOTE": (
                f"Raw files are in the directory BACKINTEL_FILES_DIR: {', '.join(self.files)}. "
                "Read them with polars.read_csv(path) or pandas.read_csv(path); dates are text and "
                "need parsing. For .jsonl files use polars.read_ndjson(path)."
            ),
        }


def export_csv_files(
    dataset: str, canonical_dir: Path, out_dir: Path, *, force: bool = False, mixed: bool = False
) -> Path:
    """Write the raw-files view of a dataset: one CSV per source table (or per source sheet)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.glob("*.csv")) and not force:
        return out_dir
    for index, path in enumerate(sorted(canonical_dir.glob("*.parquet"))):
        frame = pl.read_parquet(path)
        if path.stem == "geolocation":
            continue
        if "source_sheet" in frame.columns:
            for sheet, part in frame.partition_by("source_sheet", as_dict=True).items():
                label = str(sheet[0]).replace(" ", "_").lower()
                part.drop("source_sheet").write_csv(
                    out_dir / f"online_retail_II_{label}.csv", datetime_format="%Y-%m-%d %H:%M:%S"
                )
        else:
            if mixed and index % 2 == 0:
                for name, dtype in frame.schema.items():
                    if dtype.is_temporal():
                        frame = frame.with_columns(pl.col(name).dt.strftime("%Y-%m-%d %H:%M:%S"))
                frame.write_ndjson(out_dir / f"{path.stem}.jsonl")
            else:
                frame.write_csv(out_dir / f"{path.stem}.csv", datetime_format="%Y-%m-%d %H:%M:%S")
    return out_dir
