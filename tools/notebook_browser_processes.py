"""Reap a private notebook server and its descendants before deleting its logs."""
from __future__ import annotations

import os
import subprocess
from typing import Callable

import psutil


def is_live(process: psutil.Process) -> bool:
    """Exited POSIX grandchildren may await reaping by their new parent."""
    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def stop_process_tree(server: subprocess.Popen, request_shutdown: Callable[[], None],
                      *, graceful_timeout: float = 30, terminate_timeout: float = 5) -> dict:
    """Stop only the server started by this process and its observed children.

    Keep Process objects before requesting shutdown: descendants can outlive
    their parent and retain its redirected log handle on Windows. psutil checks
    process identity when signalling, including protection against PID reuse.
    """
    if server.poll() is not None:
        return dict(stopped=True, returncode=server.returncode, descendants=[], terminated=[], killed=[], remaining=[])
    parent = psutil.Process(server.pid)
    if parent.ppid() != os.getpid():
        raise RuntimeError("Refusing to stop a server not launched by this checker")
    children: dict[tuple[int, float], psutil.Process] = {}

    def remember(process: psutil.Process) -> None:
        try:
            for child in process.children(recursive=True):
                children[(child.pid, child.create_time())] = child
        except psutil.NoSuchProcess:
            pass

    remember(parent)
    terminated, killed = [], []
    try:
        try:
            request_shutdown()
            server.wait(timeout=graceful_timeout)
        except (OSError, TimeoutError, subprocess.TimeoutExpired):
            # The normal Jupyter shutdown can stall in a kernel or extension.
            # The finally block still owns and reaps those processes.
            pass
    finally:
        remember(parent)
        if server.poll() is None:
            try:
                parent.terminate()
                terminated.append(parent.pid)
            except psutil.NoSuchProcess:
                pass
            try:
                server.wait(timeout=terminate_timeout)
            except subprocess.TimeoutExpired:
                try:
                    parent.kill()
                    killed.append(parent.pid)
                except psutil.NoSuchProcess:
                    pass
                server.wait(timeout=terminate_timeout)
        # A surviving descendant may have started another child during the
        # shutdown request. Capture it before terminating the recorded tree.
        for child in list(children.values()):
            remember(child)
        _, alive = psutil.wait_procs(list(children.values()), timeout=terminate_timeout)
        for child in reversed(alive):
            if not is_live(child):
                continue
            try:
                child.terminate()
                terminated.append(child.pid)
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(alive, timeout=terminate_timeout)
        for child in alive:
            if not is_live(child):
                continue
            try:
                child.kill()
                killed.append(child.pid)
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(alive, timeout=terminate_timeout)
        alive = [child for child in alive if is_live(child)]
        if alive:
            raise RuntimeError(f"Private notebook descendants remain alive: {[child.pid for child in alive]}")
    return dict(stopped=server.poll() is not None, returncode=server.returncode,
                descendants=sorted(child.pid for child in children.values()),
                terminated=sorted(terminated), killed=sorted(killed), remaining=[])
