class PySootError(Exception):
    pass


class ParameterError(PySootError):
    pass


class JavaNotFoundError(PySootError):
    pass


class MissingJavaRuntimeJarsError(PySootError):
    pass


class UnsupportedClassFileVersionError(PySootError):
    pass
