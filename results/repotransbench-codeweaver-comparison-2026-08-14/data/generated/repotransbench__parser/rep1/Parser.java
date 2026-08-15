import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class Parser {
    private Parser() {
    }

    public static List<Node> lexicalAnalysis(String input) throws Exception {
        Map<Integer, TokenType> mappings = new HashMap<Integer, TokenType>();
        mappings.put((int) '+', TokenType.T_PLUS);
        mappings.put((int) '-', TokenType.T_MINUS);
        mappings.put((int) '*', TokenType.T_MULT);
        mappings.put((int) '/', TokenType.T_DIV);
        mappings.put((int) '(', TokenType.T_LPAR);
        mappings.put((int) ')', TokenType.T_RPAR);

        List<Node> tokens = new ArrayList<Node>();
        for (int offset = 0; offset < input.length(); ) {
            int codePoint = input.codePointAt(offset);
            String character = new String(Character.toChars(codePoint));
            TokenType tokenType = mappings.get(codePoint);

            if (tokenType != null) {
                tokens.add(new Node(tokenType, character));
            } else if (Character.isDigit(codePoint)) {
                tokens.add(new Node(TokenType.T_NUM, Character.digit(codePoint, 10)));
            } else {
                throw new Exception("Invalid token: " + character);
            }

            offset += Character.charCount(codePoint);
        }

        tokens.add(new Node(TokenType.T_END));
        return tokens;
    }

    public static Node match(List<Node> tokens, TokenType tokenType) throws Exception {
        if (tokens.get(0).getTokenType() == tokenType) {
            return tokens.remove(0);
        }
        throw new Exception(
                "Invalid syntax on token TokenType." + tokens.get(0).getTokenType());
    }

    public static Node parseE(List<Node> tokens) throws Exception {
        Node leftNode = parseE2(tokens);

        while (tokens.get(0).getTokenType() == TokenType.T_PLUS
                || tokens.get(0).getTokenType() == TokenType.T_MINUS) {
            Node node = tokens.remove(0);
            node.getChildren().add(leftNode);
            node.getChildren().add(parseE2(tokens));
            leftNode = node;
        }

        return leftNode;
    }

    public static Node parseE2(List<Node> tokens) throws Exception {
        Node leftNode = parseE3(tokens);

        while (tokens.get(0).getTokenType() == TokenType.T_MULT
                || tokens.get(0).getTokenType() == TokenType.T_DIV) {
            Node node = tokens.remove(0);
            node.getChildren().add(leftNode);
            node.getChildren().add(parseE3(tokens));
            leftNode = node;
        }

        return leftNode;
    }

    public static Node parseE3(List<Node> tokens) throws Exception {
        if (tokens.get(0).getTokenType() == TokenType.T_NUM) {
            return tokens.remove(0);
        }

        match(tokens, TokenType.T_LPAR);
        Node expression = parseE(tokens);
        match(tokens, TokenType.T_RPAR);
        return expression;
    }

    public static Node parse(String input) throws Exception {
        List<Node> tokens = lexicalAnalysis(input);
        Node ast = parseE(tokens);
        match(tokens, TokenType.T_END);
        return ast;
    }
}
