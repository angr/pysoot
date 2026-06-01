from __future__ import annotations

from dataclasses import dataclass

from frozendict import frozendict

from .soot_method import SootMethod


@dataclass(slots=True, frozen=True)
class SootClass:
    name: str
    super_class: str
    interfaces: tuple[str, ...]
    attrs: tuple[str, ...]
    methods: tuple[SootMethod, ...]
    fields: frozendict[str, tuple[tuple[str], str]]

    def __str__(self):
        tstr = "//" + repr(self) + "\n"
        tstr += (
            " ".join([a.lower() for a in self.attrs])
            + " class "
            + self.name
            + " extends "
            + self.super_class
        )
        if self.interfaces:
            tstr += " implements " + ", ".join(self.interfaces)
        tstr += "{\n"

        for field_name, field_value in self.fields.items():
            tstr += (
                "\t"
                + " ".join([f.lower() for f in field_value[0]])
                + " "
                + field_value[1]
                + " "
                + field_name
                + "\n"
            )
        tstr += "\n"

        for m in self.methods:
            tstr += "\n".join(["\t" + line for line in str(m).split("\n")]) + "\n"

        tstr += "}\n"
        return tstr
