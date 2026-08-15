public final class AvalancheException extends RuntimeException {
    private final int status;

    public AvalancheException(String message, int status) {
        super(message);
        this.status = status;
    }

    public AvalancheException(String message, int status, Throwable cause) {
        super(message, cause);
        this.status = status;
    }

    public int getStatus() {
        return status;
    }
}
