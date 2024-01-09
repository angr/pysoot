from __future__ import annotations

import os

import jpype
import psutil
from jpype.types import JClass

from pysoot.sootir.soot_class import SootClass

jpype.addClassPath(os.path.join(os.path.dirname(__file__), "soot-trunk.jar"))
jpype.startJVM("-Xmx2G")

class SootManager:
    def __init__(self, java_heap_size: int | None = None):
        if java_heap_size is None:
            # use 75% of total memory for the Java heap
            self.java_heap_size = int(psutil.virtual_memory().total*0.75)
        else:
            self.java_heap_size = java_heap_size


    def init(self, main_class, input_file, input_format: str, android_sdk: str | None, soot_classpath: str | None, ir_format: str):
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

        self.scene = Scene.v()
        self.raw_classes = self.scene.getClasses()
        self.class_name_map = {c.getName(): c for c in self.raw_classes}
        self.hierarchy = Hierarchy()

    def get_classes(self):
        classes = {}
        for raw_class in self.raw_classes:
            # TODO with this we only get classes for which we have all the code
            # soot also has classes with lower "resolving levels", but for those we may not have
            # the method list or the code, if we want them we cannot fully translate them
            if raw_class.isApplicationClass():
                soot_class = SootClass.from_ir(raw_class)
                classes[soot_class.name] = soot_class
        return classes

    def getSubclassesOf(self, class_name: str) -> list[str]:
        return [c.getName() for c in self.hierarchy.getSubclassesOf(self.class_name_map[class_name])]
