from __future__ import annotations

from dataclasses import dataclass

from .soot_value import SootValue


@dataclass(slots=True, unsafe_hash=True)
class SootExpr(SootValue):
    NAME_TO_CLASS = {}

    @staticmethod
    def from_ir(ir_expr):
        subtype = ir_expr.getClass().getSimpleName()
        cls = SootExpr.NAME_TO_CLASS.get(subtype, None)
        if cls is None:
            raise NotImplementedError(f"Unsupported Soot expression type {subtype}.")

        return cls.from_ir(str(ir_expr.getType()), subtype, ir_expr)


@dataclass(slots=True, unsafe_hash=True)
class SootBinopExpr(SootExpr):
    op: str
    value1: SootValue
    value2: SootValue

    def __str__(self):
        return f"{str(self.value1)} {SootExpr.OP_TO_STR[self.op]} {str(self.value2)}"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        op = expr_name[1:].replace("Expr", "").lower()

        return SootBinopExpr(
            type_,
            op,
            SootValue.from_ir(ir_subvalue.getOp1()),
            SootValue.from_ir(ir_subvalue.getOp2()),
        )


@dataclass(slots=True, unsafe_hash=True)
class SootUnopExpr(SootExpr):
    op: str
    value: SootValue

    def __str__(self):
        return f"{SootExpr.OP_TO_STR[self.op]} {str(self.value)}"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        op = expr_name[1:].replace("Expr", "").lower()
        return SootUnopExpr(type_, op, SootValue.from_ir(ir_subvalue.getOp()))


@dataclass(slots=True, unsafe_hash=True)
class SootCastExpr(SootExpr):
    cast_type: str
    value: SootValue

    def __str__(self):
        return f"(({str(self.cast_type)}) {str(self.value)})"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootCastExpr(
            type_,
            str(ir_subvalue.getCastType()),
            SootValue.from_ir(ir_subvalue.getOp()),
        )


@dataclass(slots=True, unsafe_hash=True)
class SootConditionExpr(SootExpr):
    op: str
    value1: SootValue
    value2: SootValue

    def __str__(self):
        return f"{str(self.value1)} {SootExpr.OP_TO_STR[self.op]} {str(self.value2)}"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        op = expr_name[1:].replace("Expr", "").lower()
        return SootConditionExpr(
            type_,
            op,
            SootValue.from_ir(ir_subvalue.getOp1()),
            SootValue.from_ir(ir_subvalue.getOp2()),
        )


@dataclass(slots=True, unsafe_hash=True)
class SootLengthExpr(SootExpr):
    value: SootValue

    def __str__(self):
        return f"len({str(self.value)})"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootLengthExpr(type_, SootValue.from_ir(ir_subvalue.getOp()))


@dataclass(slots=True, unsafe_hash=True)
class SootNewArrayExpr(SootExpr):
    base_type: str
    size: SootValue

    def __repr__(self):
        return f"SootNewArrayExpr({self.base_type}[{self.size}])"

    def __str__(self):
        return f"new {self.base_type}[{str(self.size)}]"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootNewArrayExpr(
            type_,
            str(ir_subvalue.getBaseType()),
            SootValue.from_ir(ir_subvalue.getSize()),
        )


@dataclass(slots=True, unsafe_hash=True)
class SootNewMultiArrayExpr(SootExpr):
    base_type: str
    sizes: tuple[SootValue, ...]

    def __str__(self):
        return "new {}{}".format(
            self.base_type.replace("[", "").replace("]", ""),
            "".join([f"[{str(s)}]" for s in self.sizes]),
        )

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootNewMultiArrayExpr(
            type_,
            str(ir_subvalue.getBaseType()),
            tuple(SootValue.from_ir(size) for size in ir_subvalue.getSizes()),
        )


@dataclass(slots=True, unsafe_hash=True)
class SootNewExpr(SootExpr):
    base_type: str

    def __str__(self):
        return f"new {str(self.base_type)}"

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootNewExpr(type_, str(ir_subvalue.getBaseType()))


@dataclass(slots=True, unsafe_hash=True)
class SootPhiExpr(SootExpr):
    values: tuple[SootValue, ...]

    def __str__(self):
        return "Phi({})".format(", ".join([f"{s} #{b_id}" for s, b_id in self.values]))

    @staticmethod
    def from_ir(type_, expr_name, ir_subvalue):
        return SootPhiExpr(
            type_, tuple(SootValue.from_ir(v.getValue()) for v in ir_subvalue.getArgs())
        )


# every invoke type has a method signature
# (class + name + parameter types) and concrete arguments
# all invoke types, EXCEPT static, have a base
# ("this" concrete instance)
@dataclass(slots=True, unsafe_hash=True)
class SootInvokeExpr(SootExpr):
    class_name: str
    method_name: str
    method_params: tuple[str, ...]
    args: tuple[SootValue, ...]

    def __str__(self):
        params = self.list_to_arg_str(self.method_params)
        return f"{self.class_name}.{self.method_name}({params})]"

    @staticmethod
    def list_to_arg_str(args):
        return ", ".join(str(arg) for arg in args)


@dataclass(slots=True, unsafe_hash=True)
class SootVirtualInvokeExpr(SootInvokeExpr):
    base: SootValue

    def __str__(self):
        base = str(self.base)
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootVirtualInvokeExpr, self).__str__())
        return f"{base}.{self.method_name}({args}) [virtualinvoke {parent}"

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple(SootValue.from_ir(arg) for arg in ir_expr.getArgs())
        called_method = ir_expr.getMethod()
        params = tuple(str(param) for param in called_method.getParameterTypes())

        return SootVirtualInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            base=SootValue.from_ir(ir_expr.getBase()),
            args=args,
        )


@dataclass(slots=True, unsafe_hash=True)
class SootDynamicInvokeExpr(SootInvokeExpr):
    bootstrap_method: None
    bootstrap_args: None

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        bootstrap_method = None  # ir_expr.getBootstrapMethod()
        # tuple([SootValue.from_ir(arg)
        #        for arg in ir_expr.getBootstrapArgs()])
        bootstrap_args = None
        method = ir_expr.getMethod()
        method_params = tuple(str(param) for param in method.getParameterTypes())
        args = tuple(SootValue.from_ir(arg) for arg in ir_expr.getArgs())

        class_name = str(method.getDeclaringClass().getName())
        method_name = str(method.getName())

        return SootDynamicInvokeExpr(
            type=type_,
            class_name=class_name,
            method_name=method_name,
            method_params=method_params,
            args=args,
            bootstrap_method=bootstrap_method,
            bootstrap_args=bootstrap_args,
        )


@dataclass(slots=True, unsafe_hash=True)
class SootInterfaceInvokeExpr(SootInvokeExpr):
    base: SootValue

    def __str__(self):
        base = str(self.base)
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootInterfaceInvokeExpr, self).__str__())
        return f"{base}.{self.method_name}({args}) [interfaceinvoke {parent}"

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple(SootValue.from_ir(arg) for arg in ir_expr.getArgs())
        called_method = ir_expr.getMethod()
        params = tuple(str(param) for param in called_method.getParameterTypes())

        return SootInterfaceInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            base=SootValue.from_ir(ir_expr.getBase()),
            args=args,
        )


@dataclass(slots=True, unsafe_hash=True)
class SootSpecialInvokeExpr(SootInvokeExpr):
    base: SootValue

    def __str__(self):
        base = str(self.base)
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootSpecialInvokeExpr, self).__str__())
        return f"{base}.{self.method_name}({args}) [specialinvoke {parent}"

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple(SootValue.from_ir(arg) for arg in ir_expr.getArgs())
        called_method = ir_expr.getMethod()
        params = tuple(str(param) for param in called_method.getParameterTypes())

        return SootSpecialInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            base=SootValue.from_ir(ir_expr.getBase()),
            args=args,
        )


@dataclass(slots=True, unsafe_hash=True)
class SootStaticInvokeExpr(SootInvokeExpr):
    def __str__(self):
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootStaticInvokeExpr, self).__str__())
        return f"{self.method_name}({args}) [staticinvoke {parent}"

    @staticmethod
    def from_ir(type_, expr_name, ir_expr):
        args = tuple(SootValue.from_ir(arg) for arg in ir_expr.getArgs())
        called_method = ir_expr.getMethod()
        params = tuple(str(param) for param in called_method.getParameterTypes())

        return SootStaticInvokeExpr(
            type=type_,
            class_name=str(called_method.getDeclaringClass().getName()),
            method_name=str(called_method.getName()),
            method_params=params,
            args=args,
        )


@dataclass(slots=True, unsafe_hash=True)
class SootInstanceOfExpr(SootValue):
    check_type: str
    value: SootValue

    def __str__(self):
        return f"{str(self.value)} instanceof {str(self.check_type)}"

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
