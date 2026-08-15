import java.io.IOException;
import java.io.UncheckedIOException;

public final class Graphviz {
    static int nodeCounter = 1;

    private Graphviz() {
    }

    public static void label(Node node) {
        if (node == null) {
            throw new IllegalArgumentException("Node must not be null");
        }

        node.setId(nodeCounter);
        nodeCounter += 1;

        for (Node child : node.getChildren()) {
            label(child);
        }
    }

    public static void toGraphviz(Node node) {
        try {
            toGraphviz(node, System.out);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }

    static void toGraphviz(Node node, Appendable output) throws IOException {
        output.append("graph \"\"\n");
        output.append("{\n");

        _toGraphviz(node, output);

        output.append("}\n");
    }

    private static void _toGraphviz(Node node, Appendable output) throws IOException {
        int nodeId = requireId(node);
        output.append("n")
                .append(Integer.toString(nodeId))
                .append(" [label=\"")
                .append(String.valueOf(node.getValue()))
                .append("\"] ;\n");

        for (Node child : node.getChildren()) {
            int childId = requireId(child);
            output.append("n")
                    .append(Integer.toString(nodeId))
                    .append(" -- n")
                    .append(Integer.toString(childId))
                    .append(" ;\n");
            _toGraphviz(child, output);
        }
    }

    private static int requireId(Node node) {
        if (node == null) {
            throw new IllegalArgumentException("Node must not be null");
        }
        if (node.getId() == null) {
            throw new IllegalStateException("Node must be labeled before Graphviz output");
        }
        return node.getId();
    }

    static void run(String[] args, Appendable output) throws Exception {
        Node ast = Parser.parse(args[0]);
        label(ast);
        toGraphviz(ast, output);
    }

    public static void main(String[] args) throws Exception {
        run(args, System.out);
    }
}
