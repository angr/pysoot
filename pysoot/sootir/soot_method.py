from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from frozendict import frozendict
from jpype.types import JClass

from .soot_block import SootBlock
from . import convert_soot_attributes


@dataclass(unsafe_hash=True)
class SootMethod:
    # TODO: replace with dataclass in Python 3.10
    __slots__ = [
        "class_name",
        "name",
        "ret",
        "attrs",
        "exceptions",
        "blocks",
        "params",
        "basic_cfg",
        "exceptional_preds",
    ]
    class_name: str
    name: str
    ret: str
    attrs: tuple[str, ...]
    exceptions: tuple[str, ...]
    blocks: tuple[SootBlock, ...]
    params: tuple[str, ...]
    basic_cfg: frozendict[SootBlock, tuple[SootBlock]]
    exceptional_preds: frozendict[SootBlock, tuple[SootBlock]]

    @property
    @lru_cache(maxsize=1)
    def block_by_label(self):
        return {b.label: b for b in self.blocks}

    def __str__(self):
        tstr = "//" + repr(self) + "\n"
        if self.attrs:
            tstr += " ".join([a.lower() for a in self.attrs]) + " "
        tstr += "%s %s(%s){\n" % (self.ret, self.name, ", ".join(self.params))

        for idx, b in enumerate(self.blocks):
            tstr += "\n".join(["\t" + line for line in str(b).split("\n")]) + "\n"

        tstr += "}\n"
        return tstr

    @staticmethod
    def from_ir(class_name, ir_method):
        blocks = []
        basic_cfg = defaultdict(list)
        exceptional_preds = defaultdict(list)

        if ir_method.hasActiveBody():
            body = ir_method.getActiveBody()
            ExceptionalBlockGraph = JClass("soot.toolkits.graph.ExceptionalBlockGraph")
            cfg = ExceptionalBlockGraph(body)
            units = body.getUnits()

            # this should work, I assume that since here we are in Jython the map is "hashed"
            # based on object identity (and not value), equivalent of Java == operator or Python is operator
            # we create a map to assign to every instruction instance a label
            stmt_map = {u: i for i, u in enumerate(units)}
            # We need index and block maps to consistently retrieve soot_blocks later when we create
            # links to successors
            idx_map = {ir_block: idx for idx, ir_block in enumerate(cfg)}
            block_map = dict()
            for ir_block in cfg:
                soot_block = SootBlock.from_ir(ir_block, stmt_map, idx_map[ir_block])
                blocks.append(soot_block)
                block_map[idx_map[ir_block]] = soot_block

            # Walk through the CFG again to link soot_blocks to the successors soot_blocks
            for ir_block in cfg:
                idx = idx_map[ir_block]
                soot_block = block_map[idx]
                succs = ir_block.getSuccs()
                for succ in succs:
                    succ_idx = idx_map[succ]
                    succ_soot_block = block_map[succ_idx]
                    basic_cfg[soot_block].append(succ_soot_block)

            # Walk through the CFG again to link exceptional predecessors: soot_blocks
            # that are predecessors of a given block when only exceptional control flow is considered.
            for ir_block in cfg:
                idx = idx_map[ir_block]
                soot_block = block_map[idx]
                preds = cfg.getExceptionalPredsOf(ir_block)
                for pred in preds:
                    pred_idx = idx_map[pred]
                    pred_soot_block = block_map[pred_idx]
                    exceptional_preds[soot_block].append(pred_soot_block)

            from .soot_value import SootValue

            stmt_to_block_idx = {}
            for ir_block in cfg:
                for ir_stmt in ir_block:
                    stmt_to_block_idx[ir_stmt] = idx_map[ir_block]

            for ir_block in cfg:
                for ir_stmt in ir_block:
                    if "Assign" in ir_stmt.getClass().getSimpleName():
                        ir_expr = ir_stmt.getRightOp()
                        if "Phi" in ir_expr.getClass().getSimpleName():
                            values = tuple(
                                (
                                    SootValue.from_ir(v.getValue()),
                                    stmt_to_block_idx[v.getUnit()],
                                )
                                for v in ir_expr.getArgs()
                            )

                            phi_expr = SootValue.IREXPR_TO_EXPR[ir_expr]
                            phi_expr.values = values

            # "Free" map
            SootValue.IREXPR_TO_EXPR = {}

        params = tuple(str(p) for p in ir_method.getParameterTypes())
        attrs = convert_soot_attributes(ir_method.getModifiers())
        exceptions = tuple(e.getName() for e in ir_method.getExceptions())
        rt = str(ir_method.getReturnType())

        return SootMethod(
            class_name=class_name,
            name=str(ir_method.getName()),
            params=params,
            ret=rt,
            attrs=tuple(attrs),
            exceptions=tuple(exceptions),
            blocks=tuple(blocks),
            basic_cfg=frozendict({k: tuple(v) for k, v in basic_cfg.items()}),
            exceptional_preds=frozendict({k: tuple(v) for k, v in exceptional_preds.items()}),
        )
