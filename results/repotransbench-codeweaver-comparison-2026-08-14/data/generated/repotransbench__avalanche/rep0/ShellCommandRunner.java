import java.io.IOException;

public final class ShellCommandRunner implements CommandRunner {
    @Override
    public int run(String command) {
        Process process;
        try {
            process = new ProcessBuilder("/bin/sh", "-c", command)
                    .redirectErrorStream(true)
                    .redirectOutput(ProcessBuilder.Redirect.INHERIT)
                    .start();
        } catch (IOException exception) {
            throw new AvalancheFatalException("error: failed to start subprocess", exception);
        }

        try {
            return process.waitFor();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new AvalancheFatalException(
                    "error: interrupted while waiting for subprocess", exception);
        }
    }
}
