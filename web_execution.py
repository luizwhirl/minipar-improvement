"""Private build artifacts and bounded, cancellable subprocess output for the Web."""
from __future__ import annotations

import codecs
from dataclasses import dataclass
import ntpath
import os
from pathlib import Path
import queue
import re
import secrets
import signal
import subprocess
import threading
import time

from run_artifacts import create_run_dir, executable_path


@dataclass
class BuildRun:
    directory: Path
    source: Path
    stem: str
    filename: str

    @property
    def executable(self):
        return Path(executable_path(str(self.directory), self.stem))


@dataclass
class ProcessResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    output_limited: bool = False


def validate_source(data, with_inputs=False):
    if not isinstance(data, dict):
        raise ValueError("Envie um objeto JSON com o código MiniPar.")
    code = data.get("code")
    filename = data.get("filename", "ide_temp.minipar")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Informe o código MiniPar.")
    if (not isinstance(filename, str) or len(filename) > 120
            or filename != ntpath.basename(filename) or filename != os.path.basename(filename)
            or not filename.lower().endswith(".minipar") or not filename[:-8].strip(" .")
            or filename.endswith((" ", "."))
            or any(ord(char) < 32 or char in '<>:"/\\|?*' for char in filename)
            or filename.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL",
                *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
        raise ValueError("Use um nome de arquivo .minipar sem diretórios ou caracteres especiais.")
    inputs = data.get("inputs", []) if with_inputs else []
    if not isinstance(inputs, list) or not all(isinstance(value, str) for value in inputs):
        raise ValueError("As entradas devem ser uma lista de textos, um por valor.")
    if inputs:
        # Use the language's lexer: text and comments mentioning input() are
        # not reads. Keep invalid source on the normal compiler error path.
        from src.lexer import Lexer, TokenType
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        if not lexer.has_errors and not any(token.type == TokenType.INPUT for token in tokens):
            raise ValueError("O código atual não usa input(). Os valores digitados não seriam utilizados.")
    return code, filename, inputs


def prepare_run(code, filename, output_root):
    directory = Path(create_run_dir(output_root)).resolve()
    source_dir = directory / "source"
    source_dir.mkdir()
    source = source_dir / filename
    source.write_text(code, encoding="utf-8")
    return BuildRun(directory, source, Path(filename).stem, filename)


def read_artifacts(run):
    def read(extension):
        path = run.directory / (run.stem + extension)
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    return {"cpp": read(".cpp"), "tac": read(".tac")}


class DownloadRegistry:
    """Only successfully built binaries receive an unguessable download handle."""
    def __init__(self):
        self._records = {}
        self._lock = threading.Lock()

    def register(self, run):
        token = secrets.token_urlsafe(32)
        with self._lock:
            if len(self._records) >= 1000:
                self._records.pop(next(iter(self._records)))
            self._records[token] = (run.directory, run.executable.name)
        return token, run.executable.name

    def lookup(self, token, filename, output_root):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return None
        with self._lock:
            record = self._records.get(token)
        if record is None or record[1] != filename:
            return None
        directory, expected_name = record
        root = Path(output_root).resolve() / "runs"
        path = directory / expected_name
        if (directory.resolve().parent != root or not directory.name.startswith("run-")
                or path.is_symlink() or path.resolve().parent != directory.resolve()
                or not path.is_file()):
            return None
        return path


def _windows_job(process):
    """Kill all assigned descendants when the job handle closes (Windows)."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
            ("flags", wintypes.DWORD), ("min_working_set", ctypes.c_size_t),
            ("max_working_set", ctypes.c_size_t), ("active_processes", wintypes.DWORD),
            ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]

    class IOCounts(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in
                    ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("basic", BasicLimits), ("io", IOCounts),
            ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
            ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        return None
    limits = ExtendedLimits()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if (not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits))
            or not kernel.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle)))):
        kernel.CloseHandle(handle)
        return None
    return lambda: kernel.CloseHandle(handle)


def _resume_windows_process(process):
    """Resume the primary thread only after its suspended process joins a job."""
    import ctypes
    from ctypes import wintypes

    class ThreadEntry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
            ("thread_id", wintypes.DWORD), ("process_id", wintypes.DWORD),
            ("priority", wintypes.LONG), ("delta", wintypes.LONG), ("flags", wintypes.DWORD)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Thread32First.argtypes = kernel.Thread32Next.argtypes = (wintypes.HANDLE, ctypes.POINTER(ThreadEntry))
    kernel.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.ResumeThread.argtypes = (wintypes.HANDLE,)
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    snapshot = kernel.CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        found = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.process_id == process.pid:
                thread = kernel.OpenThread(0x2, False, entry.thread_id)  # THREAD_SUSPEND_RESUME
                if not thread:
                    raise ctypes.WinError(ctypes.get_last_error())
                try:
                    previous_count = kernel.ResumeThread(thread)
                    if previous_count == 0xFFFFFFFF:
                        raise ctypes.WinError(ctypes.get_last_error())
                    if previous_count != 1:
                        raise OSError("Não foi possível retomar a thread inicial do processo.")
                    return
                finally:
                    kernel.CloseHandle(thread)
            found = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        raise OSError("A thread inicial do processo não foi encontrada.")
    finally:
        kernel.CloseHandle(snapshot)


def iter_process(command, *, cwd, timeout, stdin_data=None, output_limit=2 * 1024 * 1024):
    """Yield decoded pipe chunks immediately; return ProcessResult at EOF."""
    options = {"cwd": str(cwd), "stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
               "stderr": subprocess.PIPE, "bufsize": 0}
    if os.name == "nt":
        options["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                                    | 0x4)  # CREATE_SUSPENDED: assign the job before any child code runs.
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(command, **options)
    try:
        close_job = _windows_job(process)
    except Exception:
        close_job = None
    if os.name == "nt" and close_job is not None:
        try:
            _resume_windows_process(process)
        except Exception:
            close_job()
            close_job = None
    if os.name == "nt" and close_job is None:
        # Without a job, a parent that exits first can leave unkillable pipe
        # owners behind. Reject this run immediately instead of streaming it.
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            pass
        finally:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=2)
            finally:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    pipe.close()
        raise RuntimeError("Não foi possível preparar o isolamento dos processos no Windows.")
    stopping = threading.Event()
    timed_out = threading.Event()
    terminated = threading.Event()
    kill_lock = threading.Lock()
    messages = queue.Queue(maxsize=128)
    readers = []
    chunks = {"stdout": [], "stderr": []}

    def terminate():
        with kill_lock:
            if terminated.is_set():
                return
            terminated.set()
            if close_job:
                close_job()
            elif os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass

    def put(message):
        while not stopping.is_set():
            try:
                messages.put(message, timeout=0.1)
                return
            except queue.Full:
                pass

    def read_pipe(name, pipe):
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while not stopping.is_set():
                data = os.read(pipe.fileno(), 4096)
                if not data:
                    break
                text = decoder.decode(data)
                if text:
                    put((name, text))
            tail = decoder.decode(b"", final=True)
            if tail:
                put((name, tail))
        except (OSError, ValueError):
            pass
        finally:
            put((name, None))

    def write_input():
        try:
            if stdin_data:
                data = stdin_data.encode("utf-8")
                while data and not stopping.is_set():
                    count = process.stdin.write(data)
                    if not count:
                        break
                    data = data[count:]
        except (BrokenPipeError, OSError, ValueError):
            pass
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    def watchdog():
        if not stopping.wait(timeout):
            if process.poll() is None:
                timed_out.set()
            terminate()

    output_limited = False
    total = 0
    writer = None
    try:
        for name in ("stdout", "stderr"):
            thread = threading.Thread(target=read_pipe, args=(name, getattr(process, name)), daemon=True)
            thread.start()
            readers.append(thread)
        writer = threading.Thread(target=write_input, daemon=True)
        writer.start()
        timer = threading.Thread(target=watchdog, daemon=True)
        timer.start()
        remaining = 2
        while remaining:
            if process.poll() is not None:
                terminate()  # Also close pipe handles held by surviving descendants.
            try:
                name, text = messages.get(timeout=0.1)
            except queue.Empty:
                continue
            if text is None:
                remaining -= 1
                continue
            encoded = text.encode("utf-8")
            available = max(0, output_limit - total)
            if len(encoded) > available:
                text = encoded[:available].decode("utf-8", errors="ignore")
                output_limited = True
                terminate()
            total += len(text.encode("utf-8"))
            if text:
                chunks[name].append(text)
                yield {"type": "output", "stream": name, "text": text}
        while process.poll() is None:
            time.sleep(0.05)  # The independent watchdog still enforces the configured limit.
        return ProcessResult(process.returncode, "".join(chunks["stdout"]), "".join(chunks["stderr"]),
                             timed_out.is_set(), output_limited)
    finally:
        stopping.set()
        try:
            terminate()
        finally:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
            for pipe in (process.stdin, process.stdout, process.stderr):
                try:
                    pipe.close()
                except (OSError, ValueError):
                    pass
            for thread in readers + ([writer] if writer else []):
                thread.join(timeout=0.5)


def run_capture(command, **options):
    iterator = iter_process(command, **options)
    while True:
        try:
            next(iterator)
        except StopIteration as done:
            return done.value
