"""Exercise real private process trees, inherited log handles, and isolation."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notebook_browser_processes import stop_process_tree


WORKER = r'''
from pathlib import Path
import os, subprocess, sys, time
folder, role, depth = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
with (folder / 'server.log').open('a', encoding='utf-8') as stream:
    stream.write('owned process holding a log\n')
    stream.flush()
    if depth:
        subprocess.Popen([sys.executable, __file__, str(folder), 'child', str(depth - 1)],
            stdout=stream, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        deadline = time.monotonic() + 10
        while not (folder / f'ready-{depth - 1}').exists():
            assert time.monotonic() < deadline
            time.sleep(0.02)
    (folder / f'ready-{depth}').write_text(str(os.getpid()), encoding='utf-8')
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        if role == 'parent' and (folder / 'stop').exists():
            break
        time.sleep(0.02)
'''


class ProcessCleanupTests(unittest.TestCase):
    def exercise_tree(self, shutdown_kind):
        with tempfile.TemporaryDirectory(prefix='fullbleed-process-cleanup-') as private:
            root = Path(private).resolve()
            worker = root / 'worker.py'
            worker.write_text(WORKER, encoding='utf-8')
            folder, sibling_folder = root / 'owned', root / 'sibling'
            folder.mkdir(); sibling_folder.mkdir()
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            server = subprocess.Popen([sys.executable, str(worker), str(folder), 'parent', '2'],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
            sibling = subprocess.Popen([sys.executable, str(worker), str(sibling_folder), 'child', '0'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
            tracked = []
            try:
                deadline = time.monotonic() + 15
                while not (folder / 'ready-2').exists() or not (sibling_folder / 'ready-0').exists():
                    self.assertIsNone(server.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.02)
                tracked = psutil.Process(server.pid).children(recursive=True)
                # Windows virtual-environment launchers can add intermediate
                # processes. Require both worker descendants, plus stop every
                # process actually observed in the private tree.
                self.assertGreaterEqual(len(tracked), 2)
                worker_children = {int((folder / f'ready-{depth}').read_text()) for depth in (0, 1)}
                self.assertTrue(worker_children.issubset({process.pid for process in tracked}))

                def request_shutdown():
                    if shutdown_kind == 'graceful':
                        (folder / 'stop').touch()
                    elif shutdown_kind == 'error':
                        raise ValueError('simulated shutdown callback failure')
                    # 'timeout' deliberately leaves the parent running.

                if shutdown_kind == 'error':
                    with self.assertRaisesRegex(ValueError, 'callback failure'):
                        stop_process_tree(server, request_shutdown, graceful_timeout=0.3, terminate_timeout=1)
                else:
                    report = stop_process_tree(server, request_shutdown, graceful_timeout=0.3, terminate_timeout=1)
                    self.assertTrue(report['stopped'])
                    self.assertEqual(set(report['descendants']), {process.pid for process in tracked})
                    self.assertEqual(report['remaining'], [])
                self.assertIsNotNone(server.poll())
                for process in tracked:
                    try:
                        self.assertTrue(not process.is_running() or process.status() == psutil.STATUS_ZOMBIE)
                    except psutil.NoSuchProcess:
                        pass
                self.assertIsNone(sibling.poll(), 'An unrelated sibling must remain alive')
                log = (folder / 'server.log').resolve()
                self.assertEqual(log.parent, folder.resolve())
                log.unlink()  # This failed in Windows CI while an orphan retained the log.
            finally:
                for process in tracked:
                    if process.is_running():
                        process.kill()
                psutil.wait_procs(tracked, timeout=5)
                for process in (server, sibling):
                    if process.poll() is None:
                        process.terminate()
                    process.wait(timeout=5)

    def test_graceful_parent_exit_reaps_grandchildren_and_releases_log(self):
        self.exercise_tree('graceful')

    def test_stuck_parent_and_descendants_are_reaped(self):
        self.exercise_tree('timeout')

    def test_callback_error_still_reaps_owned_tree(self):
        self.exercise_tree('error')

    def test_already_finished_process_is_a_noop(self):
        process = subprocess.Popen([sys.executable, '--version'], stdout=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        process.wait(timeout=5)
        result = stop_process_tree(process, lambda: self.fail('Shutdown callback must not run'))
        self.assertTrue(result['stopped'])
        self.assertEqual(result['descendants'], [])


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
