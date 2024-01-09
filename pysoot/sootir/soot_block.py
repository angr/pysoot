from __future__ import annotations

from dataclasses import dataclass

from .soot_statement import SootStmt


@dataclass(unsafe_hash=True)
class SootBlock:
    __slots__ = [
        "label",
        "statements",
        "idx",
    ]  # TODO: replace with dataclass in Python 3.10
    label: str
    statements: tuple[SootStmt, ...]
    idx: int | None

    def __repr__(self):
        return "<Block %d [%d], %d statements>" % (
            self.idx if self.idx is not None else -1,
            self.label,
            len(self.statements),
        )

    def __str__(self):
        tstr = "//" + repr(self) + "\n"

        for s in self.statements:
            sstr = str(s)
            if not sstr.strip():
                continue
            # assume one line per statement
            tstr += sstr + "\n"
        tstr = tstr.strip()
        return tstr

    @staticmethod
    def from_ir(ir_block, stmt_map, idx=None):
        stmts = []
        label = stmt_map[ir_block.getHead()]

        for ir_stmt in ir_block:
            stmt = SootStmt.from_ir(ir_stmt, stmt_map)
            stmts.append(stmt)

        return SootBlock(label, tuple(stmts), idx)
