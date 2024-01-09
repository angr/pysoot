from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jpype.types import JDouble, JFloat, JInt, JLong, JString


@dataclass(unsafe_hash=True)
class SootValue:
    NAME_TO_CLASS = {}
    IREXPR_TO_EXPR = {}

    __slots__ = ["type"]  # TODO: replace with dataclass in Python 3.10
    type: str

    def __str__(self):
        return str(self.type)

    @staticmethod
    def from_ir(ir_value):
        subtype = ir_value.getClass().getSimpleName()
        subtype = subtype.replace("Jimple", "").replace("Shimple", "")

        if subtype.endsWith("Expr"):
            from .soot_expr import SootExpr

            expr = SootExpr.from_ir(ir_value)
            SootValue.IREXPR_TO_EXPR[ir_value] = expr
            return expr

        cls = SootValue.NAME_TO_CLASS.get(subtype, None)

        if cls is None:
            raise NotImplementedError("Unsupported SootValue type %s." % subtype)

        return cls.from_ir(str(ir_value.getType()), ir_value)


@dataclass(unsafe_hash=True)
class SootLocal(SootValue):
    __slots__ = ["name"]  # TODO: replace with dataclass in Python 3.10
    name: str

    def __str__(self):
        return self.name

    @staticmethod
    def from_ir(type_, ir_value):
        return SootLocal(type_, str(ir_value.getName()))


@dataclass(unsafe_hash=True)
class SootArrayRef(SootValue):
    __slots__ = ["base", "index"]  # TODO: replace with dataclass in Python 3.10
    base: Any
    index: Any

    def __str__(self):
        return "%s[%s]" % (self.base, self.index)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootArrayRef(
            type_,
            SootValue.from_ir(ir_value.getBase()),
            SootValue.from_ir(ir_value.getIndex()),
        )


@dataclass(unsafe_hash=True)
class SootCaughtExceptionRef(SootValue):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "Caught(%s)" % str(super(SootCaughtExceptionRef, self).__str__())

    @staticmethod
    def from_ir(type_, ir_value):
        return SootCaughtExceptionRef(type_)


@dataclass(unsafe_hash=True)
class SootParamRef(SootValue):
    __slots__ = ["index"]  # TODO: replace with dataclass in Python 3.10
    index: Any

    def __str__(self):
        return "@parameter%d[%s]" % (self.index, self.type)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootParamRef(type_, ir_value.getIndex())


@dataclass(unsafe_hash=True)
class SootThisRef(SootValue):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "@this[%s]" % str(self.type)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootThisRef(type_)


@dataclass(unsafe_hash=True)
class SootStaticFieldRef(SootValue):
    __slots__ = ["field"]  # TODO: replace with dataclass in Python 3.10
    field: Any

    def __str__(self):
        return "StaticFieldRef %s" % (self.field,)

    @staticmethod
    def from_ir(type_, ir_value):
        raw_field = ir_value.getField()
        return SootStaticFieldRef(type_, (str(raw_field.getName()), str(raw_field.getDeclaringClass().getName())))


@dataclass(unsafe_hash=True)
class SootInstanceFieldRef(SootValue):
    __slots__ = ["base", "field"]  # TODO: replace with dataclass in Python 3.10
    base: Any
    field: tuple[str, str]

    def __str__(self):
        return "%s.%s" % (str(self.base), str(self.field))

    @staticmethod
    def from_ir(type_, ir_value):
        field = ir_value.getField()
        return SootInstanceFieldRef(
            type_,
            SootValue.from_ir(ir_value.getBase()),
            (str(field.getName()), str(field.getDeclaringClass().getName())),
        )


@dataclass(unsafe_hash=True)
class SootClassConstant(SootValue):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: Any

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootClassConstant(type_, ir_value)


@dataclass(unsafe_hash=True)
class SootDoubleConstant(SootValue):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: float

    def __str__(self):
        return str(self.value) + "d"

    @staticmethod
    def from_ir(type_, ir_value):
        return SootDoubleConstant(type_, float(ir_value.value))


@dataclass(unsafe_hash=True)
class SootFloatConstant(SootValue):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: float

    def __str__(self):
        return str(self.value) + "f"

    @staticmethod
    def from_ir(type_, ir_value):
        return SootFloatConstant(type_, float(ir_value.value))


@dataclass(unsafe_hash=True)
class SootIntConstant(SootValue):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: int

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootIntConstant(type_, int(ir_value.value))


@dataclass(unsafe_hash=True)
class SootLongConstant(SootValue):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: int

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootLongConstant(type_, int(ir_value.value))


@dataclass(unsafe_hash=True)
class SootNullConstant(SootValue):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "null"

    @staticmethod
    def from_ir(type_, ir_value):
        return SootNullConstant(type_)


@dataclass(unsafe_hash=True)
class SootStringConstant(SootValue):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: str

    def __str__(self):
        # this automatically adds quotes and escape weird characters using Python-style
        return repr(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootStringConstant(type_, str(ir_value.value))


SootValue.NAME_TO_CLASS = {
    "Local": SootLocal,
    "JArrayRef": SootArrayRef,
    "JCaughtExceptionRef": SootCaughtExceptionRef,
    "JInstanceFieldRef": SootInstanceFieldRef,
    "ParameterRef": SootParamRef,
    "ThisRef": SootThisRef,
    "StaticFieldRef": SootStaticFieldRef,
    "ClassConstant": SootClassConstant,
    "DoubleConstant": SootDoubleConstant,
    "FloatConstant": SootFloatConstant,
    "IntConstant": SootIntConstant,
    "LongConstant": SootLongConstant,
    "NullConstant": SootNullConstant,
    "StringConstant": SootStringConstant,
}
