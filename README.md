PySoot
======

`pysoot` is a lifter from JAR/APK files to a Soot-like Python IR.

The `master` branch supports Python 3, the `py2k` branch supports Python2.

# Installation
`pip install .`

# How to use
```Python 3
from pysoot.lifter import Lifter
input_file = "tests/test_samples/simple1.jar" # the jar/apk you want to analyze
lifter = Lifter(input_file) # the default IR is Shimple, the default input_format is jar
classes = lifter.classes # get the IR of all the classes (as a dict of classes)
print(classes[list(classes.keys())[0]]) # print the IR of one of the translated classes
```

Many other examples are in `tests/test_pysoot.py`

# Requirements
* Java. Currently tested using OpenJDK 8 (`sudo apt-get install openjdk-8-jdk`).

Other components used by `pysoot` are:
* `jpype`, used for accessing Java from Python.
* `soot-trunk.jar`. This is a slightly modified version of the pre-compiled Soot JAR. At some point, I will upload its source code and the compilation script somewhere.
`pysoot` should also work with a normal version of `soot-trunk.jar`.

# Internals
#### Components
`pysoot` works by running Soot (compiled in the embedded `soot-trunk.jar`) using jpype, in `soot_manager.py`.

`lifter.py` uses `soot_manager.py` to translate the JAR/APK file to a Soot-like Python IR.

Classes in `pysoot.sootir` provide the exposed IR.
