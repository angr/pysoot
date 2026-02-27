from __future__ import annotations

from dataclasses import dataclass

from .soot_statement import SootStmt


@dataclass(slots=True, unsafe_hash=True)
class SootBlock:
    label: str
    statements: tuple[SootStmt, ...]
    idx: int | None

    def __repr__(self):
        idx = self.idx if self.idx is not None else -1
        return f"<Block {idx} [{self.label}], {len(self.statements)} statements>"

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
