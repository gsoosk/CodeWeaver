import java.util.ArrayList;
import java.util.List;

public class Node {
    private TokenType tokenType;
    private Object value;
    private List<Node> children;
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

    public void setTokenType(TokenType tokenType) {
        this.tokenType = tokenType;
    }

    public Object getValue() {
        return value;
    }

    public void setValue(Object value) {
        this.value = value;
    }

    public List<Node> getChildren() {
        return children;
    }

    public void setChildren(List<Node> children) {
        this.children = children;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }
}
