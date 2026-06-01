from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import jpype
from jpype.types import JClass
from frozendict import frozendict

from pysoot.sootir import convert_soot_attributes
from pysoot.sootir.soot_block import SootBlock
from pysoot.sootir.soot_class import SootClass
from pysoot.sootir.soot_expr import (
    SootBinopExpr,
    SootCastExpr,
    SootConditionExpr,
    SootDynamicInvokeExpr,
    SootInstanceOfExpr,
    SootInterfaceInvokeExpr,
    SootLengthExpr,
    SootNewArrayExpr,
    SootNewExpr,
    SootNewMultiArrayExpr,
    SootPhiExpr,
    SootSpecialInvokeExpr,
    SootStaticInvokeExpr,
    SootUnopExpr,
    SootVirtualInvokeExpr,
)
from pysoot.sootir.soot_method import SootMethod
from pysoot.sootir.soot_statement import (
    AssignStmt,
    BreakpointStmt,
    EnterMonitorStmt,
    ExitMonitorStmt,
    GotoStmt,
    IdentityStmt,
    IfStmt,
    InvokeStmt,
    LookupSwitchStmt,
    ReturnStmt,
    ReturnVoidStmt,
    SootStmt,
    TableSwitchStmt,
    ThrowStmt,
)
from pysoot.sootir.soot_value import (
    SootArrayRef,
    SootCaughtExceptionRef,
    SootClassConstant,
    SootDoubleConstant,
    SootFloatConstant,
    SootInstanceFieldRef,
    SootIntConstant,
    SootLocal,
    SootLongConstant,
    SootNullConstant,
    SootParamRef,
    SootStaticFieldRef,
    SootStringConstant,
    SootThisRef,
    SootValue,
)


def _start_jvm():
    if jpype.isJVMStarted():
        return
    jpype.addClassPath(os.path.join(os.path.dirname(__file__), "soot-trunk.jar"))
    jpype.startJVM("-Xmx2G")
    if os.name != "nt":
        os.register_at_fork(before=jpype.shutdownJVM)


def run_soot(
    input_file: str,
    input_format: str,
    android_sdk: str | None,
    soot_classpath: str | None,
    ir_format: str,
) -> tuple[dict[str, SootClass], dict[str, list[str]]]:
    """Run Soot on the given input and return (classes, hierarchy).

    classes: dict mapping class name to SootClass (application classes only)
    hierarchy: dict mapping class name to list of subclass names
    """
    _start_jvm()

    Collections = JClass("java.util.Collections")
    G = JClass("soot.G")
    Hierarchy = JClass("soot.Hierarchy")
    Options = JClass("soot.options.Options")
    PackManager = JClass("soot.PackManager")
    Scene = JClass("soot.Scene")

    G.reset()

    Options.v().set_process_dir(Collections.singletonList(input_file))

    if input_format == "apk":
        Options.v().set_android_jars(android_sdk)
        Options.v().set_process_multiple_dex(True)
        Options.v().set_src_prec(Options.src_prec_apk)
    elif input_format == "jar":
        Options.v().set_soot_classpath(soot_classpath)
    else:
        raise Exception("invalid input type")

    if ir_format == "jimple":
        Options.v().set_output_format(Options.output_format_jimple)
    elif ir_format == "shimple":
        Options.v().set_output_format(Options.output_format_shimple)
    else:
        raise Exception("invalid ir format")

    Options.v().set_allow_phantom_refs(True)

    # this options may or may not work
    Options.v().setPhaseOption("cg", "all-reachable:true")
    Options.v().setPhaseOption("jb.dae", "enabled:false")
    Options.v().setPhaseOption("jb.uce", "enabled:false")
    Options.v().setPhaseOption("jj.dae", "enabled:false")
    Options.v().setPhaseOption("jj.uce", "enabled:false")

    # this avoids an exception in some apks
    Options.v().set_wrong_staticness(Options.wrong_staticness_ignore)

    Scene.v().loadNecessaryClasses()
    PackManager.v().runPacks()

    raw_classes = Scene.v().getClasses()
    class_name_map = {c.getName(): c for c in raw_classes}

    # Convert application classes to Python IR
    classes = {}
    for raw_class in raw_classes:
        if raw_class.isApplicationClass():
            soot_class = _convert_class(raw_class)
            classes[soot_class.name] = soot_class

    # Pre-compute subclass relationships
    hierarchy_obj = Hierarchy()
    hierarchy = {}
    for name, raw_class in class_name_map.items():
        try:
            hierarchy[name] = [
                c.getName() for c in hierarchy_obj.getSubclassesOf(raw_class)
            ]
        except Exception:
            # Some classes (e.g. interfaces) may not support getSubclassesOf
            pass

    return classes, hierarchy


# ========== Soot IR -> pysoot dataclass conversion ==========
# JPype-returned Java objects have no type stubs, so the `ir_*` parameters
# and the keys of the per-method maps below are typed as Any.


@dataclass(slots=True, frozen=True)
class _Ctx:
    """Per-method conversion context, threaded through value/stmt conversion.

    stmt_map maps each Soot Unit (statement) to its sequential index in the
    method body; used for statement labels and jump targets.
    stmt_to_block_idx maps each Unit to the index of the block that contains
    it; used by SootPhiExpr to record which block each value came from.
    """

    stmt_map: dict[Any, int]
    stmt_to_block_idx: dict[Any, int]


def _convert_class(ir_class: Any) -> SootClass:
    class_name = str(ir_class.getName())

    methods = tuple(
        _convert_method(class_name, ir_method) for ir_method in ir_class.getMethods()
    )

    attrs = convert_soot_attributes(ir_class.getModifiers())
    for extra in ("LibraryClass", "JavaLibraryClass", "Phantom"):
        if getattr(ir_class, "is" + extra)():
            attrs.append(extra)

    fields = {}
    for field in ir_class.getFields():
        fields[str(field.getName())] = (
            tuple(convert_soot_attributes(field.getModifiers())),
            str(field.getType()),
        )

    interfaces = tuple(str(i.getName()) for i in ir_class.getInterfaces())
    if class_name == "java.lang.Object":
        super_class = ""
    else:
        super_class = str(ir_class.getSuperclass().getName())

    return SootClass(
        name=class_name,
        super_class=super_class,
        interfaces=interfaces,
        attrs=tuple(attrs),
        methods=methods,
        fields=frozendict(fields),
    )


def _convert_method(class_name: str, ir_method: Any) -> SootMethod:
    blocks: tuple[SootBlock, ...] = ()
    basic_cfg: dict[SootBlock, tuple[SootBlock, ...]] = {}
    exceptional_preds: dict[SootBlock, tuple[SootBlock, ...]] = {}

    if ir_method.hasActiveBody():
        ExceptionalBlockGraph = JClass("soot.toolkits.graph.ExceptionalBlockGraph")
        body = ir_method.getActiveBody()
        cfg = ExceptionalBlockGraph(body)
        units = body.getUnits()

        # Soot Units and Blocks are hashed by identity (Python's default
        # for objects that don't override __hash__); we rely on each Java
        # object being a single instance throughout this method's conversion.
        stmt_map: dict[Any, int] = {u: i for i, u in enumerate(units)}
        idx_map: dict[Any, int] = {b: i for i, b in enumerate(cfg)}

        stmt_to_block_idx: dict[Any, int] = {}
        for ir_block in cfg:
            for ir_stmt in ir_block:
                stmt_to_block_idx[ir_stmt] = idx_map[ir_block]

        ctx = _Ctx(stmt_map=stmt_map, stmt_to_block_idx=stmt_to_block_idx)

        # Convert blocks. Phi values are populated in this single pass
        # because _convert_value uses ctx.stmt_to_block_idx directly.
        block_by_idx: dict[int, SootBlock] = {}
        blocks_list: list[SootBlock] = []
        for ir_block in cfg:
            idx = idx_map[ir_block]
            block = _convert_block(ir_block, idx, ctx)
            blocks_list.append(block)
            block_by_idx[idx] = block
        blocks = tuple(blocks_list)

        for ir_block in cfg:
            block = block_by_idx[idx_map[ir_block]]
            succs = tuple(block_by_idx[idx_map[s]] for s in ir_block.getSuccs())
            if succs:
                basic_cfg[block] = succs

            preds = tuple(
                block_by_idx[idx_map[p]] for p in cfg.getExceptionalPredsOf(ir_block)
            )
            if preds:
                exceptional_preds[block] = preds

    return SootMethod(
        class_name=class_name,
        name=str(ir_method.getName()),
        ret=str(ir_method.getReturnType()),
        attrs=tuple(convert_soot_attributes(ir_method.getModifiers())),
        exceptions=tuple(str(e.getName()) for e in ir_method.getExceptions()),
        params=tuple(str(p) for p in ir_method.getParameterTypes()),
        blocks=blocks,
        basic_cfg=frozendict(basic_cfg),
        exceptional_preds=frozendict(exceptional_preds),
    )


def _convert_block(ir_block: Any, idx: int, ctx: _Ctx) -> SootBlock:
    label = ctx.stmt_map[ir_block.getHead()]
    stmts = tuple(_convert_stmt(s, ctx) for s in ir_block)
    return SootBlock(label=label, statements=stmts, idx=idx)


def _convert_stmt(ir_stmt: Any, ctx: _Ctx) -> SootStmt:
    stmt_type = str(ir_stmt.getClass().getSimpleName())
    label = ctx.stmt_map[ir_stmt]
    # TODO Soot appears to always set the bytecode offset to null
    offset = 0

    match stmt_type:
        case "JAssignStmt":
            return AssignStmt(
                label,
                offset,
                _convert_value(ir_stmt.getLeftOp(), ctx),
                _convert_value(ir_stmt.getRightOp(), ctx),
            )
        case "JIdentityStmt":
            return IdentityStmt(
                label,
                offset,
                _convert_value(ir_stmt.getLeftOp(), ctx),
                _convert_value(ir_stmt.getRightOp(), ctx),
            )
        case "JBreakpointStmt":
            return BreakpointStmt(label, offset)
        case "JEnterMonitorStmt":
            return EnterMonitorStmt(label, offset, _convert_value(ir_stmt.getOp(), ctx))
        case "JExitMonitorStmt":
            return ExitMonitorStmt(label, offset, _convert_value(ir_stmt.getOp(), ctx))
        case "JGotoStmt":
            return GotoStmt(label, offset, ctx.stmt_map[ir_stmt.getTarget()])
        case "JIfStmt":
            return IfStmt(
                label,
                offset,
                _convert_value(ir_stmt.getCondition(), ctx),
                ctx.stmt_map[ir_stmt.getTarget()],
            )
        case "JInvokeStmt":
            return InvokeStmt(
                label, offset, _convert_value(ir_stmt.getInvokeExpr(), ctx)
            )
        case "JReturnStmt":
            return ReturnStmt(label, offset, _convert_value(ir_stmt.getOp(), ctx))
        case "JReturnVoidStmt":
            return ReturnVoidStmt(label, offset)
        case "JLookupSwitchStmt":
            lookup_values = (int(str(v)) for v in ir_stmt.getLookupValues())
            targets = (ctx.stmt_map[t] for t in ir_stmt.getTargets())
            return LookupSwitchStmt(
                label=label,
                offset=offset,
                key=_convert_value(ir_stmt.getKey(), ctx),
                lookup_values_and_targets=frozendict(zip(lookup_values, targets)),
                default_target=ctx.stmt_map[ir_stmt.getDefaultTarget()],
            )
        case "JTableSwitchStmt":
            low, high = int(ir_stmt.getLowIndex()), int(ir_stmt.getHighIndex())
            table_targets = tuple(ctx.stmt_map[t] for t in ir_stmt.getTargets())
            return TableSwitchStmt(
                label=label,
                offset=offset,
                key=_convert_value(ir_stmt.getKey(), ctx),
                low_index=low,
                high_index=high,
                targets=table_targets,
                lookup_values_and_targets=frozendict(
                    zip(range(low, high + 1), table_targets)
                ),
                default_target=ctx.stmt_map[ir_stmt.getDefaultTarget()],
            )
        case "JThrowStmt":
            return ThrowStmt(label, offset, _convert_value(ir_stmt.getOp(), ctx))
        case _:
            raise NotImplementedError(
                f"Statement type {stmt_type} is not supported yet."
            )


def _convert_value(ir_value: Any, ctx: _Ctx) -> SootValue:
    subtype = str(ir_value.getClass().getSimpleName())
    subtype = subtype.replace("Jimple", "").replace("Shimple", "")

    if subtype.endswith("Expr"):
        return _convert_expr(subtype, ir_value, ctx)

    type_str = str(ir_value.getType())

    match subtype:
        case "Local":
            return SootLocal(type_str, str(ir_value.getName()))
        case "JArrayRef":
            return SootArrayRef(
                type_str,
                _convert_value(ir_value.getBase(), ctx),
                _convert_value(ir_value.getIndex(), ctx),
            )
        case "JCaughtExceptionRef":
            return SootCaughtExceptionRef(type_str)
        case "ParameterRef":
            return SootParamRef(type_str, int(ir_value.getIndex()))
        case "ThisRef":
            return SootThisRef(type_str)
        case "StaticFieldRef":
            raw_field = ir_value.getField()
            return SootStaticFieldRef(type_str, _field_ref(raw_field))
        case "JInstanceFieldRef":
            raw_field = ir_value.getField()
            return SootInstanceFieldRef(
                type_str,
                _convert_value(ir_value.getBase(), ctx),
                _field_ref(raw_field),
            )
        case "ClassConstant":
            return SootClassConstant(type_str, str(ir_value.getValue()))
        case "DoubleConstant":
            return SootDoubleConstant(type_str, float(ir_value.value))
        case "FloatConstant":
            return SootFloatConstant(type_str, float(ir_value.value))
        case "IntConstant":
            return SootIntConstant(type_str, int(ir_value.value))
        case "LongConstant":
            return SootLongConstant(type_str, int(ir_value.value))
        case "NullConstant":
            return SootNullConstant(type_str)
        case "StringConstant":
            return SootStringConstant(type_str, str(ir_value.value))
        case _:
            raise NotImplementedError(f"Unsupported SootValue type {subtype}.")


def _convert_expr(expr_name: str, ir_expr: Any, ctx: _Ctx) -> SootValue:
    type_str = str(ir_expr.getType())

    match expr_name:
        case "JCastExpr":
            return SootCastExpr(
                type_str,
                str(ir_expr.getCastType()),
                _convert_value(ir_expr.getOp(), ctx),
            )
        case "JLengthExpr":
            return SootLengthExpr(type_str, _convert_value(ir_expr.getOp(), ctx))
        case "JNewExpr":
            return SootNewExpr(type_str, str(ir_expr.getBaseType()))
        case "JNewArrayExpr":
            return SootNewArrayExpr(
                type_str,
                str(ir_expr.getBaseType()),
                _convert_value(ir_expr.getSize(), ctx),
            )
        case "JNewMultiArrayExpr":
            return SootNewMultiArrayExpr(
                type_str,
                str(ir_expr.getBaseType()),
                tuple(_convert_value(s, ctx) for s in ir_expr.getSizes()),
            )
        case "JInstanceOfExpr":
            return SootInstanceOfExpr(
                type_str,
                str(ir_expr.getCheckType()),
                _convert_value(ir_expr.getOp(), ctx),
            )
        case "SPhiExpr":
            # Single-pass construction: we resolve the (value, block_idx) tuples
            # here using the method-level context, so SootPhiExpr can be created
            # once with its final values — no post-init mutation required.
            values = tuple(
                (
                    _convert_value(arg.getValue(), ctx),
                    ctx.stmt_to_block_idx[arg.getUnit()],
                )
                for arg in ir_expr.getArgs()
            )
            return SootPhiExpr(type_str, values)
        case "JStaticInvokeExpr":
            return SootStaticInvokeExpr(
                type=type_str, **_invoke_method_info(ir_expr, ctx)
            )
        case "JDynamicInvokeExpr":
            return SootDynamicInvokeExpr(
                type=type_str,
                **_invoke_method_info(ir_expr, ctx),
                bootstrap_method=None,
                bootstrap_args=None,
            )
        case "JVirtualInvokeExpr":
            return SootVirtualInvokeExpr(
                type=type_str,
                **_invoke_method_info(ir_expr, ctx),
                base=_convert_value(ir_expr.getBase(), ctx),
            )
        case "JInterfaceInvokeExpr":
            return SootInterfaceInvokeExpr(
                type=type_str,
                **_invoke_method_info(ir_expr, ctx),
                base=_convert_value(ir_expr.getBase(), ctx),
            )
        case "JSpecialInvokeExpr":
            return SootSpecialInvokeExpr(
                type=type_str,
                **_invoke_method_info(ir_expr, ctx),
                base=_convert_value(ir_expr.getBase(), ctx),
            )
        # Binop, condition, and unop expressions derive their op name from the
        # class simple name (e.g. "JAddExpr" -> "add"); they're listed inline
        # here so the dispatch table stays in one place.
        # fmt: off
        case (
            "JAddExpr"
            | "JAndExpr"
            | "JCmpExpr"
            | "JCmpgExpr"
            | "JCmplExpr"
            | "JDivExpr"
            | "JMulExpr"
            | "JOrExpr"
            | "JRemExpr"
            | "JShlExpr"
            | "JShrExpr"
            | "JSubExpr"
            | "JUshrExpr"
            | "JXorExpr"
        ):
            return SootBinopExpr(
                type_str,
                _op_name(expr_name),
                _convert_value(ir_expr.getOp1(), ctx),
                _convert_value(ir_expr.getOp2(), ctx),
            )
        case "JEqExpr" | "JGeExpr" | "JGtExpr" | "JLeExpr" | "JLtExpr" | "JNeExpr":
            return SootConditionExpr(
                type_str,
                _op_name(expr_name),
                _convert_value(ir_expr.getOp1(), ctx),
                _convert_value(ir_expr.getOp2(), ctx),
            )
        # fmt: on
        case "JNegExpr":
            return SootUnopExpr(
                type_str, _op_name(expr_name), _convert_value(ir_expr.getOp(), ctx)
            )
        case _:
            raise NotImplementedError(f"Unsupported Soot expression type {expr_name}.")


def _op_name(expr_name: str) -> str:
    """e.g. "JAddExpr" -> "add"."""
    return expr_name[1:].removesuffix("Expr").lower()


def _field_ref(raw_field: Any) -> tuple[str, str]:
    return (str(raw_field.getName()), str(raw_field.getDeclaringClass().getName()))


def _invoke_method_info(ir_expr: Any, ctx: _Ctx) -> dict[str, Any]:
    """The 4 kwargs shared by every invoke expression."""
    method = ir_expr.getMethod()
    return {
        "class_name": str(method.getDeclaringClass().getName()),
        "method_name": str(method.getName()),
        "method_params": tuple(str(p) for p in method.getParameterTypes()),
        "args": tuple(_convert_value(a, ctx) for a in ir_expr.getArgs()),
    }
