public final class ThreadSleeper implements Sleeper {
    @Override
    public void sleep(int seconds) {
        try {
            Thread.sleep((long) seconds * 1000L);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new AvalancheFatalException("error: sleep interrupted", exception);
        }
    }
}
