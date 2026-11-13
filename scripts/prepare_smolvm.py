"""Prepare the pinned local SmolVM runtime and export an already-built analysis image.

Docker is needed only for image preparation and optional database services, never for
file-based sandbox execution. No model calls or cloud resources are created.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import tarfile
import tempfile
from pathlib import Path

import httpx

from backintel.smol_runtime import ARCHIVE_SHA256, RELEASE_URL, RUNTIME_HOME, VERSION, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--image", default="backintel-sandbox:py312")
    parser.add_argument("--output", type=Path, default=RUNTIME_HOME / "images/analysis-py312.tar")
    args = parser.parse_args()
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        parser.error("This qualified runtime distribution requires macOS ARM64.")
    with tempfile.TemporaryDirectory(prefix="backintel-prepare-") as temp:
        archive = args.runtime_archive or Path(temp) / "smolvm.tar.gz"
        if args.runtime_archive is None:
            with httpx.stream("GET", RELEASE_URL, follow_redirects=True, timeout=120) as response:
                response.raise_for_status()
                with archive.open("wb") as output:
                    for chunk in response.iter_bytes():
                        output.write(chunk)
        if digest(archive) != ARCHIVE_SHA256:
            raise ValueError("SmolVM release archive checksum mismatch.")
        root = RUNTIME_HOME / "runtimes"
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as source:
            for member in source:
                destination = root / member.name
                if (
                    Path(member.name).is_absolute()
                    or ".." in Path(member.name).parts
                    or not destination.parent.resolve().is_relative_to(root.resolve())
                ):
                    raise ValueError("Unsafe runtime archive path.")
                # Verified official guest rootfs includes absolute guest symlinks (/run).
                # Parent confinement above prevents following those links on the host.
                source.extract(member, root, filter="fully_trusted")
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".partial")
        try:
            with temporary.open("wb") as target:
                subprocess.run(
                    ["docker", "image", "save", args.image], stdout=target, check=True, timeout=300
                )
            with tarfile.open(temporary) as tar:
                manifest = json.load(tar.extractfile("manifest.json"))
                if len(manifest) != 1:
                    raise ValueError("Expected one prepared sandbox image.")
                config = tar.extractfile(manifest[0]["Config"]).read()
                image_id = "sha256:" + hashlib.sha256(config).hexdigest()
                if json.loads(config)["architecture"] != "arm64":
                    raise ValueError("The prepared image must be ARM64.")
            temporary.replace(output)
            receipt = {
                "image_id": image_id,
                "archive_sha256": digest(output),
                "runtime_version": VERSION,
                "runtime_archive_sha256": ARCHIVE_SHA256,
                "source_image": args.image,
            }
            output.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps({"archive": str(output), **receipt}, indent=2))
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
