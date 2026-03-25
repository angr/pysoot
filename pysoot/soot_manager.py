from __future__ import annotations

import os

import jpype
from jpype.types import JClass

from pysoot.sootir.soot_class import SootClass


def _start_jvm():
    if jpype.isJVMStarted():
        return
    jpype.addClassPath(os.path.join(os.path.dirname(__file__), "soot-trunk.jar"))
    jpype.startJVM("-Xmx2G")
    if os.name != "nt":
        os.register_at_fork(before=jpype.shutdownJVM)


def run_soot(
    input_file: str,
    input_format: str,
    android_sdk: str | None,
    soot_classpath: str | None,
    ir_format: str,
) -> tuple[dict[str, SootClass], dict[str, list[str]]]:
    """Run Soot on the given input and return (classes, hierarchy).

    classes: dict mapping class name to SootClass (application classes only)
    hierarchy: dict mapping class name to list of subclass names
    """
    _start_jvm()

    Collections = JClass("java.util.Collections")
    G = JClass("soot.G")
    Hierarchy = JClass("soot.Hierarchy")
    Options = JClass("soot.options.Options")
    PackManager = JClass("soot.PackManager")
    Scene = JClass("soot.Scene")

    G.reset()

    Options.v().set_process_dir(Collections.singletonList(input_file))

    if input_format == "apk":
        Options.v().set_android_jars(android_sdk)
        Options.v().set_process_multiple_dex(True)
        Options.v().set_src_prec(Options.src_prec_apk)
    elif input_format == "jar":
        Options.v().set_soot_classpath(soot_classpath)
    else:
        raise Exception("invalid input type")

    if ir_format == "jimple":
        Options.v().set_output_format(Options.output_format_jimple)
    elif ir_format == "shimple":
        Options.v().set_output_format(Options.output_format_shimple)
    else:
        raise Exception("invalid ir format")

    Options.v().set_allow_phantom_refs(True)

    # this options may or may not work
    Options.v().setPhaseOption("cg", "all-reachable:true")
    Options.v().setPhaseOption("jb.dae", "enabled:false")
    Options.v().setPhaseOption("jb.uce", "enabled:false")
    Options.v().setPhaseOption("jj.dae", "enabled:false")
    Options.v().setPhaseOption("jj.uce", "enabled:false")

    # this avoids an exception in some apks
    Options.v().set_wrong_staticness(Options.wrong_staticness_ignore)

    Scene.v().loadNecessaryClasses()
    PackManager.v().runPacks()

    raw_classes = Scene.v().getClasses()
    class_name_map = {c.getName(): c for c in raw_classes}

    # Convert application classes to Python IR
    classes = {}
    for raw_class in raw_classes:
        if raw_class.isApplicationClass():
            soot_class = SootClass.from_ir(raw_class)
            classes[soot_class.name] = soot_class

    # Pre-compute subclass relationships
    hierarchy_obj = Hierarchy()
    hierarchy = {}
    for name, raw_class in class_name_map.items():
        try:
            hierarchy[name] = [
                c.getName() for c in hierarchy_obj.getSubclassesOf(raw_class)
            ]
        except Exception:
            # Some classes (e.g. interfaces) may not support getSubclassesOf
            pass

    return classes, hierarchy
