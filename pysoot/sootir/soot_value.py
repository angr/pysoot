from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SootValue:
    type: str

    def __str__(self):
        return str(self.type)


@dataclass(slots=True, frozen=True)
class SootLocal(SootValue):
    name: str

    def __str__(self):
        return self.name


@dataclass(slots=True, frozen=True)
class SootArrayRef(SootValue):
    base: SootValue
    index: SootValue

    def __str__(self):
        return f"{self.base}[{self.index}]"


@dataclass(slots=True, frozen=True)
class SootCaughtExceptionRef(SootValue):
    def __str__(self):
        return f"Caught({str(super(SootCaughtExceptionRef, self).__str__())})"


@dataclass(slots=True, frozen=True)
class SootParamRef(SootValue):
    index: int

    def __str__(self):
        return f"@parameter{self.index}[{self.type}]"


@dataclass(slots=True, frozen=True)
class SootThisRef(SootValue):
    def __str__(self):
        return f"@this[{str(self.type)}]"


@dataclass(slots=True, frozen=True)
class SootStaticFieldRef(SootValue):
    field: tuple[str, str]

    def __str__(self):
        return f"StaticFieldRef {self.field}"


@dataclass(slots=True, frozen=True)
class SootInstanceFieldRef(SootValue):
    base: SootValue
    field: tuple[str, str]

    def __str__(self):
        return f"{str(self.base)}.{str(self.field)}"


@dataclass(slots=True, frozen=True)
class SootClassConstant(SootValue):
    value: str

    def __str__(self):
        return str(self.value)


@dataclass(slots=True, frozen=True)
class SootDoubleConstant(SootValue):
    value: float

    def __str__(self):
        return str(self.value) + "d"


@dataclass(slots=True, frozen=True)
class SootFloatConstant(SootValue):
    value: float

    def __str__(self):
        return str(self.value) + "f"


@dataclass(slots=True, frozen=True)
class SootIntConstant(SootValue):
    value: int

    def __str__(self):
        return str(self.value)


@dataclass(slots=True, frozen=True)
class SootLongConstant(SootValue):
    value: int

    def __str__(self):
        return str(self.value)


@dataclass(slots=True, frozen=True)
class SootNullConstant(SootValue):
    def __str__(self):
        return "null"


@dataclass(slots=True, frozen=True)
class SootStringConstant(SootValue):
    value: str

    def __str__(self):
        # this automatically adds quotes and escape weird characters using Python-style
        return repr(self.value)
