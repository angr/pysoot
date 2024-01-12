from __future__ import annotations

from dataclasses import dataclass

from frozendict import frozendict

from .soot_value import SootValue


@dataclass(unsafe_hash=True)
class SootStmt:
    NAME_TO_CLASS = {}

    __slots__ = [
        "label",
        "offset",
    ]  # TODO: replace with dataclass in Python 3.10
    label: int
    offset: int

    @staticmethod
    def from_ir(ir_stmt, stmt_map=None):
        stmt_type = ir_stmt.getClass().getSimpleName()
        stmt_class = SootStmt.NAME_TO_CLASS.get(stmt_type, None)

        if stmt_class is None:
            raise NotImplementedError(
                "Statement type %s is not supported yet." % stmt_type
            )

        # TODO it seems that soot always set bytecode offset to null
        return stmt_class.from_ir(stmt_map[ir_stmt], 0, ir_stmt, stmt_map)


@dataclass(unsafe_hash=True)
class DefinitionStmt(SootStmt):
    __slots__ = ["left_op", "right_op"]  # TODO: replace with dataclass in Python 3.10
    left_op: SootValue
    right_op: SootValue

    def __str__(self):
        return "%s = %s" % (str(self.left_op), str(self.right_op))

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        raise NotImplementedError()


@dataclass(unsafe_hash=True)
class AssignStmt(DefinitionStmt):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "%s = %s" % (str(self.left_op), str(self.right_op))

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return AssignStmt(
            label,
            offset,
            SootValue.from_ir(ir_stmt.getLeftOp()),
            SootValue.from_ir(ir_stmt.getRightOp()),
        )


@dataclass(unsafe_hash=True)
class IdentityStmt(DefinitionStmt):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "%s <- %s" % (str(self.left_op), str(self.right_op))

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return IdentityStmt(
            label,
            offset,
            SootValue.from_ir(ir_stmt.getLeftOp()),
            SootValue.from_ir(ir_stmt.getRightOp()),
        )


@dataclass(unsafe_hash=True)
class BreakpointStmt(SootStmt):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "SootBreakpoint"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return BreakpointStmt(label, offset)


@dataclass(unsafe_hash=True)
class EnterMonitorStmt(SootStmt):
    __slots__ = ["obj"]  # TODO: replace with dataclass in Python 3.10
    obj: SootValue

    def __str__(self):
        return "EnterMonitor(%s)" % str(self.obj)

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return EnterMonitorStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


@dataclass(unsafe_hash=True)
class ExitMonitorStmt(SootStmt):
    __slots__ = ["obj"]  # TODO: replace with dataclass in Python 3.10
    obj: SootValue

    def __str__(self):
        return "ExitMonitor(%s)" % str(self.obj)

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ExitMonitorStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


@dataclass(unsafe_hash=True)
class GotoStmt(SootStmt):
    __slots__ = ["target"]  # TODO: replace with dataclass in Python 3.10
    target: SootStmt

    def __str__(self):
        return "goto %d" % self.target

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return GotoStmt(label, offset, stmt_map[ir_stmt.getTarget()])


@dataclass(unsafe_hash=True)
class IfStmt(SootStmt):
    __slots__ = ["condition", "target"]  # TODO: replace with dataclass in Python 3.10
    condition: SootValue
    target: SootStmt

    def __str__(self):
        return "if(%s) goto %s" % (str(self.condition), str(self.target))

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return IfStmt(
            label,
            offset,
            SootValue.from_ir(ir_stmt.getCondition()),
            stmt_map[ir_stmt.getTarget()],
        )


@dataclass(unsafe_hash=True)
class InvokeStmt(SootStmt):
    __slots__ = ["invoke_expr"]  # TODO: replace with dataclass in Python 3.10
    invoke_expr: SootValue

    def __str__(self):
        return str(self.invoke_expr)

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return InvokeStmt(label, offset, SootValue.from_ir(ir_stmt.getInvokeExpr()))


@dataclass(unsafe_hash=True)
class ReturnStmt(SootStmt):
    __slots__ = ["value"]  # TODO: replace with dataclass in Python 3.10
    value: SootValue

    def __str__(self):
        return "return %s" % str(self.value)

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ReturnStmt(label, offset, SootValue.from_ir(ir_stmt.getOp()))


@dataclass(unsafe_hash=True)
class ReturnVoidStmt(SootStmt):
    __slots__ = []  # TODO: replace with dataclass in Python 3.10

    def __str__(self):
        return "return null"

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        return ReturnVoidStmt(label, offset)


@dataclass(unsafe_hash=True)
class LookupSwitchStmt(SootStmt):
    __slots__ = [
        "key",
        "lookup_values_and_targets",
        "default_target",
    ]  # TODO: replace with dataclass in Python 3.10
    key: SootValue
    lookup_values_and_targets: frozendict[int, SootStmt]
    default_target: SootStmt

    def __str__(self):
        return "switch_table(%s) %s default: %s" % (
            str(self.key),
            repr(self.lookup_values_and_targets),
            str(self.default_target),
        )

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        lookup_values = [int(str(v)) for v in ir_stmt.getLookupValues()]
        targets = [stmt_map[t] for t in ir_stmt.getTargets()]
        lookup_values_and_targets = frozendict({k: v for k, v in zip(lookup_values, targets)})

        return LookupSwitchStmt(
            label=label,
            offset=offset,
            key=SootValue.from_ir(ir_stmt.getKey()),
            lookup_values_and_targets=lookup_values_and_targets,
            default_target=stmt_map[ir_stmt.getDefaultTarget()],
        )


@dataclass(unsafe_hash=True)
class TableSwitchStmt(SootStmt):
    __slots__ = [  # TODO: replace with dataclass in Python 3.10
        "key",
        "low_index",
        "high_index",
        "targets",
        "lookup_values_and_targets",
        "default_target",
    ]
    key: SootValue
    low_index: int
    high_index: int
    targets: tuple[SootStmt, ...]
    lookup_values_and_targets: frozendict[int, SootStmt]
    default_target: SootStmt

    def __str__(self):
        return "switch_range(%s) %s default: %s" % (
            str(self.key),
            repr(self.lookup_values_and_targets),
            str(self.default_target),
        )

    @staticmethod
    def from_ir(label, offset, ir_stmt, stmt_map=None):
        targets = tuple(stmt_map[t] for t in ir_stmt.getTargets())
        dict_iter = zip(
            range(ir_stmt.getLowIndex(), ir_stmt.getHighIndex() + 1), targets
        )
        lookup_values_and_targets = {k: v for k, v in dict_iter}

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


@dataclass(unsafe_hash=True)
class ThrowStmt(SootStmt):
    __slots__ = ["obj"]  # TODO: replace with dataclass in Python 3.10
    obj: SootValue

    def __str__(self):
        return "Throw(%s)" % str(self.obj)

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
