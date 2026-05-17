"""Windows Job Object — guarantee child processes die with the parent.

A Job Object is the OS-level mechanism that ensures every process we spawn
gets killed when the parent exits — *no matter how the parent dies*: normal
close, taskbar right-click "Close window", Task Manager "End task", crash,
power loss, BSOD, kill -9 — anything.  This is critical because Python
subprocesses are otherwise orphaned (re-parented to the system) and keep
running in the background, including any input automation they were doing.

Usage::

    from anime_game_afk.core.job_object import KillOnCloseJob

    job = KillOnCloseJob()              # creates an unnamed job, sets
                                        # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    proc = subprocess.Popen([...])
    job.assign(proc.pid)                # child now bound to the job

    # ... when the parent process exits for any reason, Windows kernel
    #     terminates every process assigned to the job.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from loguru import logger

# ---------------------------------------------------------------------------
# Win32 constants and structures
# ---------------------------------------------------------------------------

# DesiredAccess flags for OpenProcess
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100

# JOBOBJECT_BASIC_LIMIT_INFORMATION.LimitFlags
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
# SILENT_BREAKAWAY_OK = grandchildren of the parent (e.g. the game launched
# by the worker) are NOT assigned to this job and survive parent exit.
# Without this, every process the worker spawns gets killed when the parent
# dies — including the game.
_JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000

# JobObjectInfoClass
_JobObjectExtendedLimitInformation = 9


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_void_p),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class KillOnCloseJob:
    """A Win32 Job Object that kills its children when the parent exits.

    Safe to instantiate on non-Windows platforms — becomes a no-op (the
    :meth:`assign` method silently returns ``False``).
    """

    def __init__(self) -> None:
        self._job_handle: int | None = None
        if sys.platform != "win32":
            return

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            create_job = kernel32.CreateJobObjectW
            create_job.restype = wintypes.HANDLE
            create_job.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]

            handle = create_job(None, None)
            if not handle:
                err = ctypes.get_last_error()
                logger.warning("CreateJobObjectW failed (err={}); subprocesses will NOT auto-die with parent", err)
                return

            # Configure: kill all processes when last handle to job closes.
            # The job handle is held by this Python process; when the
            # process dies for any reason, the kernel closes the handle
            # and runs the kill.
            info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = (
                _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                | _JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
            )

            set_info = kernel32.SetInformationJobObject
            set_info.restype = wintypes.BOOL
            set_info.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]

            ok = set_info(
                handle,
                _JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            if not ok:
                err = ctypes.get_last_error()
                logger.warning("SetInformationJobObject failed (err={}); subprocesses will NOT auto-die with parent", err)
                kernel32.CloseHandle(handle)
                return

            self._job_handle = handle
            self._kernel32 = kernel32
            logger.info("KillOnCloseJob created (handle={:#x})", handle)
        except Exception as exc:  # noqa: BLE001 — must not crash startup
            logger.warning("KillOnCloseJob init failed: {} — subprocesses will NOT auto-die", exc)

    def assign(self, pid: int) -> bool:
        """Bind a process (by PID) to the job.

        Returns True on success; False on any failure (job not available,
        process already exited, access denied).  Safe to call repeatedly
        for the same PID — Windows ignores duplicate assignments.
        """
        if self._job_handle is None:
            return False

        kernel32 = self._kernel32

        open_process = kernel32.OpenProcess
        open_process.restype = wintypes.HANDLE
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        proc_handle = open_process(
            _PROCESS_TERMINATE | _PROCESS_SET_QUOTA, False, pid,
        )
        if not proc_handle:
            err = ctypes.get_last_error()
            logger.warning("OpenProcess({}) failed (err={}) — child will NOT auto-die with parent", pid, err)
            return False

        try:
            assign = kernel32.AssignProcessToJobObject
            assign.restype = wintypes.BOOL
            assign.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

            ok = bool(assign(self._job_handle, proc_handle))
            if not ok:
                err = ctypes.get_last_error()
                logger.warning("AssignProcessToJobObject({}) failed (err={})", pid, err)
            else:
                logger.info("Worker PID={} bound to KillOnCloseJob", pid)
            return ok
        finally:
            kernel32.CloseHandle(proc_handle)

    def close(self) -> None:
        """Close the job handle (triggers immediate kill of all children).

        Normally called automatically when the Python process exits
        (Windows closes all handles).  Provided for explicit cleanup in
        tests or graceful shutdown sequences.
        """
        if self._job_handle is not None:
            try:
                self._kernel32.CloseHandle(self._job_handle)
            except Exception:  # noqa: BLE001
                pass
            self._job_handle = None

    def __del__(self) -> None:
        self.close()
