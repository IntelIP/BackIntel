"""Trusted per-run setup, before any analyst command is admitted."""

import json
import os
import selectors
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


def relay(client, destination):
    with client, socket.socket(socket.AF_UNIX) as upstream:
        upstream.connect(destination)
        with selectors.DefaultSelector() as selector:
            selector.register(client, selectors.EVENT_READ, upstream)
            selector.register(upstream, selectors.EVENT_READ, client)
            while selector.get_map():
                for key, _ in selector.select(timeout=1):
                    data = key.fileobj.recv(65536)
                    if not data:
                        return
                    key.data.sendall(data)


def serve(listener, destination):
    while True:
        client, _ = listener.accept()
        threading.Thread(target=relay, args=(client, destination), daemon=True).start()


def main():
    profile, services = json.loads(sys.argv[1]), json.loads(sys.argv[2])
    for path, size in [
        ("/workspace", profile["workspace_mib"]),
        ("/artifacts", profile["artifacts_mib"]),
        ("/tmp", profile["temporary_mib"]),
        ("/dev/shm", profile["temporary_mib"]),
    ]:
        Path(path).mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "mount",
                "-t",
                "tmpfs",
                "-o",
                f"size={size}m,nosuid,nodev,uid=10001,gid=10001,mode=0700",
                "tmpfs",
                path,
            ],
            check=True,
        )
    for service in services:
        with open("/etc/hosts", "a") as hosts:
            hosts.write(f"\n127.0.0.1 {service['host']}\n")
        listener = socket.socket()
        listener.bind(("127.0.0.1", service["port"]))
        listener.listen(32)
        threading.Thread(target=serve, args=(listener, service["socket"]), daemon=True).start()
    # execute.py gives each analyst command its own read-only root view.
    Path("/run/backintel-ready").write_text("ready")
    time.sleep(profile["run_timeout_s"])
    # --stop-on-exit tears down the VM even if the host orchestrator disappears.
    os._exit(0)


if __name__ == "__main__":
    main()
