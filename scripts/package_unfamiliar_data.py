"""Copy one explicitly selected domain into a new, read-only analyst package.

No model, network, source transformation or evaluator-file traversal occurs. The
energy ZIP's already-qualified member is used directly; its source hash is pinned.
"""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import tempfile
from pathlib import Path

from qualify_unfamiliar_data import MANIFEST, ROOT

from backintel.stores.package import PackageStore, digest, safe_name

SOURCE_DOCS = ROOT / "benchmarks/unfamiliar/unfamiliar-v1/source-docs"


def package_domain(
    data_dir: Path,
    output: Path,
    domain_id: str,
    *,
    manifest: Path = MANIFEST,
    source_docs: Path = SOURCE_DOCS,
) -> dict:
    document = json.loads(manifest.read_text())
    domains = [domain for domain in document["domains"] if domain["id"] == domain_id]
    if len(domains) != 1:
        raise ValueError("Choose one manifest-listed domain")
    domain = domains[0]
    assets = {asset["file"]: asset for asset in document["assets"]}
    raw = (data_dir / "raw").resolve(strict=True)
    selected = []
    for name in domain["assets"]:
        safe_name(name)
        if name not in assets:
            raise ValueError("Domain references an unqualified asset")
        item = assets[name]
        if name == "household_power.zip":
            item = document["extracted_energy"]
            name = safe_name(item["file"])
        path = raw / name
        if (
            not stat.S_ISREG(path.lstat().st_mode)
            or path.stat().st_size != item["bytes"]
            or digest(path) != item["sha256"]
        ):
            raise ValueError(f"Selected asset is linked or changed: {name}")
        kind = (
            "parquet"
            if name.endswith(".parquet")
            else "documentation"
            if item.get("role") == "source_documentation"
            else "csv"
        )
        selected.append(
            (
                path,
                {
                    "file": name,
                    "format": kind,
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                    **({"separator": ";"} if name == "household_power_consumption.txt" else {}),
                },
            )
        )
    doc = source_docs / f"{safe_name(domain_id)}.md"
    if doc.is_symlink() or not doc.is_file():
        raise ValueError("Qualified ordinary source documentation is missing")
    selected.append(
        (
            doc,
            {
                "file": "source-notes.md",
                "format": "documentation",
                "bytes": doc.stat().st_size,
                "sha256": digest(doc),
            },
        )
    )
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Use a new package path; frozen inputs are not overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".package-", dir=output.parent))
    try:
        for source, item in selected:
            target = temporary / item["file"]
            shutil.copyfile(source, target)
            if digest(target) != item["sha256"]:
                raise ValueError("Source changed during package copy")
            target.chmod(0o444)
        packaged = {
            "schema_version": 1,
            "domain": domain_id,
            "split": domain["split"],
            "source_manifest_sha256": digest(manifest),
            "source": domain["source"],
            "publisher": domain["publisher"],
            "rights": domain["rights"],
            "source_url": domain["source_url"],
            "files": [item for _, item in selected],
        }
        (temporary / "package.json").write_text(json.dumps(packaged, indent=2, sort_keys=True) + "\n")
        (temporary / "package.json").chmod(0o444)
        PackageStore(temporary, dataset=output.name)
        temporary.rename(output)
        output.chmod(0o555)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {
        "domain": domain_id,
        "package": str(output),
        "manifest_sha256": digest(output / "package.json"),
        "files": len(selected),
        "bytes": sum(item["bytes"] for _, item in selected),
        "model_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/unfamiliar-v1")
    parser.add_argument("--domain", required=True, choices=["transport", "building-energy", "weather"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(package_domain(args.data_dir, args.output, args.domain), indent=2))


if __name__ == "__main__":
    main()
