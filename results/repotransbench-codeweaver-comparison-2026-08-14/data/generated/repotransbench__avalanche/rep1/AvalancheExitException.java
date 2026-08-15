public class AvalancheExitException extends RuntimeException {
    private final int status;

    public AvalancheExitException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int getStatus() {
        return status;
    }
}
