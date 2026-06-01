"""Hatchling build hook that compiles the GraalVM native library.

Runs `pysoot/java/build.sh` to produce `pysoot/libpysoot.{dylib,so,dll}`
before hatchling packages the wheel. If the library already exists the
build is skipped so repeat `uv sync` calls don't trigger a multi-minute
GraalVM rebuild.

Requirements: GraalVM (with native-image) installed and either on PATH or
reachable via $GRAALVM_HOME.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _lib_filename() -> str:
    if sys.platform == "darwin":
        return "libpysoot.dylib"
    if sys.platform == "win32":
        return "libpysoot.dll"
    return "libpysoot.so"


class GraalvmNativeBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        build_script = root / "pysoot" / "java" / "build.sh"
        lib_path = root / "pysoot" / _lib_filename()

        if lib_path.exists():
            self.app.display_info(
                f"Native library already present at {lib_path}; skipping build."
            )
            return

        if not build_script.exists():
            self.app.display_warning(
                f"Native library missing and build script not found at {build_script}; "
                "wheel will not include a usable libpysoot."
            )
            return

        if shutil.which("bash") is None:
            raise RuntimeError(
                "bash is required to run pysoot/java/build.sh but was not found "
                "on PATH. Either install bash or run the script manually with "
                "an equivalent shell."
            )

        self.app.display_info(f"Building GraalVM native library via {build_script}")
        subprocess.run(["bash", str(build_script)], check=True, cwd=root)

        if not lib_path.exists():
            raise RuntimeError(
                f"build.sh completed but {lib_path} was not produced. "
                "Check the build output above."
            )
