"""Trusted guest entry point: apply limits before executing analyst-controlled code."""

import ctypes
import json
import os
import resource
import subprocess
import sys


def main():
    limits = json.loads(sys.argv[1])
    libc = ctypes.CDLL(None, use_errno=True)
    # crun exec reopens the image root for each command. Give this process its
    # own read-only root view without freezing the agent's image metadata path.
    if libc.unshare(0x00020000) != 0:  # CLONE_NEWNS
        raise OSError(ctypes.get_errno(), "Cannot isolate workload mounts")
    subprocess.run(["mount", "--make-rprivate", "/"], check=True)
    subprocess.run(["mount", "--rbind", "/", "/"], check=True)
    subprocess.run(["mount", "-o", "remount,bind,ro", "/"], check=True)
    os.chroot("/")
    if not os.statvfs("/").f_flag & os.ST_RDONLY:
        raise RuntimeError("Workload root is not read-only")
    # Drop the bounding set while still privileged, then permanently become the analyst.
    for capability in range(41):
        if libc.prctl(24, capability, 0, 0, 0) != 0:  # PR_CAPBSET_DROP
            raise OSError(ctypes.get_errno(), "Cannot drop guest capabilities")
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), "Cannot disable privilege escalation")
    resource.setrlimit(resource.RLIMIT_NPROC, (limits["pids"], limits["pids"]))
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    os.chdir("/workspace")
    os.execvp(sys.argv[2], sys.argv[2:])


if __name__ == "__main__":
    main()
