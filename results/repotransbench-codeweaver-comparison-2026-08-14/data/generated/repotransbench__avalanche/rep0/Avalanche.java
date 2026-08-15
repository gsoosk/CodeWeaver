import java.io.PrintStream;
import java.lang.reflect.Constructor;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.logging.ConsoleHandler;
import java.util.logging.Formatter;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

public final class Avalanche {
    public static final String VERSION = "0.1.0";

    private static final String PROGRAM_NAME = "avalanche";
    private static final String LINE_SEPARATOR = System.lineSeparator();
    private static final Formatter MESSAGE_ONLY_FORMATTER = new Formatter() {
        @Override
        public String format(LogRecord record) {
            return formatMessage(record) + LINE_SEPARATOR;
        }
    };

    private final CommandRunner commandRunner;
    private final Sleeper sleeper;
    private RandomSource randomSource;
    private final Logger logger;
    private final ShutdownHookRegistrar shutdownHookRegistrar;
    private final boolean seedFromSettingsAtStartup;

    public Avalanche() {
        this(
                new ShellCommandRunner(),
                new ThreadSleeper(),
                null,
                Logger.getLogger("avalanche"),
                cleanup -> Runtime.getRuntime().addShutdownHook(
                        new Thread(cleanup, "avalanche-cleanup")),
                true);
    }

    public Avalanche(
            CommandRunner commandRunner,
            Sleeper sleeper,
            RandomSource randomSource,
            Logger logger) {
        this(
                commandRunner,
                sleeper,
                randomSource,
                logger,
                cleanup -> Runtime.getRuntime().addShutdownHook(
                        new Thread(cleanup, "avalanche-cleanup")));
    }

    Avalanche(
            CommandRunner commandRunner,
            Sleeper sleeper,
            RandomSource randomSource,
            Logger logger,
            ShutdownHookRegistrar shutdownHookRegistrar) {
        this(
                commandRunner,
                sleeper,
                randomSource,
                logger,
                shutdownHookRegistrar,
                false);
    }

    private Avalanche(
            CommandRunner commandRunner,
            Sleeper sleeper,
            RandomSource randomSource,
            Logger logger,
            ShutdownHookRegistrar shutdownHookRegistrar,
            boolean seedFromSettingsAtStartup) {
        this.commandRunner = commandRunner;
        this.sleeper = sleeper;
        this.randomSource = randomSource;
        this.logger = logger;
        this.shutdownHookRegistrar = shutdownHookRegistrar;
        this.seedFromSettingsAtStartup = seedFromSettingsAtStartup;
    }

    public void die(String message) {
        logger.severe(message);
        throw new AvalancheFatalException(message);
    }

    public void call(String command) {
        call(command, true);
    }

    public void call(String command, boolean exitOnFail) {
        logger.fine(command);
        int status = commandRunner.run(command);
        if (status != 0 && exitOnFail) {
            die("error: subprocess returned " + status + " (not 0)");
        }
    }

    public static String tc(String iface, String args) {
        return "tc qdisc add dev " + iface + " parent 1:3 handle 30: " + args;
    }

    public Optional<Fault> generate_fault() {
        ParsedFaultConfiguration faults = requireFaultConfiguration();
        double threshold = randomSource().nextDouble();
        double cumulative = 0.0;

        for (WeightedFault configuredFault : faults.entries) {
            cumulative += Settings.p_fault * configuredFault.weight;
            if (cumulative >= threshold) {
                return Optional.of(constructFault(configuredFault.faultClass));
            }
        }

        return Optional.empty();
    }

    public void clear_faults() {
        if (Settings.debug) {
            return;
        }

        for (String iface : Settings.interfaces) {
            call("tc qdisc del dev " + iface + " root", false);
        }
    }

    public void cleanup(List<Fault> activeFaults) {
        if (!activeFaults.isEmpty()) {
            logger.info("Cleaning up...");
            clear_faults();
        }
        logger.info("Exiting.");
    }

    public void applyFault(Fault fault) {
        if (Settings.debug) {
            return;
        }

        for (String iface : Settings.interfaces) {
            call("tc qdisc add dev " + iface + " root handle 1: prio");
            call(tc(iface, fault.action()));
            for (int port : Settings.ports) {
                call("tc filter add dev " + iface
                        + " parent 1:0 protocol ip u32 match ip dport " + port
                        + " 0xffff flowid 1:3");
                call("tc filter add dev " + iface
                        + " parent 1:0 protocol ip u32 match ip sport " + port
                        + " 0xffff flowid 1:3");
            }
        }
    }

    public void runIteration(List<Fault> activeFaults) {
        if (!activeFaults.isEmpty()) {
            clear_faults();
            activeFaults.clear();
        }

        Optional<Fault> selectedFault = generate_fault();
        if (selectedFault.isPresent()) {
            Fault fault = selectedFault.get();
            activeFaults.add(fault);
            logger.info("fault: " + fault.desc());
            if (!Settings.debug) {
                applyFault(fault);
            }
        } else {
            logger.info("fault: none");
        }

        sleeper.sleep(Settings.delay);
    }

    public void runForever(List<Fault> activeFaults) {
        while (true) {
            runIteration(activeFaults);
        }
    }

    public void validateFaultProbabilities() {
        ParsedFaultConfiguration faults = requireFaultConfiguration();
        double total = 0.0;
        if (faults.uniformList && !faults.entries.isEmpty()) {
            total = 1.0;
        } else {
            for (WeightedFault configuredFault : faults.entries) {
                total += configuredFault.weight;
            }
        }

        if (total != 1.0) {
            die("fault probabilities don't sum to 1");
        }
    }

    public int runCli(String[] args, PrintStream stdout, PrintStream stderr) {
        CliOptions options = parseOptions(args, stdout, stderr);
        if (options.exitStatus != null) {
            return options.exitStatus.intValue();
        }

        if (options.version) {
            stdout.println(VERSION);
            return 0;
        }

        configureLogging(stderr, options.debug);
        validateFaultProbabilities();

        List<Fault> activeFaults =
                Collections.synchronizedList(new ArrayList<Fault>());
        shutdownHookRegistrar.register(() -> cleanup(activeFaults));

        logger.info("Starting Avalanche v" + VERSION);
        logger.info(
                "seed=" + Settings.seed
                        + ",delay=" + Settings.delay
                        + "ms,ports=" + Arrays.toString(Settings.ports));

        if (seedFromSettingsAtStartup) {
            randomSource = new JavaRandomSource(Settings.seed);
        }
        runForever(activeFaults);
        return 0;
    }

    public static void main(String[] args) {
        int status;
        try {
            status = new Avalanche().runCli(args, System.out, System.err);
        } catch (AvalancheFatalException failure) {
            status = failure.getStatus();
        }

        if (status != 0) {
            System.exit(status);
        }
    }

    void configureLogging(PrintStream stderr, boolean debug) {
        logger.setUseParentHandlers(false);
        for (Handler handler : logger.getHandlers()) {
            if (handler instanceof MessageOnlyConsoleHandler) {
                logger.removeHandler(handler);
                handler.close();
            }
        }

        MessageOnlyConsoleHandler handler = new MessageOnlyConsoleHandler(stderr);
        handler.setLevel(Level.ALL);
        handler.setFormatter(MESSAGE_ONLY_FORMATTER);
        logger.addHandler(handler);

        logger.setLevel(Settings.log_level);
        if (debug) {
            Settings.debug = true;
            logger.setLevel(Level.FINE);
        }
    }

    private ParsedFaultConfiguration requireFaultConfiguration() {
        Object configuredFaults = Settings.faults;
        if (configuredFaults instanceof List<?>) {
            List<?> configuredList = (List<?>) configuredFaults;
            double weight =
                    configuredList.isEmpty() ? 0.0 : 1.0 / configuredList.size();
            Map<Class<? extends Fault>, Double> normalized =
                    new LinkedHashMap<Class<? extends Fault>, Double>();
            for (Object configuredClass : configuredList) {
                normalized.put(requireFaultClass(configuredClass), weight);
            }

            List<WeightedFault> weighted =
                    new ArrayList<WeightedFault>(normalized.size());
            for (Map.Entry<Class<? extends Fault>, Double> entry
                    : normalized.entrySet()) {
                weighted.add(new WeightedFault(entry.getKey(), entry.getValue()));
            }
            return new ParsedFaultConfiguration(weighted, true);
        }

        if (configuredFaults instanceof Map<?, ?>) {
            Map<?, ?> configuredMap = (Map<?, ?>) configuredFaults;
            List<WeightedFault> weighted =
                    new ArrayList<WeightedFault>(configuredMap.size());
            for (Map.Entry<?, ?> entry : configuredMap.entrySet()) {
                Object weight = entry.getValue();
                if (!(weight instanceof Number)) {
                    die("can't parse faults");
                }
                weighted.add(
                        new WeightedFault(
                                requireFaultClass(entry.getKey()),
                                ((Number) weight).doubleValue()));
            }
            return new ParsedFaultConfiguration(weighted, false);
        }

        die("can't parse faults");
        throw new AssertionError("die must throw");
    }

    private Class<? extends Fault> requireFaultClass(Object configuredClass) {
        if (!(configuredClass instanceof Class)
                || !Fault.class.isAssignableFrom((Class<?>) configuredClass)) {
            die("can't parse faults");
        }

        Class<? extends Fault> faultClass =
                ((Class<?>) configuredClass).asSubclass(Fault.class);
        return faultClass;
    }

    private Fault constructFault(Class<? extends Fault> faultClass) {
        if (faultClass == Partition.class) {
            return new Partition();
        }
        if (faultClass == PacketLoss.class) {
            return new PacketLoss(randomSource());
        }
        if (faultClass == Latency.class) {
            return new Latency(randomSource());
        }
        if (faultClass == Reorder.class) {
            return new Reorder(randomSource());
        }

        try {
            Constructor<? extends Fault> constructor =
                    faultClass.getDeclaredConstructor();
            if (!constructor.isAccessible()) {
                constructor.setAccessible(true);
            }
            return constructor.newInstance();
        } catch (ReflectiveOperationException | SecurityException failure) {
            String message = "can't construct fault class: " + faultClass.getName();
            logger.severe(message);
            throw new AvalancheFatalException(message, failure);
        }
    }

    private RandomSource randomSource() {
        if (randomSource == null) {
            if (!seedFromSettingsAtStartup) {
                throw new IllegalStateException("random source must not be null");
            }
            randomSource = new JavaRandomSource(Settings.seed);
        }
        return randomSource;
    }

    private static CliOptions parseOptions(
            String[] args, PrintStream stdout, PrintStream stderr) {
        CliOptions options = new CliOptions();
        boolean optionsEnded = false;

        for (String argument : args) {
            if (optionsEnded || "-".equals(argument) || !argument.startsWith("-")) {
                continue;
            }
            if ("--".equals(argument)) {
                optionsEnded = true;
                continue;
            }
            if (argument.startsWith("--")) {
                String option = argument;
                String value = null;
                int equalsIndex = argument.indexOf('=');
                if (equalsIndex >= 0) {
                    option = argument.substring(0, equalsIndex);
                    value = argument.substring(equalsIndex + 1);
                }

                String canonicalOption = resolveLongOption(option);
                if (canonicalOption == null) {
                    printOptionError(stderr, "no such option: " + option);
                    options.exitStatus = Integer.valueOf(2);
                    return options;
                }
                if (value != null) {
                    printOptionError(
                            stderr, canonicalOption + " option does not take a value");
                    options.exitStatus = Integer.valueOf(2);
                    return options;
                }
                if ("--help".equals(canonicalOption)) {
                    printHelp(stdout);
                    options.exitStatus = Integer.valueOf(0);
                    return options;
                }
                if ("--debug".equals(canonicalOption)) {
                    options.debug = true;
                } else {
                    options.version = true;
                }
                continue;
            }

            for (int index = 1; index < argument.length(); index++) {
                char option = argument.charAt(index);
                if (option == 'h') {
                    printHelp(stdout);
                    options.exitStatus = Integer.valueOf(0);
                    return options;
                }
                if (option == 'd') {
                    options.debug = true;
                } else if (option == 'v') {
                    options.version = true;
                } else {
                    printOptionError(stderr, "no such option: -" + option);
                    options.exitStatus = Integer.valueOf(2);
                    return options;
                }
            }
        }

        return options;
    }

    private static String resolveLongOption(String option) {
        String[] supported = new String[] {"--debug", "--version", "--help"};
        String match = null;
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

    private static void printHelp(PrintStream stdout) {
        stdout.print("Usage: " + PROGRAM_NAME + " [options]" + LINE_SEPARATOR);
        stdout.print(LINE_SEPARATOR);
        stdout.print("Options:" + LINE_SEPARATOR);
        stdout.print("  -h, --help     show this help message and exit" + LINE_SEPARATOR);
        stdout.print("  -d, --debug    log the faults, but do not inject them" + LINE_SEPARATOR);
        stdout.print("  -v, --version  print the avalanche version and exit" + LINE_SEPARATOR);
    }

    private static void printOptionError(PrintStream stderr, String message) {
        stderr.print("Usage: " + PROGRAM_NAME + " [options]" + LINE_SEPARATOR);
        stderr.print(LINE_SEPARATOR);
        stderr.print(PROGRAM_NAME + ": error: " + message + LINE_SEPARATOR);
    }

    private static final class CliOptions {
        private boolean debug;
        private boolean version;
        private Integer exitStatus;
    }

    private static final class WeightedFault {
        private final Class<? extends Fault> faultClass;
        private final double weight;

        WeightedFault(Class<? extends Fault> faultClass, double weight) {
            this.faultClass = faultClass;
            this.weight = weight;
        }
    }

    private static final class ParsedFaultConfiguration {
        private final List<WeightedFault> entries;
        private final boolean uniformList;

        ParsedFaultConfiguration(List<WeightedFault> entries, boolean uniformList) {
            this.entries = entries;
            this.uniformList = uniformList;
        }
    }

    private static final class MessageOnlyConsoleHandler extends ConsoleHandler {
        private final PrintStream stderr;

        MessageOnlyConsoleHandler(PrintStream stderr) {
            this.stderr = stderr;
        }

        @Override
        public synchronized void publish(LogRecord record) {
            if (!isLoggable(record)) {
                return;
            }
            stderr.print(getFormatter().format(record));
            flush();
        }

        @Override
        public synchronized void flush() {
            stderr.flush();
        }

        @Override
        public synchronized void close() {
            flush();
        }
    }
}

interface ShutdownHookRegistrar {
    void register(Runnable cleanup);
}
