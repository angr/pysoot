#!/usr/bin/env python

import logging
import os
import pickle
import tempfile

from pysoot.lifter import Lifter


logging.basicConfig(format='%(levelname)-7s | %(asctime)-23s | %(name)-8s | %(message)s', level=logging.DEBUG)
l = logging.getLogger("pysoot.test.test_pysoot")
self_location_folder = os.path.dirname(os.path.realpath(__file__))
test_samples_folder = os.path.join(self_location_folder, "../../binaries/tests/java")
test_samples_folder_private = os.path.join(self_location_folder, "../../binaries-private/java")


def compare_code(tstr1, tstr2):
    for l1, l2 in zip(tstr1.split("\n"), tstr2.split("\n")):
        if l1.strip().startswith("//") and l2.strip().startswith("//"):
            continue
        assert l1 == l2


def _simple1_tests(ir_format):
    jar = os.path.join(test_samples_folder, "simple1.jar")
    lifter = Lifter(jar, ir_format=ir_format)
    classes = lifter.classes

    print(classes.keys())
    assert "simple1.Class1" in classes.keys()
    assert "simple1.Class2" in classes.keys()

    test_str = ["r0", "public", "specialinvoke"]
    assert all([t in str(classes['simple1.Class1']) for t in test_str])
    assert all([t in str(classes['simple1.Class2']) for t in test_str])


def _simple2_tests(ir_format):
    jar = os.path.join(test_samples_folder, "simple2.jar")
    lifter = Lifter(jar, ir_format=ir_format)
    cc = lifter.classes['simple2.Class1']

    tstr = str(cc)
    tokens = ["new int", "instanceof simple2.Class1", "parameter0", "Caught", "Throw",
              " = 2", "goto", "switch", "START!", "valueOf"]
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


def test_hierarchy():
    jar = os.path.join(test_samples_folder, "simple2.jar")
    lifter = Lifter(jar)
    test_subc = ["simple2.Class2", "simple2.Class1", "java.lang.System"]
    subc = lifter.soot_wrapper.getSubclassesOf("java.lang.Object")
    assert all([c in subc for c in test_subc])


def test_exceptions1():
    jar = os.path.join(test_samples_folder, "exceptions1.jar")
    lifter = Lifter(jar)

    mm = lifter.classes["exceptions1.Main"].methods[1]
    assert mm.basic_cfg[mm.blocks[0]] == [mm.blocks[1], mm.blocks[2]]
    assert len(mm.exceptional_preds) == 1

    preds = mm.exceptional_preds[mm.blocks[18]]
    for i, block in enumerate(mm.blocks):
        if i in [0, 1, 2, 17, 18, 19]:
            assert not block in preds
        elif i in [3, 4, 5, 14, 15, 16]:
            assert block in preds

def test_android1():
    # TODO consider adding Android Sdk in the CI server
    sdk_path = os.path.join(os.path.expanduser("~"), "Android/Sdk/platforms/")
    if not os.path.exists(sdk_path):
        l.warning("cannot run test_android1 since there is no Android SDK folder")
        return
    apk = os.path.join(test_samples_folder, "android1.apk")
    lifter = Lifter(apk, input_format="apk", android_sdk=sdk_path)
    subc = lifter.soot_wrapper.getSubclassesOf("java.lang.Object")
    assert "com.example.antoniob.android1.MainActivity" in subc
    main_activity = lifter.classes["com.example.antoniob.android1.MainActivity"]

    tstr = str(main_activity)
    tokens = ["onCreate", "ANDROID1", "TAG", "Random", "android.os.Bundle", "34387"]
    for t in tokens:
        assert t in tstr
    # l.debug("client std\n%s" % lifter.soot_wrapper.get_client_std())
test_android1.speed = "slow"


def test_textcrunchr1():
    if not os.path.exists(test_samples_folder_private):
        l.warning("cannot run test_textcrunchr1 since there is no binaries-private folder")
        return
    jar = os.path.join(test_samples_folder_private, "textcrunchr_1.jar")
    additional_jar_roots = [os.path.join(test_samples_folder_private, "textcrunchr_libs")]
    lifter = Lifter(jar, additional_jar_roots=additional_jar_roots)

    tstr = str(lifter.classes['com.cyberpointllc.stac.textcrunchr.CharacterCountProcessor'])
    tokens = ["getName", "Character Count", ">10,000 characters", "new char[10000]", "process",
              "com.cyberpointllc.stac.textcrunchr.TCResult"]
    for t in tokens:
        assert t in tstr
test_textcrunchr1.speed = "slow"

def test_ipc_options():
    jar = os.path.join(test_samples_folder, "simple2.jar")
    for split_results in [0, 10, 100]:
        lifter = Lifter(jar)
        cc = lifter.classes['simple2.Class1']
        tstr = str(cc)
        tokens = ["new int", "instanceof simple2.Class1", "parameter0", "Caught", "Throw",
                  " = 2", "goto", "switch", "START!", "valueOf"]
        for t in tokens:
            assert t in tstr

        sw = lifter.soot_wrapper
        res = sw.get_classes(_ipc_options={'return_result': False, 'return_pickle': False,
                                           'save_pickle': None, 'split_results': split_results})
        assert res is None
        res, pres = sw.get_classes(_ipc_options={'return_result': True, 'return_pickle': True,
                                                 'save_pickle': None, 'split_results': split_results})
        res2 = pickle.loads(pres)
        compare_code(str(res['simple2.Class1']), str(res2['simple2.Class1']))
        res = sw.get_classes(_ipc_options={'return_result': True, 'return_pickle': False,
                                           'save_pickle': None, 'split_results': split_results})
        compare_code(str(res['simple2.Class1']), tstr)
        res, pres = sw.get_classes(_ipc_options={'return_result': False, 'return_pickle': True,
                                                 'save_pickle': None, 'split_results': split_results})
        assert res is None
        assert pres is not None

        classes = [u'simple2.Interface2', u'simple2.Interface1', u'simple2.Class1$Inner1',
                   u'simple2.Class2', u'simple2.Class1']
        try:
            fname = tempfile.mktemp()
            res1 = sw.get_classes(_ipc_options={'return_result': False, 'return_pickle': False,
                                                'save_pickle': fname, 'split_results': split_results})
            assert res1 is None
            res2 = pickle.load(open(fname, "rb"))
            compare_code(str(res2['simple2.Class1']), tstr)
        finally:
            os.unlink(fname)
        try:
            fname = tempfile.mktemp()
            res1 = sw.get_classes(_ipc_options={'return_result': True, 'return_pickle': False,
                                                'save_pickle': fname, 'split_results': split_results})
            assert res1 is not None
            res2 = pickle.load(open(fname, "rb"))
            compare_code(str(res1['simple2.Class1']), str(res2['simple2.Class1']))
        finally:
            os.unlink(fname)
        try:
            fname = tempfile.mktemp()
            jar = os.path.join(test_samples_folder, "simple2.jar")
            Lifter(jar, save_to_file=fname)
            res2 = pickle.load(open(fname, "rb"))
            assert set(classes) == set(res2.keys())
        finally:
            os.unlink(fname)


def test_lift_simple1_shimple():
    _simple1_tests("shimple")


def test_lift_simple1_jimple():
    _simple1_tests("jimple")


def test_str_simple2_shimple():
    _simple2_tests("shimple")


def test_str_simple2_jimple():
    _simple2_tests("jimple")


def run_all():
    functions = globals()
    all_functions = { k:v for k, v in functions.items() if k.startswith('test_') and hasattr(v, '__call__') }
    for f in sorted(all_functions.keys()):
        l.info(">" * 50 + " testing %s" % str(f))
        all_functions[f]()
        l.info("<" * 50 + " test %s passed" % str(f))


if __name__ == "__main__":
    import sys
    logging.getLogger("pysoot.test.test_pysoot").setLevel("DEBUG")
    logging.getLogger("pysoot.jython_wrapper").setLevel("DEBUG")
    logging.getLogger("pysoot.lifter").setLevel("DEBUG")

    if len(sys.argv) > 1:
        globals()['test_' + sys.argv[1]]()
    else:
        run_all()
