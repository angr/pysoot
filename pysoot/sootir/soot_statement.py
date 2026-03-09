from __future__ import annotations

from dataclasses import dataclass

from frozendict import frozendict

from .soot_value import SootValue


@dataclass(slots=True, unsafe_hash=True)
class SootStmt:
    NAME_TO_CLASS = {}

    label: int
    offset: int

    @staticmethod
    def from_ir(ir_stmt, stmt_map=None):
        stmt_type = ir_stmt.getClass().getSimpleName()
        stmt_class = SootStmt.NAME_TO_CLASS.get(stmt_type, None)

        if stmt_class is None:
            raise NotImplementedError(
                f"Statement type {stmt_type} is not supported yet."
            )

        # TODO it seems that soot always set bytecode offset to null
        return stmt_class.from_ir(stmt_map[ir_stmt], 0, ir_stmt, stmt_map)


@dataclass(slots=True, unsafe_hash=True)
class DefinitionStmt(SootStmt):
    left_op: SootValue
    right_op: SootValue

    def __str__(self):
        return f"{str(self.left_op)} = {str(self.right_op)}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        raise NotImplementedError()


@dataclass(slots=True, unsafe_hash=True)
class AssignStmt(DefinitionStmt):
    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return AssignStmt(
            label,
            offset,
            SootValue.from_ir(ir_stmt.getLeftOp()),
            SootValue.from_ir(ir_stmt.getRightOp()),
        )


@dataclass(slots=True, unsafe_hash=True)
class IdentityStmt(DefinitionStmt):
    def __str__(self):
        return f"{str(self.left_op)} <- {str(self.right_op)}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return IdentityStmt(
            label,
            offset,
            SootValue.from_ir(ir_stmt.getLeftOp()),
            SootValue.from_ir(ir_stmt.getRightOp()),
        )


@dataclass(slots=True, unsafe_hash=True)
class BreakpointStmt(SootStmt):
    def __str__(self):
        return "SootBreakpoint"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return BreakpointStmt(label, offset)


@dataclass(slots=True, unsafe_hash=True)
class EnterMonitorStmt(SootStmt):
    obj: SootValue

    def __str__(self):
        return f"EnterMonitor({str(self.obj)})"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return EnterMonitorStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


@dataclass(slots=True, unsafe_hash=True)
class ExitMonitorStmt(SootStmt):
    obj: SootValue

    def __str__(self):
        return f"ExitMonitor({str(self.obj)})"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ExitMonitorStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


@dataclass(slots=True, unsafe_hash=True)
class GotoStmt(SootStmt):
    target: SootStmt

    def __str__(self):
        return f"goto {self.target}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return GotoStmt(label, offset, stmt_map[ir_stmt.getTarget()])


@dataclass(slots=True, unsafe_hash=True)
class IfStmt(SootStmt):
    condition: SootValue
    target: SootStmt

    def __str__(self):
        return f"if({str(self.condition)}) goto {str(self.target)}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return IfStmt(
            label,
            offset,
            SootValue.from_ir(ir_stmt.getCondition()),
            stmt_map[ir_stmt.getTarget()],
        )


@dataclass(slots=True, unsafe_hash=True)
class InvokeStmt(SootStmt):
    invoke_expr: SootValue

    def __str__(self):
        return str(self.invoke_expr)

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return InvokeStmt(label, offset, SootValue.from_ir(ir_stmt.getInvokeExpr()))


@dataclass(slots=True, unsafe_hash=True)
class ReturnStmt(SootStmt):
    value: SootValue

    def __str__(self):
        return f"return {str(self.value)}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ReturnStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


@dataclass(slots=True, unsafe_hash=True)
class ReturnVoidStmt(SootStmt):
    def __str__(self):
        return "return null"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ReturnVoidStmt(label, offset)


@dataclass(slots=True, unsafe_hash=True)
class LookupSwitchStmt(SootStmt):
    key: SootValue
    lookup_values_and_targets: frozendict[int, SootStmt]
    default_target: SootStmt

    def __str__(self):
        targets = repr(self.lookup_values_and_targets)
        default = str(self.default_target)
        return f"switch_table({self.key}) {targets} default: {default}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        lookup_values = [int(str(v)) for v in ir_stmt.getLookupValues()]
        targets = [stmt_map[t] for t in ir_stmt.getTargets()]
        lookup_values_and_targets = frozendict(zip(lookup_values, targets))

        return LookupSwitchStmt(
            label=label,
            offset=offset,
            key=SootValue.from_ir(ir_stmt.getKey()),
            lookup_values_and_targets=lookup_values_and_targets,
            default_target=stmt_map[ir_stmt.getDefaultTarget()],
        )


@dataclass(slots=True, unsafe_hash=True)
class TableSwitchStmt(SootStmt):
    key: SootValue
    low_index: int
    high_index: int
    targets: tuple[SootStmt, ...]
    lookup_values_and_targets: frozendict[int, SootStmt]
    default_target: SootStmt

    def __str__(self):
        targets = repr(self.lookup_values_and_targets)
        default = str(self.default_target)
        return f"switch_range({self.key}) {targets} default: {default}"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        targets = tuple(stmt_map[t] for t in ir_stmt.getTargets())
        dict_iter = zip(
            range(ir_stmt.getLowIndex(), ir_stmt.getHighIndex() + 1), targets
        )
        lookup_values_and_targets = dict(dict_iter)

        return TableSwitchStmt(
            label=label,
            offset=offset,
            key=SootValue.from_ir(ir_stmt.getKey()),
            low_index=int(ir_stmt.getLowIndex()),
            high_index=int(ir_stmt.getHighIndex()),
            targets=tuple(targets),
            default_target=stmt_map[ir_stmt.getDefaultTarget()],
            lookup_values_and_targets=frozendict(lookup_values_and_targets),
        )


@dataclass(slots=True, unsafe_hash=True)
class ThrowStmt(SootStmt):
    obj: SootValue

    def __str__(self):
        return f"Throw({str(self.obj)})"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ThrowStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


SootStmt.NAME_TO_CLASS = {
    "JAssignStmt": AssignStmt,
    "JBreakpointStmt": BreakpointStmt,
    "JEnterMonitorStmt": EnterMonitorStmt,
    "JExitMonitorStmt": ExitMonitorStmt,
    "JGotoStmt": GotoStmt,
    "JIdentityStmt": IdentityStmt,
    "JIfStmt": IfStmt,
    "JInvokeStmt": InvokeStmt,
    "JLookupSwitchStmt": LookupSwitchStmt,
    "JReturnStmt": ReturnStmt,
    "JReturnVoidStmt": ReturnVoidStmt,
    "JTableSwitchStmt": TableSwitchStmt,
    "JThrowStmt": ThrowStmt,
}
