#!/usr/bin/env python

import os
import unittest

from pysoot.lifter import Lifter


class TestPySoot(unittest.TestCase):
    test_samples_folder = os.path.join(
        os.path.join(os.path.dirname(__file__), "..", "..", "binaries", "tests", "java")
    )
    test_samples_folder_private = os.path.join(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "binaries-private", "tests", "java"
        )
    )
    android_sdk_path = os.path.join(
        os.path.expanduser("~"), "Android", "Sdk", "platforms"
    )

    def compare_code(self, tstr1, tstr2):
        for l1, l2 in zip(tstr1.split("\n"), tstr2.split("\n")):
            if l1.strip().startswith("//") and l2.strip().startswith("//"):
                continue
            assert l1 == l2

    def _simple1_tests(self, ir_format):
        jar = os.path.join(self.test_samples_folder, "simple1.jar")
        lifter = Lifter(jar, ir_format=ir_format)
        classes = lifter.classes

        assert "simple1.Class1" in classes.keys()
        assert "simple1.Class2" in classes.keys()

        test_str = ["r0", "public", "specialinvoke"]
        assert all([t in str(classes["simple1.Class1"]) for t in test_str])
        assert all([t in str(classes["simple1.Class2"]) for t in test_str])

    def _simple2_tests(self, ir_format):
        jar = os.path.join(self.test_samples_folder, "simple2.jar")
        lifter = Lifter(jar, ir_format=ir_format)
        cc = lifter.classes["simple2.Class1"]

        tstr = str(cc)
        tokens = [
            "new int",
            "instanceof simple2.Class1",
            "parameter0",
            "Caught",
            "Throw",
            " = 2",
            "goto",
            "switch",
            "START!",
            "valueOf",
        ]
        for t in tokens:
            assert t in tstr

        # Phi instructions only exist in SSA form (shimple)
        if ir_format == "jimple":
            assert "Phi" not in tstr
        elif ir_format == "shimple":
            assert "Phi" in tstr

        # "<pysoot" in a line (outside comments) means that a str is missing (and therefore repr was used)
        for line in tstr.split("\n"):
            line = line.split("//")[0]
            assert "<pysoot" not in line

    def test_hierarchy(self):
        jar = os.path.join(self.test_samples_folder, "simple2.jar")
        lifter = Lifter(jar)
        # Only check application classes — JDK classes (e.g. java.lang.System)
        # are phantom refs on modular JDKs (Java 9+) and won't appear in the hierarchy.
        test_subc = ["simple2.Class2", "simple2.Class1"]
        subc = lifter.soot_wrapper.getSubclassesOf("java.lang.Object")
        assert all([c in subc for c in test_subc])

    def test_exceptions1(self):
        jar = os.path.join(self.test_samples_folder, "exceptions1.jar")
        lifter = Lifter(jar)

        mm = lifter.classes["exceptions1.Main"].methods[1]
        assert mm.basic_cfg[mm.blocks[0]] == (mm.blocks[1], mm.blocks[2])
        assert len(mm.exceptional_preds) == 1

        preds = mm.exceptional_preds[mm.blocks[18]]
        for i, block in enumerate(mm.blocks):
            if i in [0, 1, 2, 17, 18, 19]:
                assert block not in preds
            elif i in [3, 4, 5, 14, 15, 16]:
                assert block in preds

    # TODO consider adding Android Sdk in the CI server
    @unittest.skipUnless(os.path.exists(android_sdk_path), "Android SDK not found")
    def test_android1(self):
        apk = os.path.join(self.test_samples_folder, "android1.apk")
        lifter = Lifter(apk, input_format="apk", android_sdk=self.android_sdk_path)
        subc = lifter.soot_wrapper.getSubclassesOf("java.lang.Object")
        assert "com.example.antoniob.android1.MainActivity" in subc
        main_activity = lifter.classes["com.example.antoniob.android1.MainActivity"]

        tstr = str(main_activity)
        tokens = ["onCreate", "ANDROID1", "TAG", "Random", "android.os.Bundle", "34387"]
        for t in tokens:
            assert t in tstr

    test_android1.speed = "slow"

    @unittest.skipUnless(
        os.path.exists(test_samples_folder_private), "binaries-private not found"
    )
    def test_textcrunchr1(self):
        jar = os.path.join(self.test_samples_folder_private, "textcrunchr_1.jar")
        additional_jar_roots = [
            os.path.join(self.test_samples_folder_private, "textcrunchr_libs")
        ]
        lifter = Lifter(jar, additional_jar_roots=additional_jar_roots)

        tstr = str(
            lifter.classes["com.cyberpointllc.stac.textcrunchr.CharacterCountProcessor"]
        )
        tokens = [
            "getName",
            "Character Count",
            ">10,000 characters",
            "new char[10000]",
            "process",
            "com.cyberpointllc.stac.textcrunchr.TCResult",
        ]
        for t in tokens:
            assert t in tstr

    test_textcrunchr1.speed = "slow"

    def test_lift_simple1_shimple(self):
        self._simple1_tests("shimple")

    def test_lift_simple1_jimple(self):
        self._simple1_tests("jimple")

    def test_str_simple2_shimple(self):
        self._simple2_tests("shimple")

    def test_str_simple2_jimple(self):
        self._simple2_tests("jimple")


if __name__ == "__main__":
    unittest.main()
