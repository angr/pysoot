from __future__ import annotations

from dataclasses import dataclass

from .soot_statement import SootStmt


@dataclass(slots=True, frozen=True)
class SootBlock:
    label: int
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
