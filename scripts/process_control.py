"""Portable process ownership and state locations for desktop update launchers."""
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import subprocess
import sys


def state_home():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Gravewright/updates'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/Gravewright/updates'
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'gravewright/updates'


def environment_python(project):
    return Path(project) / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


@contextmanager
def instance_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.seek(0, 2) == 0:
            handle.write(b'\0'); handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


class WindowsJob:
    """Closing the parent-owned handle also terminates orphaned child processes."""
    def __init__(self, process):
        import ctypes as c
        from ctypes import wintypes as w
        class Basic(c.Structure):
            _fields_ = [('process_time',c.c_int64),('job_time',c.c_int64),('flags',w.DWORD),
                        ('min_working',c.c_size_t),('max_working',c.c_size_t),('active',w.DWORD),
                        ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class Counters(c.Structure):
            _fields_ = [(name,c.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(c.Structure):
            _fields_ = [('basic',Basic),('io',Counters),('process_memory',c.c_size_t),
                        ('job_memory',c.c_size_t),('peak_process',c.c_size_t),('peak_job',c.c_size_t)]
        self.api = c.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [c.c_void_p,w.LPCWSTR]; self.api.CreateJobObjectW.restype=w.HANDLE
        self.api.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]; self.api.SetInformationJobObject.restype=w.BOOL
        self.api.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]; self.api.AssignProcessToJobObject.restype=w.BOOL
        self.api.CloseHandle.argtypes=[w.HANDLE]; self.api.CloseHandle.restype=w.BOOL
        self.handle=self.api.CreateJobObjectW(None,None)
        if not self.handle:raise c.WinError(c.get_last_error())
        limits=Extended();limits.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle,9,c.byref(limits),c.sizeof(limits)) or not self.api.AssignProcessToJobObject(self.handle,int(process._handle)):
            error=c.WinError(c.get_last_error());self.close();raise error

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle);self.handle=None


def spawn(args, **kwargs):
    options = {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
    process=subprocess.Popen(args,**kwargs,**options)
    try:
        process.gravewright_job=WindowsJob(process) if os.name=='nt' else None
    except BaseException:
        process.kill();process.wait();raise
    return process


def stop(process, timeout=20):
    if process is None:return
    try:
        if process.poll() is None:
            try:
                if os.name=='nt':process.send_signal(signal.CTRL_BREAK_EVENT)
                else:os.killpg(process.pid,signal.SIGTERM)
                process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired,OSError):
                if os.name=='nt':
                    process.gravewright_job.close()
                else:os.killpg(process.pid,signal.SIGKILL)
                process.wait(timeout=10)
    finally:
        if getattr(process,'gravewright_job',None):process.gravewright_job.close()
