public enum TokenType {
    T_NUM(0),
    T_PLUS(1),
    T_MINUS(2),
    T_MULT(3),
    T_DIV(4),
    T_LPAR(5),
    T_RPAR(6),
    T_END(7);

    private final int value;

    TokenType(int value) {
        this.value = value;
    }

    public int getValue() {
        return value;
    }
}
