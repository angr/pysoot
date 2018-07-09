
from . import convert_soot_attributes


class SootMethod(object):

    __slots__ = ['class_name', 'name', 'ret', 'attrs', 'attrs', 'exceptions', 'blocks', 'params', 'block_by_label']

    def __init__(self, class_name, name, params, ret, attrs, exceptions, blocks):
        self.class_name = class_name
        self.name = name
        self.params = params
        self.ret = ret
        self.attrs = attrs
        self.exceptions = exceptions
        self.blocks = blocks

        self.block_by_label = dict((block.label, block) for block in self.blocks)

    def __str__(self):
        tstr = "//" + repr(self) + "\n"
        if self.attrs:
            tstr += " ".join([a.lower() for a in self.attrs]) + " "
        tstr += "%s %s(%s){\n" % (self.ret, self.name, ", ".join(self.params))

        for idx, b in enumerate(self.blocks):
            tstr += "\n".join(["\t"+line for line in str(b).split("\n")]) + "\n"

        tstr += "}\n"
        return tstr

    @staticmethod
    def from_ir(class_name, ir_method):
        blocks = []

        if ir_method.hasActiveBody():
            body = ir_method.getActiveBody()
            from soot.toolkits.graph import ExceptionalBlockGraph
            cfg = ExceptionalBlockGraph(body)
            units = body.getUnits()
            # this should work, I assume that since here we are in Jython the map is "hashed" 
            # based on object identity (and not value), equivalent of Java == operator or Python is operator
            # we create a map to assign to every instruction instance a label
            stmt_map = {u: i for i, u in enumerate(units)}
            for idx, ir_block in enumerate(cfg):
                soot_block = SootBlock.from_ir(ir_block, stmt_map, idx)
                blocks.append(soot_block)

        params = tuple(str(p) for p in ir_method.getParameterTypes())
        attrs = convert_soot_attributes(ir_method.getModifiers())
        exceptions = tuple(e.getName() for e in ir_method.getExceptions())
        rt = str(ir_method.getReturnType())

        return SootMethod(class_name, ir_method.getName(), params, rt, attrs, exceptions, blocks)


from .soot_block import SootBlock
