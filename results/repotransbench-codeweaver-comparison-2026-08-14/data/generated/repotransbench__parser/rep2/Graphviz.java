import java.io.PrintStream;

public final class Graphviz {
    public static int nodeCounter = 1;

    private Graphviz() {
    }

    public static void label(Node node) {
        node.setId(nodeCounter);
        nodeCounter += 1;

        for (Node child : node.getChildren()) {
            label(child);
        }
    }

    public static void toGraphviz(Node node) {
        toGraphviz(node, System.out);
    }

    static void toGraphviz(Node node, PrintStream output) {
        output.println("graph \"\"");
        output.println("{");

        emitGraphviz(node, output);

        output.println("}");
    }

    private static void emitGraphviz(Node node, PrintStream output) {
        int nodeId = requireNodeId(node);
        output.println("n" + nodeId + " [label=\"" + node.getValue() + "\"] ;");

        for (Node child : node.getChildren()) {
            int childId = requireNodeId(child);
            output.println("n" + nodeId + " -- n" + childId + " ;");
            emitGraphviz(child, output);
        }
    }

    private static int requireNodeId(Node node) {
        Integer id = node.getId();
        if (id == null) {
            throw new IllegalStateException("Cannot emit an unlabeled node");
        }
        return id;
    }

    public static void main(String[] args) throws ParserException {
        String inputString = args[0];
        Node ast = Parser.parse(inputString);
        label(ast);
        toGraphviz(ast);
    }
}
