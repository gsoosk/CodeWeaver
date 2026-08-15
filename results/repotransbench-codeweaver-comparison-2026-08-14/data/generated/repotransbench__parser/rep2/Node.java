import java.util.ArrayList;
import java.util.List;

public class Node {
    private final TokenType tokenType;
    private final Object value;
    private final List<Node> children;
    private Integer id;

    public Node(TokenType tokenType) {
        this(tokenType, null);
    }

    public Node(TokenType tokenType, Object value) {
        this.tokenType = tokenType;
        this.value = value;
        this.children = new ArrayList<Node>();
    }

    public TokenType getTokenType() {
        return tokenType;
    }

    public Object getValue() {
        return value;
    }

    public List<Node> getChildren() {
        return children;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }
}
