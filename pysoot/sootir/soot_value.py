from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, unsafe_hash=True)
class SootValue:
    NAME_TO_CLASS = {}
    IREXPR_TO_EXPR = {}

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


@dataclass(slots=True, unsafe_hash=True)
class SootLocal(SootValue):
    name: str

    def __str__(self):
        return self.name

    @staticmethod
    def from_ir(type_, ir_value):
        return SootLocal(type_, str(ir_value.getName()))


@dataclass(slots=True, unsafe_hash=True)
class SootArrayRef(SootValue):
    base: SootValue
    index: SootValue

    def __str__(self):
        return "%s[%s]" % (self.base, self.index)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootArrayRef(
            type_,
            SootValue.from_ir(ir_value.getBase()),
            SootValue.from_ir(ir_value.getIndex()),
        )


@dataclass(slots=True, unsafe_hash=True)
class SootCaughtExceptionRef(SootValue):
    def __str__(self):
        return "Caught(%s)" % str(super(SootCaughtExceptionRef, self).__str__())

    @staticmethod
    def from_ir(type_, ir_value):
        return SootCaughtExceptionRef(type_)


@dataclass(slots=True, unsafe_hash=True)
class SootParamRef(SootValue):
    index: int

    def __str__(self):
        return "@parameter%d[%s]" % (self.index, self.type)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootParamRef(type_, int(ir_value.getIndex()))


@dataclass(slots=True, unsafe_hash=True)
class SootThisRef(SootValue):
    def __str__(self):
        return "@this[%s]" % str(self.type)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootThisRef(type_)


@dataclass(slots=True, unsafe_hash=True)
class SootStaticFieldRef(SootValue):
    field: tuple[str, str]

    def __str__(self):
        return "StaticFieldRef %s" % (self.field,)

    @staticmethod
    def from_ir(type_, ir_value):
        raw_field = ir_value.getField()
        return SootStaticFieldRef(type_, (str(raw_field.getName()), str(raw_field.getDeclaringClass().getName())))


@dataclass(slots=True, unsafe_hash=True)
class SootInstanceFieldRef(SootValue):
    base: SootValue
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


@dataclass(slots=True, unsafe_hash=True)
class SootClassConstant(SootValue):
    value: str

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootClassConstant(type_, str(ir_value.getValue()))


@dataclass(slots=True, unsafe_hash=True)
class SootDoubleConstant(SootValue):
    value: float

    def __str__(self):
        return str(self.value) + "d"

    @staticmethod
    def from_ir(type_, ir_value):
        return SootDoubleConstant(type_, float(ir_value.value))


@dataclass(slots=True, unsafe_hash=True)
class SootFloatConstant(SootValue):
    value: float

    def __str__(self):
        return str(self.value) + "f"

    @staticmethod
    def from_ir(type_, ir_value):
        return SootFloatConstant(type_, float(ir_value.value))


@dataclass(slots=True, unsafe_hash=True)
class SootIntConstant(SootValue):
    value: int

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootIntConstant(type_, int(ir_value.value))


@dataclass(slots=True, unsafe_hash=True)
class SootLongConstant(SootValue):
    value: int

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_ir(type_, ir_value):
        return SootLongConstant(type_, int(ir_value.value))


@dataclass(slots=True, unsafe_hash=True)
class SootNullConstant(SootValue):
    def __str__(self):
        return "null"

    @staticmethod
    def from_ir(type_, ir_value):
        return SootNullConstant(type_)


@dataclass(slots=True, unsafe_hash=True)
class SootStringConstant(SootValue):
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
