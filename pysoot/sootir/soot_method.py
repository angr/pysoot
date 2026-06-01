from __future__ import annotations

from dataclasses import dataclass

from frozendict import frozendict

from .soot_block import SootBlock


@dataclass(slots=True, frozen=True)
class SootMethod:
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
    def block_by_label(self):
        return {b.label: b for b in self.blocks}

    def __str__(self):
        tstr = "//" + repr(self) + "\n"
        if self.attrs:
            tstr += " ".join([a.lower() for a in self.attrs]) + " "
        tstr += "{} {}({}){{\n".format(self.ret, self.name, ", ".join(self.params))

        for b in self.blocks:
            tstr += "\n".join(["\t" + line for line in str(b).split("\n")]) + "\n"

        tstr += "}\n"
        return tstr
