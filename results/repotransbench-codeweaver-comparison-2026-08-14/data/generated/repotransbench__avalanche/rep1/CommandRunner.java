import java.io.IOException;

public interface CommandRunner {
    int run(String command) throws IOException, InterruptedException;
}
