import java.io.IOException;
import java.io.PrintStream;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import java.util.logging.ConsoleHandler;
import java.util.logging.Formatter;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

public class Avalanche {
    public static final String VERSION = "0.1.0";

    private final RandomSource randomSource;
    private final FaultFactory faultFactory;
    private final CommandRunner commandRunner;
    private final Sleeper sleeper;
    private final Logger logger;
    private final AtomicReference<Fault> activeFault;

    public Avalanche(
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
        this.activeFault = new AtomicReference<Fault>();
    }

    public static void main(String[] args)
            throws IOException, InterruptedException {
        Avalanche avalanche = new Avalanche(
                new JavaRandomSource(Settings.seed),
                new FaultFactory(),
                new ShellCommandRunner(),
                new ThreadSleeper(),
                Logger.getLogger("avalanche"));
        try {
            int status = avalanche.run(args, System.out);
            if (status != 0) {
                System.exit(status);
            }
        } catch (AvalancheExitException exit) {
            System.exit(exit.getStatus());
        }
    }

    public int run(String[] args, PrintStream standardOutput)
            throws IOException, InterruptedException {
        if (args == null) {
            throw new IllegalArgumentException("args must not be null");
        }
        if (standardOutput == null) {
            throw new IllegalArgumentException(
                    "standard output must not be null");
        }

        ParsedOptions options = parseOptions(args, standardOutput);
        if (options.status != 0 || options.help) {
            return options.status;
        }
        if (options.version) {
            standardOutput.println(VERSION);
            return 0;
        }

        configureLogger(logger, Settings.log_level);
        if (options.debug) {
            Settings.debug = true;
            logger.setLevel(Level.FINE);
        }

        try {
            validateFaultWeights(Settings.faults);
        } catch (IllegalArgumentException failure) {
            die(failure.getMessage());
        }

        registerShutdownHook();
        logger.info("Starting Avalanche v" + VERSION);
        logger.info("seed=" + Settings.seed
                + ",delay=" + Settings.delay
                + "ms,ports=" + Arrays.toString(Settings.ports));
        runLoop();
        return 0;
    }

    public static void configureLogger(Logger logger, Level level) {
        if (logger == null) {
            throw new IllegalArgumentException("logger must not be null");
        }
        if (level == null) {
            throw new IllegalArgumentException("level must not be null");
        }

        logger.setUseParentHandlers(false);
        for (Handler handler : logger.getHandlers()) {
            logger.removeHandler(handler);
            handler.close();
        }

        ConsoleHandler handler = new ConsoleHandler();
        handler.setLevel(Level.ALL);
        handler.setFormatter(new Formatter() {
            @Override
            public String format(LogRecord record) {
                return formatMessage(record) + "\n";
            }
        });
        logger.addHandler(handler);
        logger.setLevel(level);
    }

    protected void registerShutdownHook() {
        Runtime.getRuntime().addShutdownHook(
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            cleanup();
                        } catch (IOException failure) {
                            throw new IllegalStateException(
                                    "failed to clean up network faults",
                                    failure);
                        } catch (InterruptedException interruption) {
                            Thread.currentThread().interrupt();
                            throw new IllegalStateException(
                                    "network fault cleanup was interrupted",
                                    interruption);
                        }
                    }
                }, "avalanche-cleanup"));
    }

    public void die(String message) {
        logger.severe(message);
        throw new AvalancheExitException(1, message);
    }

    public void call(String command)
            throws IOException, InterruptedException {
        call(command, true);
    }

    public void call(String command, boolean exitOnFail)
            throws IOException, InterruptedException {
        logger.fine(command);

        final int status;
        try {
            status = commandRunner.run(command);
        } catch (InterruptedException interruption) {
            Thread.currentThread().interrupt();
            throw interruption;
        }

        if (status != 0 && exitOnFail) {
            die("error: subprocess returned " + status + " (not 0)");
        }
    }

    public static String tc(String iface, String args) {
        return "tc qdisc add dev " + iface
                + " parent 1:3 handle 30: " + args;
    }

    public Optional<Fault> generateFault() {
        return generateFault(Settings.faults, Settings.p_fault);
    }

    public Optional<Fault> generateFault(
            Map<Class<?>, Double> faults,
            double faultProbability) {
        validateConfiguration(faults);

        double draw = randomSource.nextDouble();
        double cumulativeProbability = 0.0;
        for (Map.Entry<Class<?>, Double> entry : faults.entrySet()) {
            cumulativeProbability += faultProbability * entry.getValue();
            if (cumulativeProbability >= draw) {
                return Optional.of(
                        faultFactory.create(entry.getKey(), randomSource));
            }
        }
        return Optional.empty();
    }

    public Optional<Fault> generateFault(
            List<Class<?>> faults,
            double faultProbability) {
        if (faults == null) {
            throw new IllegalArgumentException("faults must not be null");
        }

        Map<Class<?>, Double> normalized =
                new LinkedHashMap<Class<?>, Double>();
        for (Class<?> faultClass : faults) {
            if (faultClass == null) {
                throw new IllegalArgumentException(
                        "fault class must not be null");
            }
            normalized.put(faultClass, 1.0 / faults.size());
        }
        return generateFault(normalized, faultProbability);
    }

    public Optional<Fault> generateFault(
            Object faults,
            double faultProbability) {
        if (faults == null) {
            throw new IllegalArgumentException("faults must not be null");
        }
        if (faults instanceof Map<?, ?>) {
            return generateFault(asFaultMap((Map<?, ?>) faults),
                    faultProbability);
        }
        if (faults instanceof List<?>) {
            return generateFault(asFaultList((List<?>) faults),
                    faultProbability);
        }
        throw new IllegalArgumentException("can't parse faults");
    }

    public static void validateFaultWeights(Map<Class<?>, Double> faults) {
        validateConfiguration(faults);

        double total = 0.0;
        for (Double probability : faults.values()) {
            total += probability;
        }
        if (Double.compare(total, 1.0) != 0) {
            throw new IllegalArgumentException(
                    "fault probabilities don't sum to 1");
        }
    }

    public void clearFaults() throws IOException, InterruptedException {
        if (Settings.debug) {
            return;
        }
        for (String iface : Settings.interfaces) {
            call("tc qdisc del dev " + iface + " root", false);
        }
    }

    public void applyFault(Fault fault)
            throws IOException, InterruptedException {
        if (Settings.debug) {
            return;
        }
        for (String iface : Settings.interfaces) {
            call("tc qdisc add dev " + iface + " root handle 1: prio");
            call(tc(iface, fault.action()));
            for (int port : Settings.ports) {
                call("tc filter add dev " + iface
                        + " parent 1:0 protocol ip u32 match ip dport "
                        + port + " 0xffff flowid 1:3");
                call("tc filter add dev " + iface
                        + " parent 1:0 protocol ip u32 match ip sport "
                        + port + " 0xffff flowid 1:3");
            }
        }
    }

    public void runIteration() throws IOException, InterruptedException {
        if (activeFault.get() != null) {
            clearFaults();
            activeFault.set(null);
        }

        Optional<Fault> selectedFault = generateFault();
        if (selectedFault.isPresent()) {
            Fault fault = selectedFault.get();
            activeFault.set(fault);
            logger.info("fault: " + fault.desc());
            applyFault(fault);
        } else {
            logger.info("fault: none");
        }

        sleeper.sleep(Settings.delay * 1000L);
    }

    public void runLoop() throws IOException, InterruptedException {
        try {
            while (true) {
                runIteration();
            }
        } catch (InterruptedException interruption) {
            Thread.currentThread().interrupt();
            throw interruption;
        }
    }

    public void cleanup() throws IOException, InterruptedException {
        Fault fault = activeFault.get();
        if (fault == null) {
            cleanup(Collections.<Fault>emptyList());
        } else {
            cleanup(Collections.singletonList(fault));
        }
    }

    public void cleanup(List<? extends Fault> activeFaults)
            throws IOException, InterruptedException {
        if (activeFaults == null) {
            throw new IllegalArgumentException(
                    "active faults must not be null");
        }
        if (!activeFaults.isEmpty()) {
            logger.info("Cleaning up...");
            clearFaults();
        }
        logger.info("Exiting.");
    }

    public Optional<Fault> getActiveFault() {
        return Optional.ofNullable(activeFault.get());
    }

    private static void validateConfiguration(
            Map<Class<?>, Double> faults) {
        if (faults == null) {
            throw new IllegalArgumentException("faults must not be null");
        }
        for (Map.Entry<Class<?>, Double> entry : faults.entrySet()) {
            if (entry.getKey() == null) {
                throw new IllegalArgumentException(
                        "fault class must not be null");
            }
            if (entry.getValue() == null) {
                throw new IllegalArgumentException(
                        "fault probability must not be null");
            }
        }
    }

    private static Map<Class<?>, Double> asFaultMap(Map<?, ?> faults) {
        Map<Class<?>, Double> typed =
                new LinkedHashMap<Class<?>, Double>();
        for (Map.Entry<?, ?> entry : faults.entrySet()) {
            if (!(entry.getKey() instanceof Class<?>)) {
                throw new IllegalArgumentException(
                        "fault map keys must be classes");
            }
            if (!(entry.getValue() instanceof Double)) {
                throw new IllegalArgumentException(
                        "fault map values must be doubles");
            }
            typed.put((Class<?>) entry.getKey(), (Double) entry.getValue());
        }
        return typed;
    }

    private static List<Class<?>> asFaultList(List<?> faults) {
        java.util.ArrayList<Class<?>> typed =
                new java.util.ArrayList<Class<?>>(faults.size());
        for (Object faultClass : faults) {
            if (!(faultClass instanceof Class<?>)) {
                throw new IllegalArgumentException(
                        "fault list values must be classes");
            }
            typed.add((Class<?>) faultClass);
        }
        return typed;
    }

    private static ParsedOptions parseOptions(
            String[] args,
            PrintStream standardOutput) {
        boolean debug = false;
        boolean version = false;
        boolean parseOptions = true;

        for (String argument : args) {
            if (!parseOptions || !argument.startsWith("-")
                    || "-".equals(argument)) {
                continue;
            }
            if ("--".equals(argument)) {
                parseOptions = false;
                continue;
            }
            if (argument.startsWith("--")) {
                String option = argument.substring(2);
                int equals = option.indexOf('=');
                String value = null;
                if (equals >= 0) {
                    value = option.substring(equals + 1);
                    option = option.substring(0, equals);
                }

                String resolved = resolveLongOption(option);
                if (resolved == null) {
                    return optionError(
                            "no such option: --" + option);
                }
                if (value != null) {
                    return optionError(
                            "--" + resolved
                                    + " option does not take a value");
                }
                if ("help".equals(resolved)) {
                    standardOutput.print(helpText());
                    return ParsedOptions.help();
                }
                if ("debug".equals(resolved)) {
                    debug = true;
                } else {
                    version = true;
                }
                continue;
            }

            for (int index = 1; index < argument.length(); index++) {
                char option = argument.charAt(index);
                if (option == 'h') {
                    standardOutput.print(helpText());
                    return ParsedOptions.help();
                }
                if (option == 'd') {
                    debug = true;
                } else if (option == 'v') {
                    version = true;
                } else {
                    return optionError(
                            "no such option: -" + option);
                }
            }
        }
        return new ParsedOptions(debug, version, false, 0);
    }

    private static String resolveLongOption(String option) {
        String match = null;
        String[] supported = {"help", "debug", "version"};
        for (String candidate : supported) {
            if (candidate.startsWith(option)) {
                if (match != null) {
                    return null;
                }
                match = candidate;
            }
        }
        return match;
    }

    private static ParsedOptions optionError(String message) {
        System.err.print("Usage: avalanche [options]\n\n"
                + "avalanche: error: " + message + "\n");
        return new ParsedOptions(false, false, false, 2);
    }

    private static String helpText() {
        return "Usage: avalanche [options]\n"
                + "\n"
                + "Options:\n"
                + "  -h, --help     show this help message and exit\n"
                + "  -d, --debug    log the faults, but do not inject them\n"
                + "  -v, --version  print the avalanche version and exit\n";
    }

    private static final class ParsedOptions {
        private final boolean debug;
        private final boolean version;
        private final boolean help;
        private final int status;

        private ParsedOptions(
                boolean debug,
                boolean version,
                boolean help,
                int status) {
            this.debug = debug;
            this.version = version;
            this.help = help;
            this.status = status;
        }

        private static ParsedOptions help() {
            return new ParsedOptions(false, false, true, 0);
        }
    }
}
