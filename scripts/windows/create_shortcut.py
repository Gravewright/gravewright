"""Create the optional Gravewright Runner icon shortcut using Windows COM.

Only Python's standard library and the Windows Shell are used. The batch file
remains the launch target; a shortcut supplies the icon that a .bat cannot have.
COM interface layouts follow IShellLinkW and IPersistFile in the Windows SDK:
https://learn.microsoft.com/windows/win32/shell/links
"""

import argparse
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import sys
import tempfile
import uuid


class GUID(ctypes.Structure):
    _fields_ = [('data1', ctypes.c_uint32), ('data2', ctypes.c_uint16),
                ('data3', ctypes.c_uint16), ('data4', ctypes.c_ubyte * 8)]

    @classmethod
    def from_string(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


CLSID_SHELL_LINK = GUID.from_string('00021401-0000-0000-c000-000000000046')
IID_SHELL_LINK = GUID.from_string('000214f9-0000-0000-c000-000000000046')
IID_PERSIST_FILE = GUID.from_string('0000010b-0000-0000-c000-000000000046')


def checked(result, action):
    if result < 0:
        raise OSError(f'{action} failed with Windows HRESULT 0x{result & 0xffffffff:08x}.')


def method(pointer, index, *argument_types):
    """Bind one documented COM vtable slot; the first argument is always this."""
    vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    prototype = ctypes.WINFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, *argument_types)
    return prototype(vtable[index])


def release(pointer):
    if pointer:
        # IUnknown::Release returns a reference count, not an HRESULT.
        method(pointer, 2)(pointer)


@contextmanager
def interface(pointer, identifier):
    result = ctypes.c_void_p()
    checked(method(pointer, 0, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))(
        pointer, ctypes.byref(identifier), ctypes.byref(result)), 'QueryInterface')
    try:
        yield result
    finally:
        release(result)


@contextmanager
def shell_link():
    """Create IShellLinkW and release the COM apartment/interfaces we own."""
    if os.name != 'nt':
        raise OSError('Windows shortcuts can only be created on Windows.')
    ole32 = ctypes.WinDLL('ole32', use_last_error=True)
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ole32.CoInitializeEx.restype = ctypes.c_int32
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_uint32,
                                     ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_int32
    status = ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
    # An embedding caller may already own a different COM apartment. In that
    # case use it, but do not undo its initialization when this helper exits.
    own_apartment = status >= 0
    if not own_apartment and status & 0xffffffff != 0x80010106:  # RPC_E_CHANGED_MODE
        checked(status, 'CoInitializeEx')
    link = ctypes.c_void_p()
    try:
        checked(ole32.CoCreateInstance(ctypes.byref(CLSID_SHELL_LINK), None, 1,
                                      ctypes.byref(IID_SHELL_LINK), ctypes.byref(link)),
                'Create Shell link')  # CLSCTX_INPROC_SERVER
        yield link
    finally:
        release(link)
        if own_apartment:
            ole32.CoUninitialize()


def create_shortcut(project_root):
    project_root = Path(project_root).resolve()
    target = project_root / 'Gravewright Runner.bat'
    icon = project_root / 'scripts/windows/gravewright.ico'
    for source in (target, icon):
        if not source.is_file():
            raise FileNotFoundError(f'The project is incomplete: {source.name} is missing.')
    destination = project_root / 'Gravewright Runner.lnk'
    temporary = None
    try:
        with shell_link() as link:
            checked(method(link, 20, ctypes.c_wchar_p)(link, str(target)), 'Set shortcut target')
            checked(method(link, 9, ctypes.c_wchar_p)(link, str(project_root)), 'Set working directory')
            checked(method(link, 7, ctypes.c_wchar_p)(link, 'Start Gravewright Virtual Tabletop'), 'Set description')
            checked(method(link, 17, ctypes.c_wchar_p, ctypes.c_int)(link, str(icon), 0), 'Set project icon')
            checked(method(link, 15, ctypes.c_int)(link, 1), 'Set console window style')
            with interface(link, IID_PERSIST_FILE) as persist:
                # Save beside the target and replace atomically, preserving
                # any previous shortcut if Windows cannot finish the write.
                with tempfile.NamedTemporaryFile(dir=project_root, prefix='.Gravewright-',
                                                 suffix='.lnk', delete=False) as handle:
                    temporary = Path(handle.name)
                checked(method(persist, 6, ctypes.c_wchar_p, ctypes.c_int)(
                    persist, str(temporary), 1), 'Save shortcut')
        temporary.replace(destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        print(f'Project icon shortcut: {create_shortcut(args.project_root)}')
        return 0
    except (OSError, ValueError) as error:
        print(f'The optional icon shortcut could not be created: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
