from __future__ import annotations

from dataclasses import dataclass

from frozendict import frozendict

from .soot_value import SootValue


@dataclass(slots=True, frozen=True)
class SootStmt:
    label: int
    offset: int


@dataclass(slots=True, frozen=True)
class DefinitionStmt(SootStmt):
    left_op: SootValue
    right_op: SootValue

    def __str__(self):
        return f"{str(self.left_op)} = {str(self.right_op)}"


@dataclass(slots=True, frozen=True)
class AssignStmt(DefinitionStmt):
    pass


@dataclass(slots=True, frozen=True)
class IdentityStmt(DefinitionStmt):
    def __str__(self):
        return f"{str(self.left_op)} <- {str(self.right_op)}"


@dataclass(slots=True, frozen=True)
class BreakpointStmt(SootStmt):
    def __str__(self):
        return "SootBreakpoint"


@dataclass(slots=True, frozen=True)
class EnterMonitorStmt(SootStmt):
    obj: SootValue

    def __str__(self):
        return f"EnterMonitor({str(self.obj)})"


@dataclass(slots=True, frozen=True)
class ExitMonitorStmt(SootStmt):
    obj: SootValue

    def __str__(self):
        return f"ExitMonitor({str(self.obj)})"


@dataclass(slots=True, frozen=True)
class GotoStmt(SootStmt):
    target: int

    def __str__(self):
        return f"goto {self.target}"


@dataclass(slots=True, frozen=True)
class IfStmt(SootStmt):
    condition: SootValue
    target: int

    def __str__(self):
        return f"if({str(self.condition)}) goto {str(self.target)}"


@dataclass(slots=True, frozen=True)
class InvokeStmt(SootStmt):
    invoke_expr: SootValue

    def __str__(self):
        return str(self.invoke_expr)


@dataclass(slots=True, frozen=True)
class ReturnStmt(SootStmt):
    value: SootValue

    def __str__(self):
        return f"return {str(self.value)}"


@dataclass(slots=True, frozen=True)
class ReturnVoidStmt(SootStmt):
    def __str__(self):
        return "return null"


@dataclass(slots=True, frozen=True)
class LookupSwitchStmt(SootStmt):
    key: SootValue
    lookup_values_and_targets: frozendict[int, int]
    default_target: int

    def __str__(self):
        targets = repr(self.lookup_values_and_targets)
        default = str(self.default_target)
        return f"switch_table({self.key}) {targets} default: {default}"


@dataclass(slots=True, frozen=True)
class TableSwitchStmt(SootStmt):
    key: SootValue
    low_index: int
    high_index: int
    targets: tuple[int, ...]
    lookup_values_and_targets: frozendict[int, int]
    default_target: int

    def __str__(self):
        targets = repr(self.lookup_values_and_targets)
        default = str(self.default_target)
        return f"switch_range({self.key}) {targets} default: {default}"


@dataclass(slots=True, frozen=True)
class ThrowStmt(SootStmt):
    obj: SootValue

    def __str__(self):
        return f"Throw({str(self.obj)})"
