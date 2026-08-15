import java.util.function.Consumer;
import java.util.function.IntSupplier;

public final class Graphviz {
    private static int nodeCounter = 1;

    private Graphviz() {
    }

    public static void label(Node node) {
        label(node, () -> nodeCounter++);
    }

    static void label(Node node, IntSupplier ids) {
        node.setId(Integer.valueOf(ids.getAsInt()));

        for (Node child : node.getChildren()) {
            label(child, ids);
        }
    }

    public static void toGraphviz(Node node) {
        toGraphviz(node, System.out::println);
    }

    static void toGraphviz(Node node, Consumer<String> output) {
        output.accept("graph \"\"");
        output.accept("{");
        emitGraphviz(node, output);
        output.accept("}");
    }

    private static void emitGraphviz(Node node, Consumer<String> output) {
        int nodeId = requireId(node);
        output.accept("n" + nodeId + " [label=\"" + node.getValue() + "\"] ;");

        for (Node child : node.getChildren()) {
            int childId = requireId(child);
            output.accept("n" + nodeId + " -- n" + childId + " ;");
            emitGraphviz(child, output);
        }
    }

    private static int requireId(Node node) {
        Integer id = node.getId();
        if (id == null) {
            throw new IllegalStateException(
                    "Node must be labeled before Graphviz output");
        }
        return id.intValue();
    }

    static void run(String[] args, Consumer<String> output) throws ParserException {
        run(args, output, () -> nodeCounter++);
    }

    static void run(String[] args, Consumer<String> output, IntSupplier ids)
            throws ParserException {
        Node ast = Parser.parse(args[0]);
        label(ast, ids);
        toGraphviz(ast, output);
    }

    public static void main(String[] args) throws ParserException {
        run(args, System.out::println);
    }
}
