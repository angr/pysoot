
class PySootError(Exception):
    pass


class ParameterError(PySootError):
    pass


class JythonClientException(PySootError):
    pass


class RecvException(PySootError):
    pass


class JavaNotFoundError(PySootError):
    pass


class MissingJavaRuntimeJarsError(PySootError):
    pass
