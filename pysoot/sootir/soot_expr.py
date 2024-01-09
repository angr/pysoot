from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .soot_value import SootValue


@dataclass(unsafe_hash=True)
class SootExpr(SootValue):
    NAME_TO_CLASS = {}

    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    @staticmethod
    def from_ir(ir_expr):
        subtype = ir_expr.getClass().getSimpleName()
        cls = SootExpr.NAME_TO_CLASS.get(subtype, None)
        if cls is None:
            raise NotImplementedError("Unsupported Soot expression type %s." % subtype)

        return cls.from_ir(str(ir_expr.getType()), subtype, ir_expr)


@dataclass(unsafe_hash=True)
class SootBinopExpr(SootExpr):
    __slots__ = [
        "op",
        "value1",
        "value2",
    ]  # TODO: replace with dataclass in Python 3.10
    op: str
    value1: SootValue
    value2: SootValue

    def __str__(self):
        return "%s %s %s" % (
            str(self.value1),
            SootExpr.OP_TO_STR[self.op],
            str(self.value2),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        op = expr_name[1:].replace("Expr", "").lower()

        return SootBinopExpr(
            type_,
            op,
            SootValue.from_ir(ir_subvalue.getOp1()),
            SootValue.from_ir(ir_subvalue.getOp2()),
        )


@dataclass(unsafe_hash=True)
class SootUnopExpr(SootExpr):
    __slots__ = ["op", "value"]  # TODO: replace with dataclass in Python 3.10
    op: str
    value: SootValue

    def __str__(self):
        return "%s %s" % (SootExpr.OP_TO_STR[self.op], str(self.value))

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        op = expr_name[1:].replace("Expr", "").lower()
        return SootUnopExpr(type_, op, SootValue.from_ir(ir_subvalue.getOp()))


@dataclass(unsafe_hash=True)
class SootCastExpr(SootExpr):
    __slots__ = ["cast_type", "value"]  # TODO: replace with dataclass in Python 3.10
    cast_type: str
    value: SootValue

    def __str__(self):
        return "((%s) %s)" % (str(self.cast_type), str(self.value))

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootCastExpr(
            type_,
            str(ir_subvalue.getCastType()),
            SootValue.from_ir(ir_subvalue.getOp()),
        )


@dataclass(unsafe_hash=True)
class SootConditionExpr(SootExpr):
    __slots__ = [
        "op",
        "value1",
        "value2",
    ]  # TODO: replace with dataclass in Python 3.10
    op: str
    value1: SootValue
    value2: SootValue

    def __str__(self):
        return "%s %s %s" % (
            str(self.value1),
            SootExpr.OP_TO_STR[self.op],
            str(self.value2),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        op = expr_name[1:].replace("Expr", "").lower()
        return SootConditionExpr(
            type_,
            op,
            SootValue.from_ir(ir_subvalue.getOp1()),
            SootValue.from_ir(ir_subvalue.getOp2()),
        )


@dataclass(unsafe_hash=True)
class SootLengthExpr(SootExpr):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: SootValue

    def __str__(self):
        return "len(%s)" % str(self.value)

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootLengthExpr(type_, SootValue.from_ir(ir_subvalue.getOp()))


@dataclass(unsafe_hash=True)
class SootNewArrayExpr(SootExpr):
    __slots__ = ["base_type", "size"]  # TODO: replace with dataclass in Python 3.10
    base_type: str
    size: SootValue

    def __repr__(self):
        return "SootNewArrayExpr(%s[%s])" % (self.base_type, self.size)

    def __str__(self):
        return "new %s[%s]" % (self.base_type, str(self.size))

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootNewArrayExpr(
            type_,
            str(ir_subvalue.getBaseType()),
            SootValue.from_ir(ir_subvalue.getSize()),
        )


@dataclass(unsafe_hash=True)
class SootNewMultiArrayExpr(SootExpr):
    __slots__ = ["base_type", "sizes"]  # TODO: replace with dataclass in Python 3.10
    base_type: str
    sizes: Any

    def __str__(self):
        return "new %s%s" % (
            self.base_type.replace("[", "").replace("]", ""),
            "".join((["[%s]" % str(s) for s in self.sizes])),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootNewMultiArrayExpr(
            type_,
            str(ir_subvalue.getBaseType()),
            (SootValue.from_ir(size) for size in ir_subvalue.getSizes()),
        )


@dataclass(unsafe_hash=True)
class SootNewExpr(SootExpr):
    __slots__ = ["base_type"]  # TODO: replace with dataclass in Python 3.10
    base_type: str

    def __str__(self):
        return "new %s" % str(self.base_type)

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootNewExpr(type_, str(ir_subvalue.getBaseType()))


@dataclass(unsafe_hash=True)
class SootPhiExpr(SootExpr):
    __slots__ = ["values"]  # TODO: replace with dataclass in Python 3.10
    values: tuple[SootValue, ...]

    def __str__(self):
        return "Phi(%s)" % (
            ", ".join(["{} #{}".format(s, b_id) for s, b_id in self.values])
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootPhiExpr(
            type_, (SootValue.from_ir(v.getValue()) for v in ir_subvalue.getArgs())
        )


# every invoke type has a method signature (class + name + parameter types) and concrete arguments
# all invoke types, EXCEPT static, have a base ("this" concrete instance)
@dataclass(unsafe_hash=True)
class SootInvokeExpr(SootExpr):
    __slots__ = [
        "class_name",
        "method_name",
        "method_params",
        "args",
    ]  # TODO: replace with dataclass in Python 3.10
    class_name: str
    method_name: str
    method_params: Any
    args: Any

    def __str__(self):
        return "%s.%s(%s)]" % (
            self.class_name,
            self.method_name,
            self.list_to_arg_str(self.method_params),
        )

    @staticmethod
    def list_to_arg_str(args):
        return ", ".join([str(arg) for arg in args])


@dataclass(unsafe_hash=True)
class SootVirtualInvokeExpr(SootInvokeExpr):
    __slots__ = ["base"]  # TODO: replace with dataclass in Python 3.10
    base: Any

    def __str__(self):
        return "%s.%s(%s) [virtualinvoke %s" % (
            str(self.base),
            self.method_name,
            self.list_to_arg_str(self.args),
            str(super(SootVirtualInvokeExpr, self).__str__()),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple([SootValue.from_ir(arg) for arg in ir_expr.getArgs()])
        called_method = ir_expr.getMethod()
        params = tuple([str(param) for param in called_method.getParameterTypes()])

        return SootVirtualInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            base=SootValue.from_ir(ir_expr.getBase()),
            args=args,
        )


@dataclass(unsafe_hash=True)
class SootDynamicInvokeExpr(SootInvokeExpr):
    __slots__ = [
        "bootstrap_method",
        "bootstrap_args",
    ]  # TODO: replace with dataclass in Python 3.10
    bootstrap_method: Any
    bootstrap_args: Any

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        bootstrap_method = None  # ir_expr.getBootstrapMethod()
        bootstrap_args = None  # tuple([ SootValue.from_ir(arg) for arg in ir_expr.getBootstrapArgs() ])
        method = ir_expr.getMethod()
        method_params = tuple([str(param) for param in method.getParameterTypes()])
        args = tuple([SootValue.from_ir(arg) for arg in ir_expr.getArgs()])

        class_name = str(method.getDeclaringClass().getName())
        method_name = str(method.getName())

        return SootDynamicInvokeExpr(
            type=type_,
            class_name=class_name,
            method_name=method_name,
            method_params=method_params,
            args=method_args,
            bootstrap_method=bootstrap_method,
            bootstrap_args=bootstrap_args,
        )


@dataclass(unsafe_hash=True)
class SootInterfaceInvokeExpr(SootInvokeExpr):
    __slots__ = ["base"]  # TODO: replace with dataclass in Python 3.10
    base: Any

    def __str__(self):
        return "%s.%s(%s) [interfaceinvoke %s" % (
            str(self.base),
            self.method_name,
            self.list_to_arg_str(self.args),
            str(super(SootInterfaceInvokeExpr, self).__str__()),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple([SootValue.from_ir(arg) for arg in ir_expr.getArgs()])
        called_method = ir_expr.getMethod()
        params = tuple([str(param) for param in called_method.getParameterTypes()])

        return SootInterfaceInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            base=SootValue.from_ir(ir_expr.getBase()),
            args=args,
        )


@dataclass(unsafe_hash=True)
class SootSpecialInvokeExpr(SootInvokeExpr):
    __slots__ = ["base"]  # TODO: replace with dataclass in Python 3.10
    base: Any

    def __str__(self):
        return "%s.%s(%s) [specialinvoke %s" % (
            str(self.base),
            self.method_name,
            self.list_to_arg_str(self.args),
            str(super(SootSpecialInvokeExpr, self).__str__()),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple([SootValue.from_ir(arg) for arg in ir_expr.getArgs()])
        called_method = ir_expr.getMethod()
        params = tuple([str(param) for param in called_method.getParameterTypes()])

        return SootSpecialInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            base=SootValue.from_ir(ir_expr.getBase()),
            args=args,
        )


@dataclass(unsafe_hash=True)
class SootStaticInvokeExpr(SootInvokeExpr):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "%s(%s) [staticinvoke %s" % (
            self.method_name,
            self.list_to_arg_str(self.args),
            str(super(SootStaticInvokeExpr, self).__str__()),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple([SootValue.from_ir(arg) for arg in ir_expr.getArgs()])
        called_method = ir_expr.getMethod()
        params = tuple([str(param) for param in called_method.getParameterTypes()])

        return SootStaticInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            args=args,
        )


@dataclass(unsafe_hash=True)
class SootInstanceOfExpr(SootValue):
    __slots__ = ["check_type", "value"]  # TODO: replace with dataclass in Python 3.10
    check_type: str
    value: SootValue

    def __str__(self):
        return "%s instanceof %s" % (str(self.value), str(self.check_type))

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        return SootInstanceOfExpr(
            type_, str(ir_expr.getCheckType()), SootValue.from_ir(ir_expr.getOp())
        )


SootExpr.NAME_TO_CLASS = {
    "JCastExpr": SootCastExpr,
    "JLengthExpr": SootLengthExpr,
    "JNewExpr": SootNewExpr,
    "JNewArrayExpr": SootNewArrayExpr,
    "JNewMultiArrayExpr": SootNewMultiArrayExpr,
    "JInstanceOfExpr": SootInstanceOfExpr,
    "SPhiExpr": SootPhiExpr,
    "JDynamicInvokeExpr": SootDynamicInvokeExpr,
    "JInterfaceInvokeExpr": SootInterfaceInvokeExpr,
    "JSpecialInvokeExpr": SootSpecialInvokeExpr,
    "JStaticInvokeExpr": SootStaticInvokeExpr,
    "JVirtualInvokeExpr": SootVirtualInvokeExpr,
    "JEqExpr": SootConditionExpr,
    "JGeExpr": SootConditionExpr,
    "JGtExpr": SootConditionExpr,
    "JLeExpr": SootConditionExpr,
    "JLtExpr": SootConditionExpr,
    "JNeExpr": SootConditionExpr,
    "JNegExpr": SootUnopExpr,
    "JAddExpr": SootBinopExpr,
    "JAndExpr": SootBinopExpr,
    "JCmpExpr": SootBinopExpr,
    "JCmpgExpr": SootBinopExpr,
    "JCmplExpr": SootBinopExpr,
    "JDivExpr": SootBinopExpr,
    "JMulExpr": SootBinopExpr,
    "JOrExpr": SootBinopExpr,
    "JRemExpr": SootBinopExpr,
    "JShlExpr": SootBinopExpr,
    "JShrExpr": SootBinopExpr,
    "JSubExpr": SootBinopExpr,
    "JUshrExpr": SootBinopExpr,
    "JXorExpr": SootBinopExpr,
}

SootExpr.OP_TO_STR = {
    "eq": "==",
    "ge": ">=",
    "gt": ">",
    "le": "<=",
    "lt": "<",
    "ne": "!=",
    "neg": "!",
    "add": "+",
    "and": "&",
    "cmp": "cmp",
    "cmpg": "cmpg",
    "cmpl": "cmpl",
    "div": "/",
    "mul": "*",
    "or": "|",
    "rem": "%",
    "shl": "<<",
    "shr": ">>",
    "sub": "-",
    "ushr": ">>>",
    "xor": "^",
}
