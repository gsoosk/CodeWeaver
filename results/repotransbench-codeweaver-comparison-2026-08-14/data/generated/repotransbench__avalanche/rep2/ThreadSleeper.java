import java.util.concurrent.TimeUnit;

public final class ThreadSleeper implements Sleeper {
    @Override
    public void sleepSeconds(int seconds) throws InterruptedException {
        try {
            TimeUnit.SECONDS.sleep(seconds);
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw failure;
        }
    }
}
