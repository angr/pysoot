import org.graalvm.nativeimage.IsolateThread;
import org.graalvm.nativeimage.UnmanagedMemory;
import org.graalvm.nativeimage.c.function.CEntryPoint;
import org.graalvm.nativeimage.c.type.CCharPointer;
import org.graalvm.nativeimage.c.type.CTypeConversion;
import org.graalvm.word.WordFactory;

import soot.*;
import soot.jimple.*;
import soot.options.Options;
import soot.shimple.PhiExpr;
import soot.toolkits.graph.Block;
import soot.toolkits.graph.ExceptionalBlockGraph;

import java.nio.charset.StandardCharsets;
import java.util.*;

public class PySootNative {

    private static final Map<Integer, String> ATTR_MAP = new LinkedHashMap<>();
    static {
        ATTR_MAP.put(0x0001, "PUBLIC");
        ATTR_MAP.put(0x0002, "PRIVATE");
        ATTR_MAP.put(0x0004, "PROTECTED");
        ATTR_MAP.put(0x0008, "STATIC");
        ATTR_MAP.put(0x0010, "FINAL");
        ATTR_MAP.put(0x0020, "SYNCHRONIZED");
        ATTR_MAP.put(0x0040, "VOLATILE");
        ATTR_MAP.put(0x0080, "TRANSIENT");
        ATTR_MAP.put(0x0100, "NATIVE");
        ATTR_MAP.put(0x0200, "INTERFACE");
        ATTR_MAP.put(0x0400, "ABSTRACT");
        ATTR_MAP.put(0x0800, "STRICTFP");
        ATTR_MAP.put(0x1000, "SYNTHETIC");
        ATTR_MAP.put(0x2000, "ANNOTATION");
        ATTR_MAP.put(0x4000, "ENUM");
        ATTR_MAP.put(0x10000, "CONSTRUCTOR");
        ATTR_MAP.put(0x20000, "DECLARED_SYNCHRONIZED");
    }

    // ========== GraalVM Entry Points ==========

    @CEntryPoint(name = "pysoot_run")
    public static CCharPointer run(
            IsolateThread thread,
            CCharPointer cInputFile,
            CCharPointer cInputFormat,
            CCharPointer cIrFormat,
            CCharPointer cSootClasspath,
            CCharPointer cAndroidSdk) {
        try {
            String inputFile = CTypeConversion.toJavaString(cInputFile);
            String inputFormat = CTypeConversion.toJavaString(cInputFormat);
            String irFormat = CTypeConversion.toJavaString(cIrFormat);
            String sootClasspath = cSootClasspath.isNull() ? null
                    : CTypeConversion.toJavaString(cSootClasspath);
            String androidSdk = cAndroidSdk.isNull() ? null
                    : CTypeConversion.toJavaString(cAndroidSdk);
            return toCString(runSoot(inputFile, inputFormat, irFormat,
                                     sootClasspath, androidSdk));
        } catch (Throwable t) {
            StringBuilder sb = new StringBuilder();
            new Json(sb).beginObj()
                    .field("error", t.getClass().getName() + ": " + t.getMessage())
                    .endObj();
            return toCString(sb.toString());
        }
    }

    @CEntryPoint(name = "pysoot_free")
    public static void free(IsolateThread thread, CCharPointer ptr) {
        UnmanagedMemory.free(ptr);
    }

    private static CCharPointer toCString(String s) {
        byte[] bytes = s.getBytes(StandardCharsets.UTF_8);
        CCharPointer ptr = UnmanagedMemory.malloc(
                WordFactory.unsigned(bytes.length + 1));
        for (int i = 0; i < bytes.length; i++) {
            ptr.write(i, bytes[i]);
        }
        ptr.write(bytes.length, (byte) 0);
        return ptr;
    }

    // ========== Soot Runner ==========

    static String runSoot(String inputFile, String inputFormat, String irFormat,
                          String sootClasspath, String androidSdk) {
        G.reset();

        Options.v().set_process_dir(Collections.singletonList(inputFile));

        switch (inputFormat) {
            case "apk" -> {
                Options.v().set_android_jars(androidSdk);
                Options.v().set_process_multiple_dex(true);
                Options.v().set_src_prec(Options.src_prec_apk);
            }
            case "jar" -> {
                if (sootClasspath != null) {
                    Options.v().set_soot_classpath(sootClasspath);
                }
            }
            default -> throw new IllegalArgumentException(
                    "invalid input type: " + inputFormat);
        }

        switch (irFormat) {
            case "jimple" -> Options.v().set_output_format(Options.output_format_jimple);
            case "shimple" -> Options.v().set_output_format(Options.output_format_shimple);
            default -> throw new IllegalArgumentException(
                    "invalid ir format: " + irFormat);
        }

        Options.v().set_allow_phantom_refs(true);
        Options.v().setPhaseOption("cg", "all-reachable:true");
        Options.v().setPhaseOption("jb.dae", "enabled:false");
        Options.v().setPhaseOption("jb.uce", "enabled:false");
        Options.v().setPhaseOption("jj.dae", "enabled:false");
        Options.v().setPhaseOption("jj.uce", "enabled:false");
        Options.v().set_wrong_staticness(Options.wrong_staticness_ignore);

        Scene.v().loadNecessaryClasses();
        PackManager.v().runPacks();

        Chain<SootClass> rawClasses = Scene.v().getClasses();
        Map<String, SootClass> classNameMap = new LinkedHashMap<>();
        Map<String, SootClass> appClasses = new LinkedHashMap<>();
        for (SootClass c : rawClasses) {
            classNameMap.put(c.getName(), c);
            if (c.isApplicationClass()) {
                appClasses.put(c.getName(), c);
            }
        }

        Hierarchy hierarchy = new Hierarchy();
        Map<String, List<String>> hierarchyMap = new LinkedHashMap<>();
        for (Map.Entry<String, SootClass> entry : classNameMap.entrySet()) {
            try {
                List<String> names = new ArrayList<>();
                for (SootClass sc : hierarchy.getSubclassesOf(entry.getValue())) {
                    names.add(sc.getName());
                }
                hierarchyMap.put(entry.getKey(), names);
            } catch (Exception e) {
                // interfaces etc. may not support getSubclassesOf
            }
        }

        StringBuilder sb = new StringBuilder(1024 * 1024);
        Json j = new Json(sb);
        j.beginObj();
        j.key("classes").beginObj();
        for (Map.Entry<String, SootClass> entry : appClasses.entrySet()) {
            j.key(entry.getKey());
            serializeClass(j, entry.getValue());
        }
        j.endObj();
        j.key("hierarchy").beginObj();
        for (Map.Entry<String, List<String>> entry : hierarchyMap.entrySet()) {
            j.key(entry.getKey()).strs(entry.getValue());
        }
        j.endObj();
        j.endObj();
        return sb.toString();
    }

    // ========== Class / Method / Block ==========

    static void serializeClass(Json j, SootClass cls) {
        List<String> attrs = convertAttributes(cls.getModifiers());
        if (cls.isLibraryClass()) attrs.add("LibraryClass");
        if (cls.isJavaLibraryClass()) attrs.add("JavaLibraryClass");
        if (cls.isPhantom()) attrs.add("Phantom");

        j.beginObj()
                .field("name", cls.getName())
                .field("super_class",
                        cls.getName().equals("java.lang.Object")
                                ? "" : cls.getSuperclass().getName())
                .key("interfaces").beginArr();
        for (SootClass iface : cls.getInterfaces()) j.str(iface.getName());
        j.endArr()
                .key("attrs").strs(attrs)
                .key("methods").beginArr();
        for (SootMethod m : cls.getMethods()) serializeMethod(j, cls.getName(), m);
        j.endArr()
                .key("fields").beginObj();
        for (SootField f : cls.getFields()) {
            j.key(f.getName()).beginObj()
                    .key("attrs").strs(convertAttributes(f.getModifiers()))
                    .field("type", f.getType().toString())
                    .endObj();
        }
        j.endObj()
                .endObj();
    }

    static void serializeMethod(Json j, String className, SootMethod method) {
        List<String> exceptions = new ArrayList<>();
        for (SootClass e : method.getExceptions()) exceptions.add(e.getName());
        List<String> params = new ArrayList<>();
        for (Type t : method.getParameterTypes()) params.add(t.toString());

        j.beginObj()
                .field("class_name", className)
                .field("name", method.getName())
                .field("ret", method.getReturnType().toString())
                .key("attrs").strs(convertAttributes(method.getModifiers()))
                .key("exceptions").strs(exceptions)
                .key("params").strs(params);

        if (method.hasActiveBody()) {
            Body body = method.getActiveBody();
            ExceptionalBlockGraph cfg = new ExceptionalBlockGraph(body);

            Map<Unit, Integer> stmtMap = new IdentityHashMap<>();
            int n = 0;
            for (Unit u : body.getUnits()) stmtMap.put(u, n++);

            Map<Block, Integer> idxMap = new IdentityHashMap<>();
            int i = 0;
            for (Block b : cfg) idxMap.put(b, i++);

            Map<Unit, Integer> stmtToBlockIdx = new IdentityHashMap<>();
            for (Block b : cfg) {
                int blockIdx = idxMap.get(b);
                for (Iterator<Unit> it = b.iterator(); it.hasNext(); ) {
                    stmtToBlockIdx.put(it.next(), blockIdx);
                }
            }

            j.key("blocks").beginArr();
            for (Block b : cfg) serializeBlock(j, b, stmtMap, idxMap.get(b), stmtToBlockIdx);
            j.endArr();

            j.key("basic_cfg").beginArr();
            for (Block b : cfg) {
                List<Block> succs = b.getSuccs();
                if (succs.isEmpty()) continue;
                emitCfgEntry(j, idxMap.get(b), succs, idxMap);
            }
            j.endArr();

            j.key("exceptional_preds").beginArr();
            for (Block b : cfg) {
                List<Block> preds = cfg.getExceptionalPredsOf(b);
                if (preds.isEmpty()) continue;
                emitCfgEntry(j, idxMap.get(b), preds, idxMap);
            }
            j.endArr();
        } else {
            j.key("blocks").beginArr().endArr()
                    .key("basic_cfg").beginArr().endArr()
                    .key("exceptional_preds").beginArr().endArr();
        }

        j.endObj();
    }

    private static void emitCfgEntry(Json j, int blockIdx, List<Block> blocks,
                                     Map<Block, Integer> idxMap) {
        j.beginArr().num(blockIdx).beginArr();
        for (Block b : blocks) j.num(idxMap.get(b));
        j.endArr().endArr();
    }

    static void serializeBlock(Json j, Block block,
                               Map<Unit, Integer> stmtMap, int blockIdx,
                               Map<Unit, Integer> stmtToBlockIdx) {
        j.beginObj()
                .field("label", stmtMap.get(block.getHead()))
                .field("idx", blockIdx)
                .key("statements").beginArr();
        for (Iterator<Unit> it = block.iterator(); it.hasNext(); ) {
            serializeStmt(j, (Stmt) it.next(), stmtMap, stmtToBlockIdx);
        }
        j.endArr().endObj();
    }

    // ========== Statement Serialization ==========

    static void serializeStmt(Json j, Stmt stmt,
                              Map<Unit, Integer> stmtMap,
                              Map<Unit, Integer> stmtToBlockIdx) {
        String stmtType = stmt.getClass().getSimpleName();
        j.beginObj()
                .field("label", stmtMap.get(stmt))
                .field("offset", 0);

        switch (stmtType) {
            case "JAssignStmt" -> {
                DefinitionStmt ds = (DefinitionStmt) stmt;
                j.field("type", "assign").key("left_op");
                serializeValue(j, ds.getLeftOp(), stmtToBlockIdx);
                j.key("right_op");
                serializeValue(j, ds.getRightOp(), stmtToBlockIdx);
            }
            case "JIdentityStmt" -> {
                DefinitionStmt ds = (DefinitionStmt) stmt;
                j.field("type", "identity").key("left_op");
                serializeValue(j, ds.getLeftOp(), stmtToBlockIdx);
                j.key("right_op");
                serializeValue(j, ds.getRightOp(), stmtToBlockIdx);
            }
            case "JBreakpointStmt" -> j.field("type", "breakpoint");
            case "JEnterMonitorStmt" -> {
                j.field("type", "enter_monitor").key("op");
                serializeValue(j, ((EnterMonitorStmt) stmt).getOp(), stmtToBlockIdx);
            }
            case "JExitMonitorStmt" -> {
                j.field("type", "exit_monitor").key("op");
                serializeValue(j, ((ExitMonitorStmt) stmt).getOp(), stmtToBlockIdx);
            }
            case "JGotoStmt" -> j.field("type", "goto")
                    .field("target", stmtMap.get(((GotoStmt) stmt).getTarget()));
            case "JIfStmt" -> {
                IfStmt is = (IfStmt) stmt;
                j.field("type", "if").key("condition");
                serializeValue(j, is.getCondition(), stmtToBlockIdx);
                j.field("target", stmtMap.get(is.getTarget()));
            }
            case "JInvokeStmt" -> {
                j.field("type", "invoke").key("invoke_expr");
                serializeValue(j, ((InvokeStmt) stmt).getInvokeExpr(), stmtToBlockIdx);
            }
            case "JReturnStmt" -> {
                j.field("type", "return").key("value");
                serializeValue(j, ((ReturnStmt) stmt).getOp(), stmtToBlockIdx);
            }
            case "JReturnVoidStmt" -> j.field("type", "return_void");
            case "JLookupSwitchStmt" -> {
                LookupSwitchStmt ls = (LookupSwitchStmt) stmt;
                j.field("type", "lookup_switch").key("key");
                serializeValue(j, ls.getKey(), stmtToBlockIdx);
                j.key("lookup_values_and_targets").beginArr();
                for (int i = 0; i < ls.getTargetCount(); i++) {
                    j.beginArr().num(ls.getLookupValue(i))
                            .num(stmtMap.get(ls.getTarget(i))).endArr();
                }
                j.endArr().field("default_target", stmtMap.get(ls.getDefaultTarget()));
            }
            case "JTableSwitchStmt" -> {
                TableSwitchStmt ts = (TableSwitchStmt) stmt;
                j.field("type", "table_switch").key("key");
                serializeValue(j, ts.getKey(), stmtToBlockIdx);
                j.field("low_index", ts.getLowIndex())
                        .field("high_index", ts.getHighIndex())
                        .key("targets").beginArr();
                for (int i = 0; i < ts.getTargetCount(); i++) {
                    j.num(stmtMap.get(ts.getTarget(i)));
                }
                j.endArr().field("default_target", stmtMap.get(ts.getDefaultTarget()));
            }
            case "JThrowStmt" -> {
                j.field("type", "throw").key("op");
                serializeValue(j, ((ThrowStmt) stmt).getOp(), stmtToBlockIdx);
            }
            default -> j.field("type", "unknown").field("raw", stmtType);
        }

        j.endObj();
    }

    // ========== Value Serialization ==========

    static void serializeValue(Json j, Value value, Map<Unit, Integer> stmtToBlockIdx) {
        String simpleName = value.getClass().getSimpleName()
                .replace("Jimple", "").replace("Shimple", "");

        if (simpleName.endsWith("Expr")) {
            serializeExpr(j, simpleName, value, stmtToBlockIdx);
            return;
        }

        j.beginObj().field("type", value.getType().toString());

        switch (simpleName) {
            case "Local" -> j.field("value_type", "local")
                    .field("name", ((Local) value).getName());
            case "JArrayRef" -> {
                ArrayRef ar = (ArrayRef) value;
                j.field("value_type", "array_ref").key("base");
                serializeValue(j, ar.getBase(), stmtToBlockIdx);
                j.key("index");
                serializeValue(j, ar.getIndex(), stmtToBlockIdx);
            }
            case "JCaughtExceptionRef" -> j.field("value_type", "caught_exception_ref");
            case "ParameterRef" -> j.field("value_type", "param_ref")
                    .field("index", ((ParameterRef) value).getIndex());
            case "ThisRef" -> j.field("value_type", "this_ref");
            case "StaticFieldRef" -> {
                SootField field = ((StaticFieldRef) value).getField();
                j.field("value_type", "static_field_ref")
                        .key("field").beginArr()
                        .str(field.getName())
                        .str(field.getDeclaringClass().getName())
                        .endArr();
            }
            case "JInstanceFieldRef" -> {
                InstanceFieldRef ifr = (InstanceFieldRef) value;
                SootField field = ifr.getField();
                j.field("value_type", "instance_field_ref").key("base");
                serializeValue(j, ifr.getBase(), stmtToBlockIdx);
                j.key("field").beginArr()
                        .str(field.getName())
                        .str(field.getDeclaringClass().getName())
                        .endArr();
            }
            case "ClassConstant" -> j.field("value_type", "class_constant")
                    .field("value", ((ClassConstant) value).getValue());
            case "DoubleConstant" -> j.field("value_type", "double_constant")
                    .key("value").num(((DoubleConstant) value).value);
            case "FloatConstant" -> j.field("value_type", "float_constant")
                    .key("value").num(((FloatConstant) value).value);
            case "IntConstant" -> j.field("value_type", "int_constant")
                    .key("value").num(((IntConstant) value).value);
            case "LongConstant" -> j.field("value_type", "long_constant")
                    .key("value").num(((LongConstant) value).value);
            case "NullConstant" -> j.field("value_type", "null_constant");
            case "StringConstant" -> j.field("value_type", "string_constant")
                    .field("value", ((StringConstant) value).value);
            default -> j.field("value_type", "unknown").field("raw", simpleName);
        }

        j.endObj();
    }

    // ========== Expression Serialization ==========

    static void serializeExpr(Json j, String simpleName, Value value,
                              Map<Unit, Integer> stmtToBlockIdx) {
        j.beginObj().field("type", value.getType().toString());

        switch (simpleName) {
            case "JCastExpr" -> {
                CastExpr ce = (CastExpr) value;
                j.field("value_type", "cast")
                        .field("cast_type", ce.getCastType().toString())
                        .key("value");
                serializeValue(j, ce.getOp(), stmtToBlockIdx);
            }
            case "JLengthExpr" -> {
                j.field("value_type", "length").key("value");
                serializeValue(j, ((LengthExpr) value).getOp(), stmtToBlockIdx);
            }
            case "JNewExpr" -> j.field("value_type", "new")
                    .field("base_type", ((NewExpr) value).getBaseType().toString());
            case "JNewArrayExpr" -> {
                NewArrayExpr nae = (NewArrayExpr) value;
                j.field("value_type", "new_array")
                        .field("base_type", nae.getBaseType().toString())
                        .key("size");
                serializeValue(j, nae.getSize(), stmtToBlockIdx);
            }
            case "JNewMultiArrayExpr" -> {
                NewMultiArrayExpr nmae = (NewMultiArrayExpr) value;
                j.field("value_type", "new_multi_array")
                        .field("base_type", nmae.getBaseType().toString())
                        .key("sizes").beginArr();
                for (int i = 0; i < nmae.getSizeCount(); i++) {
                    serializeValue(j, nmae.getSize(i), stmtToBlockIdx);
                }
                j.endArr();
            }
            case "JInstanceOfExpr" -> {
                InstanceOfExpr ioe = (InstanceOfExpr) value;
                j.field("value_type", "instanceof")
                        .field("check_type", ioe.getCheckType().toString())
                        .key("value");
                serializeValue(j, ioe.getOp(), stmtToBlockIdx);
            }
            case "SPhiExpr" -> {
                // Single-pass: resolve (value, block_idx) tuples here so the
                // pysoot SootPhiExpr can be built without post-init mutation.
                PhiExpr phi = (PhiExpr) value;
                j.field("value_type", "phi").key("values").beginArr();
                for (ValueUnitPair pair : phi.getArgs()) {
                    Integer blockIdx = stmtToBlockIdx.get(pair.getUnit());
                    j.beginObj().key("value");
                    serializeValue(j, pair.getValue(), stmtToBlockIdx);
                    j.field("block_idx", blockIdx != null ? blockIdx : -1).endObj();
                }
                j.endArr();
            }
            case "JStaticInvokeExpr" -> {
                j.field("value_type", "static_invoke");
                serializeInvokeCommon(j, (InvokeExpr) value, stmtToBlockIdx);
            }
            case "JDynamicInvokeExpr" -> {
                j.field("value_type", "dynamic_invoke");
                serializeInvokeCommon(j, (InvokeExpr) value, stmtToBlockIdx);
                j.key("bootstrap_method").null_().key("bootstrap_args").null_();
            }
            case "JVirtualInvokeExpr", "JInterfaceInvokeExpr", "JSpecialInvokeExpr" -> {
                String kind = switch (simpleName) {
                    case "JVirtualInvokeExpr" -> "virtual_invoke";
                    case "JInterfaceInvokeExpr" -> "interface_invoke";
                    default -> "special_invoke";
                };
                InstanceInvokeExpr iie = (InstanceInvokeExpr) value;
                j.field("value_type", kind);
                serializeInvokeCommon(j, iie, stmtToBlockIdx);
                j.key("base");
                serializeValue(j, iie.getBase(), stmtToBlockIdx);
            }
            // Binop, condition, and unop expressions derive their op name from
            // the class simple name (e.g. "JAddExpr" -> "add").
            case "JAddExpr", "JAndExpr", "JCmpExpr", "JCmpgExpr", "JCmplExpr",
                 "JDivExpr", "JMulExpr", "JOrExpr", "JRemExpr", "JShlExpr",
                 "JShrExpr", "JSubExpr", "JUshrExpr", "JXorExpr" -> {
                BinopExpr be = (BinopExpr) value;
                j.field("value_type", "binop").field("op", opName(simpleName))
                        .key("value1");
                serializeValue(j, be.getOp1(), stmtToBlockIdx);
                j.key("value2");
                serializeValue(j, be.getOp2(), stmtToBlockIdx);
            }
            case "JEqExpr", "JGeExpr", "JGtExpr",
                 "JLeExpr", "JLtExpr", "JNeExpr" -> {
                ConditionExpr ce = (ConditionExpr) value;
                j.field("value_type", "condition").field("op", opName(simpleName))
                        .key("value1");
                serializeValue(j, ce.getOp1(), stmtToBlockIdx);
                j.key("value2");
                serializeValue(j, ce.getOp2(), stmtToBlockIdx);
            }
            case "JNegExpr" -> {
                j.field("value_type", "unop").field("op", opName(simpleName))
                        .key("value");
                serializeValue(j, ((UnopExpr) value).getOp(), stmtToBlockIdx);
            }
            default -> j.field("value_type", "unknown_expr").field("raw", simpleName);
        }

        j.endObj();
    }

    /** Emits the 4 fields shared by every invoke expression. */
    static void serializeInvokeCommon(Json j, InvokeExpr expr,
                                      Map<Unit, Integer> stmtToBlockIdx) {
        SootMethodRef method = expr.getMethodRef();
        List<Type> paramTypes = method.getParameterTypes();
        List<String> params = new ArrayList<>(paramTypes.size());
        for (Type t : paramTypes) params.add(t.toString());

        j.field("class_name", method.getDeclaringClass().getName())
                .field("method_name", method.getName())
                .key("method_params").strs(params)
                .key("args").beginArr();
        for (int i = 0; i < expr.getArgCount(); i++) {
            serializeValue(j, expr.getArg(i), stmtToBlockIdx);
        }
        j.endArr();
    }

    // ========== Helpers ==========

    /** "JAddExpr" -> "add". */
    static String opName(String simpleName) {
        String s = simpleName;
        if (s.startsWith("J")) s = s.substring(1);
        if (s.endsWith("Expr")) s = s.substring(0, s.length() - 4);
        return s.toLowerCase();
    }

    static List<String> convertAttributes(int modifiers) {
        List<String> attrs = new ArrayList<>();
        for (Map.Entry<Integer, String> entry : ATTR_MAP.entrySet()) {
            if ((modifiers & entry.getKey()) != 0) {
                attrs.add(entry.getValue());
            }
        }
        return attrs;
    }

    // ========== Json Builder ==========

    /**
     * Tiny stateful JSON writer that auto-inserts separators between
     * fields/elements. Each method returns `this` for chaining.
     */
    static final class Json {
        private final StringBuilder sb;
        private boolean needsSep = false;

        Json(StringBuilder sb) { this.sb = sb; }

        Json beginObj() { sep(); sb.append('{'); needsSep = false; return this; }
        Json endObj() { sb.append('}'); needsSep = true; return this; }
        Json beginArr() { sep(); sb.append('['); needsSep = false; return this; }
        Json endArr() { sb.append(']'); needsSep = true; return this; }

        Json key(String k) {
            sep();
            sb.append('"');
            escape(k);
            sb.append("\":");
            needsSep = false;
            return this;
        }

        Json str(String s) { sep(); sb.append('"'); escape(s); sb.append('"'); needsSep = true; return this; }
        Json num(long n) { sep(); sb.append(n); needsSep = true; return this; }
        Json num(double d) { sep(); sb.append(d); needsSep = true; return this; }
        Json null_() { sep(); sb.append("null"); needsSep = true; return this; }

        Json field(String k, String v) { return key(k).str(v); }
        Json field(String k, long n) { return key(k).num(n); }

        Json strs(Collection<String> items) {
            beginArr();
            for (String s : items) str(s);
            return endArr();
        }

        private void sep() { if (needsSep) sb.append(','); }

        private void escape(String s) {
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"' -> sb.append("\\\"");
                    case '\\' -> sb.append("\\\\");
                    case '\b' -> sb.append("\\b");
                    case '\f' -> sb.append("\\f");
                    case '\n' -> sb.append("\\n");
                    case '\r' -> sb.append("\\r");
                    case '\t' -> sb.append("\\t");
                    default -> {
                        if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                        else sb.append(c);
                    }
                }
            }
        }
    }
}
