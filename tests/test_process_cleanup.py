"""Regression checks for subprocess isolation and slow streaming consumers."""
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

import web_execution as execution

ROOT = Path(__file__).resolve().parents[1]


class ProcessCleanupTests(unittest.TestCase):
    def test_immediately_successful_processes_can_start_and_finish(self):
        for _ in range(3):
            result = execution.run_capture(
                [sys.executable, "-u", "-c", "print('FAST', flush=True)"], cwd=ROOT, timeout=3)
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.stdout.strip(), "FAST")
            self.assertFalse(result.timed_out)

    def test_completed_process_is_not_timed_out_while_the_client_is_paused(self):
        processes = []
        watchdog_finished = threading.Event()
        real_popen = subprocess.Popen
        real_thread = threading.Thread

        def popen(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        def thread(*args, **kwargs):
            target = kwargs.get("target")
            if target and target.__name__ == "watchdog":
                def observed_watchdog():
                    try:
                        target()
                    finally:
                        watchdog_finished.set()
                kwargs["target"] = observed_watchdog
            return real_thread(*args, **kwargs)

        command = [sys.executable, "-u", "-c", "print('DONE', flush=True)"]
        with patch.object(execution.subprocess, "Popen", side_effect=popen), \
                patch.object(execution.threading, "Thread", side_effect=thread):
            iterator = execution.iter_process(command, cwd=ROOT, timeout=1)
            try:
                self.assertIn("DONE", next(iterator)["text"])
                self.assertEqual(processes[0].wait(timeout=2), 0)
                # Leave the generator paused at yield until its watchdog really
                # fires, exactly as a slow client can do after the child exits.
                self.assertTrue(watchdog_finished.wait(3))
                while True:
                    try:
                        next(iterator)
                    except StopIteration as done:
                        result = done.value
                        break
                self.assertEqual(result.exit_code, 0)
                self.assertFalse(result.timed_out)
            finally:
                iterator.close()

    @unittest.skipUnless(os.name == "nt", "Windows Job Object failure path")
    def test_missing_windows_job_rejects_and_terminates_the_run(self):
        self.check_missing_job()

    @unittest.skipUnless(os.name == "nt", "Windows Job Object failure path")
    def test_missing_windows_job_still_kills_the_parent_if_taskkill_fails(self):
        self.check_missing_job(taskkill_fails=True)

    @unittest.skipUnless(os.name == "nt", "Windows descendant Job Object cleanup")
    def test_exiting_parent_does_not_leave_a_descendant_holding_the_output_pipe(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        code = ("import subprocess,sys; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdout=sys.stdout); "
                "print(child.pid,flush=True)")
        iterator = execution.iter_process([sys.executable, "-u", "-c", code], cwd=ROOT, timeout=3)
        handle = None
        try:
            first = next(iterator)
            child_pid = int(first["text"].strip())
            handle = kernel.OpenProcess(0x100000 | 0x1, False, child_pid)  # SYNCHRONIZE | PROCESS_TERMINATE
            while True:
                try:
                    next(iterator)
                except StopIteration as done:
                    result = done.value
                    break
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(result.timed_out)
            if handle:
                self.assertEqual(kernel.WaitForSingleObject(handle, 2000), 0,
                                 "A descendant survived the parent and response cleanup")
        finally:
            iterator.close()
            if handle:
                if kernel.WaitForSingleObject(handle, 0) != 0:
                    kernel.TerminateProcess(handle, 1)
                kernel.CloseHandle(handle)

    @unittest.skipUnless(os.name == "nt", "Windows suspended process cleanup")
    def test_failed_resume_also_terminates_the_suspended_process(self):
        processes = []
        real_popen = subprocess.Popen

        def popen(*args, **kwargs):
            if args[0][0] == "taskkill":
                return real_popen(*args, **kwargs)
            self.assertTrue(kwargs["creationflags"] & 0x4)
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        with patch.object(execution.subprocess, "Popen", side_effect=popen), \
                patch.object(execution, "_resume_windows_process", side_effect=OSError("resume failed")):
            iterator = execution.iter_process(
                [sys.executable, "-c", "import time; time.sleep(60)"], cwd=ROOT, timeout=30)
            try:
                with self.assertRaisesRegex(RuntimeError, "isolamento"):
                    next(iterator)
            finally:
                iterator.close()
            self.assertIsNotNone(processes[0].poll())

    def check_missing_job(self, taskkill_fails=False):
        processes = []
        real_popen = subprocess.Popen

        def popen(*args, **kwargs):
            if args[0][0] == "taskkill":
                return real_popen(*args, **kwargs)
            self.assertTrue(kwargs["creationflags"] & 0x4)
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        with ExitStack() as patches:
            patches.enter_context(patch.object(execution, "_windows_job", return_value=None))
            patches.enter_context(patch.object(execution.subprocess, "Popen", side_effect=popen))
            if taskkill_fails:
                patches.enter_context(patch.object(execution.subprocess, "run", side_effect=OSError("taskkill unavailable")))
            iterator = execution.iter_process(
                [sys.executable, "-u", "-c", "import time; time.sleep(60)"], cwd=ROOT, timeout=30)
            try:
                with self.assertRaisesRegex(RuntimeError, "isolamento"):
                    next(iterator)
            finally:
                iterator.close()
            self.assertTrue(processes)
            self.assertIsNotNone(processes[0].poll())
            for pipe in (processes[0].stdin, processes[0].stdout, processes[0].stderr):
                self.assertTrue(pipe.closed)


if __name__ == "__main__":
    unittest.main()
