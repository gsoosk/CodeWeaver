import java.io.IOException;

public final class ProcessBuilderCommandRunner implements CommandRunner {
    @Override
    public int run(String command) throws IOException, InterruptedException {
        ProcessBuilder processBuilder = new ProcessBuilder("/bin/sh", "-c", command);
        processBuilder.redirectErrorStream(true);
        processBuilder.inheritIO();
        return processBuilder.start().waitFor();
    }
}
