from __future__ import annotations

import os
import logging
import subprocess
import zipfile

from .errors import (
    JavaNotFoundError,
    MissingJavaRuntimeJarsError,
    ParameterError,
    UnsupportedClassFileVersionError,
)


log = logging.getLogger("pysoot.lifter")

# The ASM bundled in soot-trunk.jar predates Java 9: its ClassReader compares
# the class file major version against a literal 52 and throws a message-less
# IllegalArgumentException above it. Soot reads every class entry of the input
# JAR, so a single too-new entry aborts the whole lift.
_MAX_CLASS_FILE_VERSION = 52

_CLASS_FILE_MAGIC = b"\xca\xfe\xba\xbe"


class Lifter:
    def __init__(
        self,
        input_file: str,
        input_format="jar",
        ir_format="shimple",
        additional_jars=None,
        additional_jar_roots=None,
        android_sdk=None,
        android_api_version=None,
    ):
        self.input_file = os.path.realpath(input_file)
        allowed_irs = ["shimple", "jimple"]
        if ir_format not in allowed_irs:
            raise ParameterError("ir_format needs to be in " + repr(allowed_irs))
        self.ir_format = ir_format

        allowed_formats = ["jar", "apk", "dex"]
        if input_format not in allowed_formats:
            raise ParameterError("format needs to be in " + repr(allowed_formats))
        self.input_format = input_format

        if input_format == "jar":
            if android_sdk is not None:
                log.warning(
                    "when input_format is 'jar', setting android_sdk is pointless"
                )
            absolute_library_jars = {_find_jrt_jar()}
            if additional_jars is not None:
                absolute_library_jars |= {
                    os.path.realpath(jar) for jar in additional_jars
                }
            if additional_jar_roots is not None:
                for jar_root in additional_jar_roots:
                    for jar_name in os.listdir(jar_root):
                        if jar_name.endswith(".jar"):
                            absolute_path = os.path.realpath(
                                os.path.join(jar_root, jar_name)
                            )
                            if absolute_path not in absolute_library_jars:
                                absolute_library_jars.add(absolute_path)
            seperator = ";" if os.name == "nt" else ":"
            bad_jars = [p for p in absolute_library_jars if seperator in p]
            if len(bad_jars) > 0:
                raise ParameterError(
                    "these jars have a semicolon in their name: " + repr(bad_jars)
                )
            self.soot_classpath = seperator.join(absolute_library_jars)
            _check_class_file_versions(self.input_file)

        elif input_format in ("apk", "dex"):
            if android_sdk is None:
                raise ParameterError(
                    f"when format is {input_format}, android_sdk should point to "
                    "something like: ~/Android/Sdk/platforms"
                )
            if input_format == "dex" and android_api_version is None:
                raise ParameterError(
                    "when format is dex, android_api_version must be given: a bare "
                    "dex file carries no manifest declaring the API level to resolve "
                    "the Android class library against"
                )
            if additional_jars is not None or additional_jar_roots is not None:
                log.warning(
                    "when input_format is '%s', setting additional_jars or "
                    "additional_jar_roots is pointless",
                    input_format,
                )
            self.android_sdk = android_sdk
            self.android_api_version = android_api_version

        self._get_ir()

    def _get_ir(self):
        config = {}
        settings = [
            "input_file",
            "input_format",
            "ir_format",
            "android_sdk",
            "android_api_version",
            "soot_classpath",
        ]
        for s in settings:
            config[s] = str(getattr(self, s, None))

        from .soot_manager import run_soot  # pylint: disable=import-outside-toplevel

        log.info("Running Soot with the following config: " + repr(config))
        self.classes, self._hierarchy = run_soot(**config)

    def getSubclassesOf(self, class_name: str) -> list[str]:
        """Return pre-computed subclasses of the given class name."""
        return self._hierarchy.get(class_name, [])


def _check_class_file_versions(jar_path: str) -> None:
    # Soot also lifts a directory of class files, and reports a missing or
    # unreadable input itself. Only an archive this can open is ours to read.
    if not os.path.isfile(jar_path) or not zipfile.is_zipfile(jar_path):
        return

    too_new = []
    with zipfile.ZipFile(jar_path) as jar:
        for info in jar.infolist():
            if not info.filename.endswith(".class"):
                continue
            with jar.open(info) as entry:
                header = entry.read(8)
            if len(header) < 8 or not header.startswith(_CLASS_FILE_MAGIC):
                continue
            major = int.from_bytes(header[6:8], "big")
            if major > _MAX_CLASS_FILE_VERSION:
                too_new.append((info.filename, major))

    if not too_new:
        return

    name, major = too_new[0]
    message = (
        f"{jar_path}: {name} has class file version {major} (Java {major - 44}), "
        f"but the bundled Soot understands at most version "
        f"{_MAX_CLASS_FILE_VERSION} (Java 8). Build the input for Java 8."
    )
    if len(too_new) > 1:
        message += f" {len(too_new)} class files in this JAR are too new."
    raise UnsupportedClassFileVersionError(message)


def _get_java_home() -> str:
    # Use $JAVA_HOME if it is set
    if "JAVA_HOME" in os.environ:
        return os.environ["JAVA_HOME"]

    # Command to get Java properties
    command = ["java", "-XshowSettings:properties", "-version"]
    # Execute the command and capture the output
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except OSError as e:
        raise JavaNotFoundError from e
    # Extract JAVA_HOME from the output
    for line in result.stderr.splitlines():
        if "java.home" in line:
            return line.split("=")[1].strip()

    raise JavaNotFoundError


def _find_jrt_jar() -> str:
    java_home = _get_java_home()
    jrt_fs = os.path.join(java_home, "lib", "jrt-fs.jar")
    if not os.path.exists(jrt_fs):
        raise MissingJavaRuntimeJarsError
    return jrt_fs
