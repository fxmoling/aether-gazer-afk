"""PyInstaller runtime hook: set up MaaFw DLL search paths.

This runs BEFORE any user code, ensuring MaaFw DLLs are findable
when maa.__init__.py calls Library.open().

MaaFw DLLs live in _internal/maa/bin/. Their transitive deps (VC runtime)
are in _internal/. We add BOTH directories to the DLL search path.

IMPORTANT: Do NOT copy VC runtime DLLs into maa/bin/ — PyInstaller's
bundled versions may differ from the ones MaaFw was compiled against,
causing DllMain initialization failures (WinError 1114).
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
