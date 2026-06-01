from __future__ import annotations

import ctypes
import json
import os
import sys

from frozendict import frozendict

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
)

_lib = None
_isolate = None
_thread = None


def _lib_path() -> str:
    pkg_dir = os.path.dirname(__file__)
    if sys.platform == "darwin":
        return os.path.join(pkg_dir, "libpysoot.dylib")
    elif sys.platform == "win32":
        return os.path.join(pkg_dir, "libpysoot.dll")
    else:
        return os.path.join(pkg_dir, "libpysoot.so")


def _load_lib():
    global _lib, _isolate, _thread
    if _lib is not None:
        return

    path = _lib_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Native library not found at {path}. "
            f"Build it with: cd pysoot/java && ./build.sh"
        )

    _lib = ctypes.CDLL(path)

    # graal_create_isolate(params, *isolate, *thread) -> int
    _lib.graal_create_isolate.restype = ctypes.c_int
    _lib.graal_create_isolate.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]

    # graal_tear_down_isolate(thread) -> int
    _lib.graal_tear_down_isolate.restype = ctypes.c_int
    _lib.graal_tear_down_isolate.argtypes = [ctypes.c_void_p]

    # pysoot_run(thread, input_file, input_format, ir_format,
    #            soot_classpath, android_sdk) -> char*
    _lib.pysoot_run.restype = ctypes.c_void_p
    _lib.pysoot_run.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]

    # pysoot_free(thread, ptr) -> void
    _lib.pysoot_free.restype = None
    _lib.pysoot_free.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    _isolate = ctypes.c_void_p()
    _thread = ctypes.c_void_p()
    ret = _lib.graal_create_isolate(None, ctypes.byref(_isolate), ctypes.byref(_thread))
    if ret != 0:
        raise RuntimeError(f"Failed to create GraalVM isolate (error code {ret})")


def run_soot(
    input_file: str,
    input_format: str,
    android_sdk: str | None,
    soot_classpath: str | None,
    ir_format: str,
) -> tuple[dict[str, SootClass], dict[str, list[str]]]:
    _load_lib()

    c_input = input_file.encode("utf-8")
    c_format = input_format.encode("utf-8")
    c_ir = ir_format.encode("utf-8")
    c_classpath = soot_classpath.encode("utf-8") if soot_classpath else None
    c_sdk = android_sdk.encode("utf-8") if android_sdk else None

    result_ptr = _lib.pysoot_run(_thread, c_input, c_format, c_ir, c_classpath, c_sdk)
    if not result_ptr:
        raise RuntimeError("pysoot_run returned NULL")

    try:
        result_json = ctypes.string_at(result_ptr).decode("utf-8")
    finally:
        _lib.pysoot_free(_thread, result_ptr)

    data = json.loads(result_json)

    if "error" in data and data["error"] is not None:
        raise RuntimeError(f"Soot analysis failed: {data['error']}")

    classes = {}
    for name, cls_data in data["classes"].items():
        classes[name] = _deserialize_class(cls_data)

    hierarchy = {}
    for name, subclasses in data["hierarchy"].items():
        hierarchy[name] = subclasses

    return classes, hierarchy


# ========== Deserialization ==========


def _deserialize_class(d: dict) -> SootClass:
    methods = tuple(_deserialize_method(m) for m in d["methods"])
    fields = {}
    for fname, fdata in d["fields"].items():
        fields[fname] = (tuple(fdata["attrs"]), fdata["type"])
    return SootClass(
        name=d["name"],
        super_class=d["super_class"],
        interfaces=tuple(d["interfaces"]),
        attrs=tuple(d["attrs"]),
        methods=methods,
        fields=frozendict(fields),
    )


def _deserialize_method(d: dict) -> SootMethod:
    blocks_data = d["blocks"]
    blocks = tuple(_deserialize_block(b) for b in blocks_data)

    block_by_idx = {b.idx: b for b in blocks}

    basic_cfg = {}
    for block_idx, succ_idxs in d["basic_cfg"]:
        block = block_by_idx[block_idx]
        basic_cfg[block] = tuple(block_by_idx[i] for i in succ_idxs)

    exceptional_preds = {}
    for block_idx, pred_idxs in d["exceptional_preds"]:
        block = block_by_idx[block_idx]
        exceptional_preds[block] = tuple(block_by_idx[i] for i in pred_idxs)

    return SootMethod(
        class_name=d["class_name"],
        name=d["name"],
        ret=d["ret"],
        attrs=tuple(d["attrs"]),
        exceptions=tuple(d["exceptions"]),
        params=tuple(d["params"]),
        blocks=blocks,
        basic_cfg=frozendict(basic_cfg),
        exceptional_preds=frozendict(exceptional_preds),
    )


def _deserialize_block(d: dict) -> SootBlock:
    stmts = tuple(_deserialize_stmt(s) for s in d["statements"])
    return SootBlock(label=d["label"], statements=stmts, idx=d["idx"])


def _deserialize_stmt(d: dict) -> object:
    label = d["label"]
    offset = d["offset"]
    t = d["type"]

    if t == "assign":
        return AssignStmt(
            label,
            offset,
            _deserialize_value(d["left_op"]),
            _deserialize_value(d["right_op"]),
        )
    elif t == "identity":
        return IdentityStmt(
            label,
            offset,
            _deserialize_value(d["left_op"]),
            _deserialize_value(d["right_op"]),
        )
    elif t == "breakpoint":
        return BreakpointStmt(label, offset)
    elif t == "enter_monitor":
        return EnterMonitorStmt(label, offset, _deserialize_value(d["op"]))
    elif t == "exit_monitor":
        return ExitMonitorStmt(label, offset, _deserialize_value(d["op"]))
    elif t == "goto":
        return GotoStmt(label, offset, d["target"])
    elif t == "if":
        return IfStmt(
            label,
            offset,
            _deserialize_value(d["condition"]),
            d["target"],
        )
    elif t == "invoke":
        return InvokeStmt(label, offset, _deserialize_value(d["invoke_expr"]))
    elif t == "return":
        return ReturnStmt(label, offset, _deserialize_value(d["value"]))
    elif t == "return_void":
        return ReturnVoidStmt(label, offset)
    elif t == "lookup_switch":
        lvt = frozendict(
            {val: target for val, target in d["lookup_values_and_targets"]}
        )
        return LookupSwitchStmt(
            label,
            offset,
            _deserialize_value(d["key"]),
            lvt,
            d["default_target"],
        )
    elif t == "table_switch":
        targets = tuple(d["targets"])
        lvt = frozendict(dict(zip(range(d["low_index"], d["high_index"] + 1), targets)))
        return TableSwitchStmt(
            label,
            offset,
            _deserialize_value(d["key"]),
            d["low_index"],
            d["high_index"],
            targets,
            lvt,
            d["default_target"],
        )
    elif t == "throw":
        return ThrowStmt(label, offset, _deserialize_value(d["op"]))
    else:
        raise NotImplementedError(f"Unknown statement type: {t}")


def _deserialize_value(d: dict) -> object:
    vt = d["value_type"]
    typ = d["type"]

    if vt == "local":
        return SootLocal(typ, d["name"])
    elif vt == "array_ref":
        return SootArrayRef(
            typ,
            _deserialize_value(d["base"]),
            _deserialize_value(d["index"]),
        )
    elif vt == "caught_exception_ref":
        return SootCaughtExceptionRef(typ)
    elif vt == "param_ref":
        return SootParamRef(typ, d["index"])
    elif vt == "this_ref":
        return SootThisRef(typ)
    elif vt == "static_field_ref":
        return SootStaticFieldRef(typ, tuple(d["field"]))
    elif vt == "instance_field_ref":
        return SootInstanceFieldRef(
            typ, _deserialize_value(d["base"]), tuple(d["field"])
        )
    elif vt == "class_constant":
        return SootClassConstant(typ, d["value"])
    elif vt == "double_constant":
        return SootDoubleConstant(typ, float(d["value"]))
    elif vt == "float_constant":
        return SootFloatConstant(typ, float(d["value"]))
    elif vt == "int_constant":
        return SootIntConstant(typ, int(d["value"]))
    elif vt == "long_constant":
        return SootLongConstant(typ, int(d["value"]))
    elif vt == "null_constant":
        return SootNullConstant(typ)
    elif vt == "string_constant":
        return SootStringConstant(typ, d["value"])
    elif vt == "binop":
        return SootBinopExpr(
            typ,
            d["op"],
            _deserialize_value(d["value1"]),
            _deserialize_value(d["value2"]),
        )
    elif vt == "unop":
        return SootUnopExpr(typ, d["op"], _deserialize_value(d["value"]))
    elif vt == "cast":
        return SootCastExpr(typ, d["cast_type"], _deserialize_value(d["value"]))
    elif vt == "condition":
        return SootConditionExpr(
            typ,
            d["op"],
            _deserialize_value(d["value1"]),
            _deserialize_value(d["value2"]),
        )
    elif vt == "length":
        return SootLengthExpr(typ, _deserialize_value(d["value"]))
    elif vt == "new_array":
        return SootNewArrayExpr(typ, d["base_type"], _deserialize_value(d["size"]))
    elif vt == "new_multi_array":
        return SootNewMultiArrayExpr(
            typ,
            d["base_type"],
            tuple(_deserialize_value(s) for s in d["sizes"]),
        )
    elif vt == "new":
        return SootNewExpr(typ, d["base_type"])
    elif vt == "phi":
        values = tuple(
            (_deserialize_value(v["value"]), v["block_idx"]) for v in d["values"]
        )
        return SootPhiExpr(typ, values)
    elif vt == "instanceof":
        return SootInstanceOfExpr(typ, d["check_type"], _deserialize_value(d["value"]))
    elif vt == "virtual_invoke":
        return SootVirtualInvokeExpr(
            type=typ,
            class_name=d["class_name"],
            method_name=d["method_name"],
            method_params=tuple(d["method_params"]),
            args=tuple(_deserialize_value(a) for a in d["args"]),
            base=_deserialize_value(d["base"]),
        )
    elif vt == "interface_invoke":
        return SootInterfaceInvokeExpr(
            type=typ,
            class_name=d["class_name"],
            method_name=d["method_name"],
            method_params=tuple(d["method_params"]),
            args=tuple(_deserialize_value(a) for a in d["args"]),
            base=_deserialize_value(d["base"]),
        )
    elif vt == "special_invoke":
        return SootSpecialInvokeExpr(
            type=typ,
            class_name=d["class_name"],
            method_name=d["method_name"],
            method_params=tuple(d["method_params"]),
            args=tuple(_deserialize_value(a) for a in d["args"]),
            base=_deserialize_value(d["base"]),
        )
    elif vt == "static_invoke":
        return SootStaticInvokeExpr(
            type=typ,
            class_name=d["class_name"],
            method_name=d["method_name"],
            method_params=tuple(d["method_params"]),
            args=tuple(_deserialize_value(a) for a in d["args"]),
        )
    elif vt == "dynamic_invoke":
        return SootDynamicInvokeExpr(
            type=typ,
            class_name=d["class_name"],
            method_name=d["method_name"],
            method_params=tuple(d["method_params"]),
            args=tuple(_deserialize_value(a) for a in d["args"]),
            bootstrap_method=None,
            bootstrap_args=None,
        )
    else:
        raise NotImplementedError(f"Unknown value type: {vt}")
