public final class AvalancheFatalException extends RuntimeException {
    private final int status;

    public AvalancheFatalException(String message) {
        this(message, 1, null);
    }

    public AvalancheFatalException(String message, Throwable cause) {
        this(message, 1, cause);
    }

    public AvalancheFatalException(String message, int status, Throwable cause) {
        super(message, cause);
        this.status = status;
    }

    public int getStatus() {
        return status;
    }
}
