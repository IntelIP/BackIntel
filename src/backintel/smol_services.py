"""Explicit service sockets: offline VMs can reach only their assigned store endpoints."""

import json
import selectors
import socket
import subprocess
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit


def docker_json(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError("Cannot inspect the assigned store infrastructure.")
    return json.loads(result.stdout)


class ServiceBridges:
    def __init__(self, network, env, allowed_hosts):
        self.network = network
        self.directory = tempfile.TemporaryDirectory(prefix="bi-svc-", dir="/tmp")
        self.services = []
        self.listeners = []
        self.connections = set()
        self.closed = False
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(32)
        endpoints = set()
        for key, default_port in [
            ("BACKINTEL_POSTGRES_DSN", 5432),
            ("BACKINTEL_MONGO_URI", 27017),
            ("BACKINTEL_CH_URL", 8123),
        ]:
            if key in env:
                url = urlsplit(env[key])
                endpoints.add((url.hostname, url.port or default_port))
        if "BACKINTEL_ICEBERG_TABLES" in env:
            endpoints.add(("backintel-garage", 3900))
        if not network or not endpoints or {host for host, _ in endpoints} != allowed_hosts:
            self.close()
            raise ValueError("Networked analysis requires explicit assigned store endpoints.")
        try:
            details = docker_json("network", "inspect", network)[0]
            if not details.get("Internal"):
                raise ValueError("Assigned store infrastructure must use an internal network.")
            for index, (host, port) in enumerate(sorted(endpoints)):
                matches = []
                for identity, peer in details.get("Containers", {}).items():
                    info = docker_json("inspect", identity)[0]
                    aliases = info["NetworkSettings"]["Networks"].get(network, {}).get("Aliases") or []
                    if host in {peer.get("Name"), *aliases}:
                        matches.append((identity, info))
                if len(matches) != 1:
                    raise ValueError("An assigned hostname must identify exactly one store container.")
                identity, info = matches[0]
                bindings = info["NetworkSettings"]["Ports"].get(f"{port}/tcp") or []
                bindings = [item for item in bindings if item["HostIp"] == "127.0.0.1"]
                if len(bindings) != 1:
                    raise ValueError("Assigned stores need a single localhost-only published TCP port.")
                host_socket = str(Path(self.directory.name) / f"{index}.sock")
                service = dict(
                    host=host,
                    port=port,
                    socket=f"/backintel-sockets/{index}.sock",
                    identity=identity,
                    host_port=int(bindings[0]["HostPort"]),
                    host_socket=host_socket,
                )
                self.services.append(service)
                listener = socket.socket(socket.AF_UNIX)
                listener.bind(host_socket)
                listener.listen(32)
                listener.settimeout(0.2)
                self.listeners.append(listener)
                threading.Thread(target=self._serve, args=(listener, service), daemon=True).start()
        except BaseException:
            self.close()
            raise

    def validate(self):
        for service in self.services:
            info = docker_json("inspect", service["identity"])[0]
            bindings = info["NetworkSettings"]["Ports"].get(f"{service['port']}/tcp") or []
            if (
                not info["State"]["Running"]
                or self.network not in info["NetworkSettings"]["Networks"]
                or {"HostIp": "127.0.0.1", "HostPort": str(service["host_port"])} not in bindings
            ):
                raise ValueError("An assigned store endpoint changed; cancelling the sandbox.")

    def _serve(self, listener, service):
        while not self.closed:
            try:
                client, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            if not self._slots.acquire(blocking=False):
                client.close()
                continue
            threading.Thread(target=self._relay, args=(client, service), daemon=True).start()

    def _relay(self, client, service):
        upstream = None
        try:
            self.validate()
            upstream = socket.create_connection(("127.0.0.1", service["host_port"]), timeout=5)
            with self._lock:
                if self.closed:
                    return
                self.connections.update((client, upstream))
            with selectors.DefaultSelector() as selector:
                selector.register(client, selectors.EVENT_READ, upstream)
                selector.register(upstream, selectors.EVENT_READ, client)
                while not self.closed:
                    for key, _ in selector.select(timeout=0.2):
                        data = key.fileobj.recv(65536)
                        if not data:
                            return
                        key.data.sendall(data)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            return
        finally:
            self._slots.release()
            with self._lock:
                for connection in (client, upstream):
                    if connection:
                        self.connections.discard(connection)
                        connection.close()

    def close(self):
        self.closed = True
        for listener in self.listeners:
            listener.close()
        with self._lock:
            for connection in self.connections:
                connection.close()
            self.connections.clear()
        self.directory.cleanup()
