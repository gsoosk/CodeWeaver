import java.io.IOException;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.logging.Formatter;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

public final class Avalanche {
    public static final String VERSION = "0.1.0";

    private final RandomSource randomSource;
    private final FaultFactory faultFactory;
    private final CommandRunner commandRunner;
    private final Sleeper sleeper;
    private final Logger logger;
    private final List<Fault> activeFaults;
    private volatile boolean cleanupComplete;

    public Avalanche() {
        this(new JavaRandomSource(Settings.seed));
    }

    private Avalanche(RandomSource randomSource) {
        this(
                randomSource,
                new DefaultFaultFactory(randomSource),
                new ProcessBuilderCommandRunner(),
                new ThreadSleeper(),
                Logger.getLogger("avalanche"));
    }

    Avalanche(
            RandomSource randomSource,
            FaultFactory faultFactory,
            CommandRunner commandRunner,
            Sleeper sleeper,
            Logger logger) {
        this.randomSource = randomSource;
        this.faultFactory = faultFactory;
        this.commandRunner = commandRunner;
        this.sleeper = sleeper;
        this.logger = logger;
        this.activeFaults = new ArrayList<Fault>();
    }

    public static void main(String[] args) {
        Avalanche avalanche = new Avalanche();
        int status;
        try {
            status = avalanche.run(args, System.out, System.err);
        } catch (AvalancheException failure) {
            status = failure.getStatus();
        }

        if (status != 0) {
            System.exit(status);
        }
    }

    int run(String[] args, PrintStream stdout, PrintStream stderr) {
        CliOptions options;
        try {
            options = parseOptions(args);
        } catch (AvalancheException failure) {
            if (failure.getStatus() != 2) {
                throw failure;
            }
            stderr.print(parseErrorText(failure.getMessage()));
            stderr.flush();
            return failure.getStatus();
        }

        if (options.help) {
            stdout.print(helpText());
            stdout.flush();
            return 0;
        }
        if (options.version) {
            stdout.print(VERSION + "\n");
            stdout.flush();
            return 0;
        }

        configureLogger(stderr);
        if (options.debug) {
            Settings.debug = true;
            logger.setLevel(Level.FINE);
        }

        try {
            validateFaultWeights(Settings.faults);
        } catch (AvalancheException failure) {
            logger.severe(failure.getMessage());
            throw failure;
        }

        registerShutdownHook();
        logger.info("Starting Avalanche v" + VERSION);
        logger.info(
                "seed=" + Settings.seed
                        + ",delay=" + Settings.delay
                        + "ms,ports=" + Arrays.toString(Settings.ports));
        runLoop();
        return 0;
    }

    void die(String message) {
        logger.severe(message);
        throw new AvalancheException(message, 1);
    }

    int call(String command, boolean exitOnFail) {
        logger.fine(command);

        int status;
        try {
            status = commandRunner.run(command);
        } catch (IOException failure) {
            throw boundaryFailure(failure);
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw boundaryFailure(failure);
        }

        if (status != 0 && exitOnFail) {
            die("error: subprocess returned " + status + " (not 0)");
        }
        return status;
    }

    static String tc(String iface, String args) {
        return "tc qdisc add dev " + iface + " parent 1:3 handle 30: " + args;
    }

    Optional<Fault> generateFault() {
        return generateFault(Settings.faults);
    }

    Optional<Fault> generateFault(Map<Class<?>, Double> configuredFaults) {
        validateFaultWeights(configuredFaults);
        return selectFault(configuredFaults);
    }

    Optional<Fault> generateFault(List<Class<?>> configuredFaults) {
        if (configuredFaults == null) {
            throw invalidFaultConfiguration(
                    new IllegalArgumentException("fault list must not be null"));
        }
        if (configuredFaults.isEmpty()) {
            throw new ArithmeticException("division by zero");
        }

        double weight = 1.0d / configuredFaults.size();
        Map<Class<?>, Double> uniformlyWeightedFaults =
                new LinkedHashMap<Class<?>, Double>();
        for (Class<?> faultClass : configuredFaults) {
            uniformlyWeightedFaults.put(faultClass, weight);
        }
        return selectFault(uniformlyWeightedFaults);
    }

    @SuppressWarnings("unchecked")
    Optional<Fault> generateFault(Object configuredFaults) {
        if (configuredFaults instanceof List<?>) {
            return generateFault((List<Class<?>>) configuredFaults);
        }
        if (configuredFaults instanceof Map<?, ?>) {
            return generateFault((Map<Class<?>, Double>) configuredFaults);
        }
        throw invalidFaultConfiguration(null);
    }

    static void validateFaultWeights(Map<Class<?>, Double> configuredFaults) {
        if (configuredFaults == null) {
            throw invalidFaultConfiguration(
                    new IllegalArgumentException("fault map must not be null"));
        }

        double total = 0.0d;
        for (Double weight : configuredFaults.values()) {
            if (weight == null) {
                throw invalidFaultConfiguration(
                        new IllegalArgumentException("fault weight must not be null"));
            }
            total += weight;
        }
        if (total != 1.0d) {
            throw new AvalancheException(
                    "fault probabilities don't sum to 1",
                    1);
        }
    }

    private Optional<Fault> selectFault(Map<Class<?>, Double> configuredFaults) {
        double draw = randomSource.nextDouble();
        double cumulativeProbability = 0.0d;
        for (Map.Entry<Class<?>, Double> entry : configuredFaults.entrySet()) {
            cumulativeProbability += Settings.p_fault * entry.getValue();
            if (cumulativeProbability >= draw) {
                return Optional.of(faultFactory.create(entry.getKey()));
            }
        }
        return Optional.empty();
    }

    private static AvalancheException invalidFaultConfiguration(Throwable cause) {
        if (cause == null) {
            return new AvalancheException("can't parse faults", 1);
        }
        return new AvalancheException("can't parse faults", 1, cause);
    }

    void clearFaults() {
        if (Settings.debug) {
            return;
        }

        for (String iface : Settings.interfaces) {
            call("tc qdisc del dev " + iface + " root", false);
        }
    }

    void installFault(Fault fault) {
        if (Settings.debug) {
            return;
        }

        for (String iface : Settings.interfaces) {
            call("tc qdisc add dev " + iface + " root handle 1: prio", true);
            call(tc(iface, fault.action()), true);
            for (int port : Settings.ports) {
                call(
                        "tc filter add dev " + iface
                                + " parent 1:0 protocol ip u32 match ip dport "
                                + port + " 0xffff flowid 1:3",
                        true);
                call(
                        "tc filter add dev " + iface
                                + " parent 1:0 protocol ip u32 match ip sport "
                                + port + " 0xffff flowid 1:3",
                        true);
            }
        }
    }

    void runCycle() {
        if (!activeFaults.isEmpty()) {
            clearFaults();
            activeFaults.clear();
        }

        Optional<Fault> selectedFault = generateFault();
        if (selectedFault.isPresent()) {
            Fault fault = selectedFault.get();
            activeFaults.add(fault);
            logger.info("fault: " + fault.desc());
            installFault(fault);
        } else {
            logger.info("fault: none");
        }

        try {
            sleeper.sleepSeconds(Settings.delay);
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw boundaryFailure(failure);
        }
    }

    void runLoop() {
        try {
            while (true) {
                runCycle();
            }
        } finally {
            boolean interrupted = Thread.interrupted();
            try {
                cleanup();
            } finally {
                if (interrupted) {
                    Thread.currentThread().interrupt();
                }
            }
        }
    }

    synchronized void cleanup() {
        if (cleanupComplete) {
            return;
        }
        cleanupComplete = true;

        try {
            if (!activeFaults.isEmpty()) {
                logger.info("Cleaning up...");
                try {
                    clearFaults();
                } finally {
                    activeFaults.clear();
                }
            }
        } finally {
            logger.info("Exiting.");
        }
    }

    List<Fault> activeFaults() {
        return Collections.unmodifiableList(activeFaults);
    }

    boolean isCleanupComplete() {
        return cleanupComplete;
    }

    private static AvalancheException boundaryFailure(Exception cause) {
        String message = cause.getMessage();
        if (message == null || message.isEmpty()) {
            message = cause.getClass().getSimpleName();
        }
        return new AvalancheException(message, 1, cause);
    }

    static CliOptions parseOptions(String[] args) {
        boolean debug = false;
        boolean version = false;
        List<String> positionalArguments = new ArrayList<String>();
        boolean parseOptions = true;

        for (String argument : args) {
            if (!parseOptions) {
                positionalArguments.add(argument);
                continue;
            }
            if ("--".equals(argument)) {
                parseOptions = false;
                continue;
            }
            if (argument.startsWith("--") && argument.length() > 2) {
                int equalsIndex = argument.indexOf('=');
                String candidate = equalsIndex < 0
                        ? argument
                        : argument.substring(0, equalsIndex);
                String option = resolveLongOption(candidate);
                if (option == null) {
                    throw optionError("no such option: " + candidate);
                }
                if (equalsIndex >= 0) {
                    throw optionError(option + " option does not take a value");
                }
                if ("--help".equals(option)) {
                    return new CliOptions(
                            debug,
                            version,
                            true,
                            positionalArguments);
                }
                if ("--debug".equals(option)) {
                    debug = true;
                } else {
                    version = true;
                }
                continue;
            }
            if (argument.startsWith("-") && argument.length() > 1) {
                for (int index = 1; index < argument.length(); index++) {
                    char option = argument.charAt(index);
                    if (option == 'h') {
                        return new CliOptions(
                                debug,
                                version,
                                true,
                                positionalArguments);
                    }
                    if (option == 'd') {
                        debug = true;
                    } else if (option == 'v') {
                        version = true;
                    } else {
                        throw optionError("no such option: -" + option);
                    }
                }
                continue;
            }
            positionalArguments.add(argument);
        }

        return new CliOptions(
                debug,
                version,
                false,
                positionalArguments);
    }

    static String helpText() {
        return "Usage: avalanche [options]\n"
                + "\n"
                + "Options:\n"
                + "  -h, --help     show this help message and exit\n"
                + "  -d, --debug    log the faults, but do not inject them\n"
                + "  -v, --version  print the avalanche version and exit\n";
    }

    private void configureLogger(PrintStream stderr) {
        logger.setUseParentHandlers(false);
        for (Handler handler : logger.getHandlers()) {
            logger.removeHandler(handler);
            handler.flush();
        }

        Handler handler = new PrintStreamHandler(stderr);
        handler.setLevel(Level.ALL);
        logger.addHandler(handler);
        logger.setLevel(Settings.log_level);
    }

    private void registerShutdownHook() {
        Runtime.getRuntime().addShutdownHook(
                new Thread(
                        new Runnable() {
                            @Override
                            public void run() {
                                cleanup();
                            }
                        },
                        "avalanche-cleanup"));
    }

    private static AvalancheException optionError(String message) {
        return new AvalancheException(message, 2);
    }

    private static String parseErrorText(String message) {
        return "Usage: avalanche [options]\n"
                + "\n"
                + "avalanche: error: " + message + "\n";
    }

    private static String resolveLongOption(String candidate) {
        String[] options = new String[]{"--help", "--debug", "--version"};
        String match = null;
        for (String option : options) {
            if (option.equals(candidate)) {
                return option;
            }
            if (option.startsWith(candidate)) {
                match = option;
            }
        }
        return match;
    }

    private static final class MessageOnlyFormatter extends Formatter {
        @Override
        public String format(LogRecord record) {
            return formatMessage(record) + "\n";
        }
    }

    private static final class PrintStreamHandler extends Handler {
        private final PrintStream stream;

        PrintStreamHandler(PrintStream stream) {
            this.stream = stream;
            setFormatter(new MessageOnlyFormatter());
        }

        @Override
        public synchronized void publish(LogRecord record) {
            if (!isLoggable(record)) {
                return;
            }
            stream.print(getFormatter().format(record));
            stream.flush();
        }

        @Override
        public void flush() {
            stream.flush();
        }

        @Override
        public void close() {
            flush();
        }
    }

    static final class CliOptions {
        final boolean debug;
        final boolean version;
        final boolean help;
        final List<String> positionalArguments;

        CliOptions(
                boolean debug,
                boolean version,
                boolean help,
                List<String> positionalArguments) {
            this.debug = debug;
            this.version = version;
            this.help = help;
            this.positionalArguments = positionalArguments;
        }
    }
}
