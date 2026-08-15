import java.util.ArrayList;
import java.util.List;

public final class Parser {
    private Parser() {
    }

    public static List<Node> lexicalAnalysis(String input) throws ParserException {
        List<Node> tokens = new ArrayList<Node>();

        for (int offset = 0; offset < input.length();) {
            int codePoint = input.codePointAt(offset);
            offset += Character.charCount(codePoint);

            TokenType tokenType;
            switch (codePoint) {
                case '+':
                    tokenType = TokenType.T_PLUS;
                    break;
                case '-':
                    tokenType = TokenType.T_MINUS;
                    break;
                case '*':
                    tokenType = TokenType.T_MULT;
                    break;
                case '/':
                    tokenType = TokenType.T_DIV;
                    break;
                case '(':
                    tokenType = TokenType.T_LPAR;
                    break;
                case ')':
                    tokenType = TokenType.T_RPAR;
                    break;
                default:
                    if (!Character.isDigit(codePoint)) {
                        throw new ParserException(
                                "Invalid token: " + new String(Character.toChars(codePoint)));
                    }
                    tokens.add(new Node(
                            TokenType.T_NUM, Integer.valueOf(Character.digit(codePoint, 10))));
                    continue;
            }

            tokens.add(new Node(tokenType, new String(Character.toChars(codePoint))));
        }

        tokens.add(new Node(TokenType.T_END));
        return tokens;
    }

    public static Node match(List<Node> tokens, TokenType token) throws ParserException {
        Node first = tokens.get(0);
        if (first.getTokenType() == token) {
            return tokens.remove(0);
        }
        throw new ParserException(
                "Invalid syntax on token TokenType." + first.getTokenType().name());
    }

    public static Node parseE(List<Node> tokens) throws ParserException {
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

    public static Node parseE2(List<Node> tokens) throws ParserException {
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

    public static Node parseE3(List<Node> tokens) throws ParserException {
        if (tokens.get(0).getTokenType() == TokenType.T_NUM) {
            return tokens.remove(0);
        }

        match(tokens, TokenType.T_LPAR);
        Node expression = parseE(tokens);
        match(tokens, TokenType.T_RPAR);
        return expression;
    }

    public static Node parse(String inputString) throws ParserException {
        List<Node> tokens = lexicalAnalysis(inputString);
        Node ast = parseE(tokens);
        match(tokens, TokenType.T_END);
        return ast;
    }
}
