"""PyInstaller runtime hook: set up MaaFw DLL search paths.

This runs BEFORE any user code, ensuring MaaFw DLLs are findable
when maa.__init__.py calls Library.open().

MaaFw DLLs live in _internal/maa/bin/. Their transitive deps (VC runtime)
come from the SYSTEM's VC++ Redistributable (C:\\Windows\\System32).

CRITICAL PACKAGING CONSTRAINT (see memory/17-packaging-v003-fixes.md):
  - PyInstaller's bundled msvcp140.dll MUST be removed from _internal/
    because it conflicts with MaaFw's opencv_world4_maa.dll (WinError 1114).
  - This makes VC++ 2015-2022 Redistributable a HARD requirement.
  - Do NOT add _internal/ to DLL search paths — it would reintroduce
    the conflict via the default search order.
  - Do NOT copy VC runtime DLLs into maa/bin/ — PyInstaller's versions
    may differ from the ones MaaFw was compiled against.
"""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    internal = Path(sys._MEIPASS)
    internal_str = str(internal)
    maa_bin = internal / "maa" / "bin"

    if maa_bin.exists():
        maa_bin_str = str(maa_bin)

        # Tell maa.__init__.py to load DLLs from maa/bin/
        os.environ["MAAFW_BINARY_PATH"] = maa_bin_str

        # Add maa/bin to PATH for MaaFw DLLs.
        # WARNING: Do NOT add _internal to PATH — PyInstaller's bundled
        # vcruntime140.dll conflicts with MaaFw's opencv_world4_maa.dll
        # (WinError 1114: DllMain initialization failure).
        os.environ["PATH"] = (
            maa_bin_str + os.pathsep +
            os.environ.get("PATH", "")
        )

        # Register maa/bin via os.add_dll_directory (Windows 10+ safe DLL search)
        try:
            os.add_dll_directory(maa_bin_str)
        except (OSError, AttributeError):
            pass
