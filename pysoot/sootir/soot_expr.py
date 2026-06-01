from __future__ import annotations

from dataclasses import dataclass

from .soot_value import SootValue


OP_TO_STR = {
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


@dataclass(slots=True, frozen=True)
class SootExpr(SootValue):
    pass


@dataclass(slots=True, frozen=True)
class SootBinopExpr(SootExpr):
    op: str
    value1: SootValue
    value2: SootValue

    def __str__(self):
        return f"{str(self.value1)} {OP_TO_STR[self.op]} {str(self.value2)}"


@dataclass(slots=True, frozen=True)
class SootUnopExpr(SootExpr):
    op: str
    value: SootValue

    def __str__(self):
        return f"{OP_TO_STR[self.op]} {str(self.value)}"


@dataclass(slots=True, frozen=True)
class SootCastExpr(SootExpr):
    cast_type: str
    value: SootValue

    def __str__(self):
        return f"(({str(self.cast_type)}) {str(self.value)})"


@dataclass(slots=True, frozen=True)
class SootConditionExpr(SootExpr):
    op: str
    value1: SootValue
    value2: SootValue

    def __str__(self):
        return f"{str(self.value1)} {OP_TO_STR[self.op]} {str(self.value2)}"


@dataclass(slots=True, frozen=True)
class SootLengthExpr(SootExpr):
    value: SootValue

    def __str__(self):
        return f"len({str(self.value)})"


@dataclass(slots=True, frozen=True)
class SootNewArrayExpr(SootExpr):
    base_type: str
    size: SootValue

    def __repr__(self):
        return f"SootNewArrayExpr({self.base_type}[{self.size}])"

    def __str__(self):
        return f"new {self.base_type}[{str(self.size)}]"


@dataclass(slots=True, frozen=True)
class SootNewMultiArrayExpr(SootExpr):
    base_type: str
    sizes: tuple[SootValue, ...]

    def __str__(self):
        return "new {}{}".format(
            self.base_type.replace("[", "").replace("]", ""),
            "".join([f"[{str(s)}]" for s in self.sizes]),
        )


@dataclass(slots=True, frozen=True)
class SootNewExpr(SootExpr):
    base_type: str

    def __str__(self):
        return f"new {str(self.base_type)}"


@dataclass(slots=True, frozen=True)
class SootPhiExpr(SootExpr):
    values: tuple[tuple[SootValue, int], ...]

    def __str__(self):
        return "Phi({})".format(", ".join([f"{s} #{b_id}" for s, b_id in self.values]))


# every invoke type has a method signature
# (class + name + parameter types) and concrete arguments
# all invoke types, EXCEPT static, have a base
# ("this" concrete instance)
@dataclass(slots=True, frozen=True)
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


@dataclass(slots=True, frozen=True)
class SootVirtualInvokeExpr(SootInvokeExpr):
    base: SootValue

    def __str__(self):
        base = str(self.base)
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootVirtualInvokeExpr, self).__str__())
        return f"{base}.{self.method_name}({args}) [virtualinvoke {parent}"


@dataclass(slots=True, frozen=True)
class SootDynamicInvokeExpr(SootInvokeExpr):
    bootstrap_method: None
    bootstrap_args: None


@dataclass(slots=True, frozen=True)
class SootInterfaceInvokeExpr(SootInvokeExpr):
    base: SootValue

    def __str__(self):
        base = str(self.base)
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootInterfaceInvokeExpr, self).__str__())
        return f"{base}.{self.method_name}({args}) [interfaceinvoke {parent}"


@dataclass(slots=True, frozen=True)
class SootSpecialInvokeExpr(SootInvokeExpr):
    base: SootValue

    def __str__(self):
        base = str(self.base)
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootSpecialInvokeExpr, self).__str__())
        return f"{base}.{self.method_name}({args}) [specialinvoke {parent}"


@dataclass(slots=True, frozen=True)
class SootStaticInvokeExpr(SootInvokeExpr):
    def __str__(self):
        args = self.list_to_arg_str(self.args)
        parent = str(super(SootStaticInvokeExpr, self).__str__())
        return f"{self.method_name}({args}) [staticinvoke {parent}"


@dataclass(slots=True, frozen=True)
class SootInstanceOfExpr(SootValue):
    check_type: str
    value: SootValue

    def __str__(self):
        return f"{str(self.value)} instanceof {str(self.check_type)}"
