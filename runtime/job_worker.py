"""Private job process entrypoint; payloads are created locally by runtime.jobs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time


def main():
    payload = Path(sys.argv[1])
    if sys.argv[-1] == '--run':
        import cloudpickle
        from runtime.jobs import _execute_claimed
        result = _execute_claimed(*cloudpickle.loads(payload.read_bytes()))
        (payload.parent / 'result.json').write_text(json.dumps(result))
        return 0

    if os.getpgrp() != os.getpid():
        raise RuntimeError('Job supervisor requires its own process group')
    deadline = float(sys.argv[2])
    with subprocess.Popen([sys.executable, '-m', 'runtime.job_worker', str(payload), '--run'],
                          stdin=subprocess.DEVNULL) as child:
        while child.poll() is None:
            remaining = deadline-time.perf_counter()
            if remaining <= 0:
                os.killpg(os.getpgrp(), signal.SIGKILL)
            readable, _, _ = select.select([sys.stdin], [], [], min(remaining, 0.1))
            if readable and not os.read(sys.stdin.fileno(), 1):
                # Losing the dispatcher must not leave native work or its
                # descendants holding a task transaction indefinitely.
                os.killpg(os.getpgrp(), signal.SIGKILL)
        return child.returncode


if __name__ == '__main__':
    raise SystemExit(main())
