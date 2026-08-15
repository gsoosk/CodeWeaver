import java.io.PrintStream;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.EnumMap;
import java.util.Map;
import java.util.function.DoubleBinaryOperator;

public final class Compute {
    private static final BigInteger TWO_POW_52 = BigInteger.ONE.shiftLeft(52);
    private static final BigInteger TWO_POW_53 = BigInteger.ONE.shiftLeft(53);
    private static final BigInteger TWO_POW_1075 = BigInteger.ONE.shiftLeft(1075);
    private static final long FRACTION_MASK = 0x000fffffffffffffL;
    private static final long MAX_FINITE_MAGNITUDE_BITS = 0x7fefffffffffffffL;
    private static final String FLOAT_OVERFLOW_MESSAGE =
            "integer division result too large for a float";
    private static final Map<TokenType, DoubleBinaryOperator> OPERATIONS =
            new EnumMap<TokenType, DoubleBinaryOperator>(TokenType.class);

    static {
        OPERATIONS.put(TokenType.T_PLUS, (left, right) -> left + right);
        OPERATIONS.put(TokenType.T_MINUS, (left, right) -> left - right);
        OPERATIONS.put(TokenType.T_MULT, (left, right) -> left * right);
        OPERATIONS.put(TokenType.T_DIV, (left, right) -> {
            if (right == 0.0d) {
                throw new ArithmeticException("division by zero");
            }
            return left / right;
        });
    }

    private Compute() {
    }

    public static double compute(Node node) {
        return promoteToDouble(computeExact(node));
    }

    public static Number computeExact(Node node) {
        if (node == null) {
            throw new IllegalArgumentException("Node must not be null");
        }

        TokenType tokenType = node.getTokenType();
        if (tokenType == null) {
            throw new IllegalArgumentException("Node token type must not be null");
        }
        if (tokenType == TokenType.T_NUM) {
            Object value = node.getValue();
            if (!(value instanceof Number)) {
                throw new IllegalArgumentException("Number node value must be numeric");
            }
            return normalizeNumber((Number) value);
        }

        DoubleBinaryOperator operation = OPERATIONS.get(tokenType);
        if (operation == null) {
            throw new IllegalArgumentException("Unsupported token type: " + tokenType);
        }
        if (node.getChildren().size() != 2) {
            throw new IllegalArgumentException(
                    "Operator node must have exactly two children: " + tokenType);
        }

        Number leftResult = computeExact(node.getChildren().get(0));
        Number rightResult = computeExact(node.getChildren().get(1));

        if (tokenType == TokenType.T_DIV && isZero(rightResult)) {
            throw new ArithmeticException("division by zero");
        }

        if (leftResult instanceof BigInteger && rightResult instanceof BigInteger) {
            BigInteger leftInteger = (BigInteger) leftResult;
            BigInteger rightInteger = (BigInteger) rightResult;
            switch (tokenType) {
                case T_PLUS:
                    return leftInteger.add(rightInteger);
                case T_MINUS:
                    return leftInteger.subtract(rightInteger);
                case T_MULT:
                    return leftInteger.multiply(rightInteger);
                case T_DIV:
                    return divideIntegers(leftInteger, rightInteger);
                default:
                    throw new IllegalArgumentException("Unsupported token type: " + tokenType);
            }
        }

        return operation.applyAsDouble(
                promoteToDouble(leftResult),
                promoteToDouble(rightResult));
    }

    static String formatResult(Node node, double result) {
        if (!containsDivision(node) && Double.isFinite(result) && result == Math.rint(result)) {
            return formatResult(BigDecimal.valueOf(result).toBigIntegerExact());
        }
        return formatResult(Double.valueOf(result));
    }

    static String formatResult(Number result) {
        if (result == null) {
            throw new IllegalArgumentException("Result must not be null");
        }
        if (result instanceof BigInteger) {
            return result.toString();
        }
        if (result instanceof Double) {
            return formatPythonFloat(result.doubleValue());
        }
        throw new IllegalArgumentException(
                "Unsupported numeric result type: " + result.getClass().getName());
    }

    private static boolean containsDivision(Node node) {
        if (node.getTokenType() == TokenType.T_DIV) {
            return true;
        }
        for (Node child : node.getChildren()) {
            if (containsDivision(child)) {
                return true;
            }
        }
        return false;
    }

    private static Number normalizeNumber(Number value) {
        if (value instanceof BigInteger) {
            return value;
        }
        if (value instanceof Byte
                || value instanceof Short
                || value instanceof Integer
                || value instanceof Long) {
            return BigInteger.valueOf(value.longValue());
        }
        return Double.valueOf(value.doubleValue());
    }

    private static boolean isZero(Number value) {
        if (value instanceof BigInteger) {
            return ((BigInteger) value).signum() == 0;
        }
        return value.doubleValue() == 0.0d;
    }

    private static Double divideIntegers(BigInteger left, BigInteger right) {
        boolean negative = (left.signum() < 0) ^ (right.signum() < 0);
        BigInteger numerator = left.abs();
        BigInteger denominator = right.abs();

        if (numerator.signum() == 0) {
            return Double.valueOf(Double.longBitsToDouble(negative ? Long.MIN_VALUE : 0L));
        }

        int exponent = floorBinaryExponent(numerator, denominator);
        if (exponent > 1023) {
            throw floatingPointOverflow();
        }

        long bits;
        if (exponent >= -1022) {
            BigInteger significand =
                    divideAndRound(numerator, denominator, 52 - exponent);
            if (significand.compareTo(TWO_POW_53) == 0) {
                significand = significand.shiftRight(1);
                exponent++;
                if (exponent > 1023) {
                    throw floatingPointOverflow();
                }
            }

            long fraction = significand.subtract(TWO_POW_52).longValue();
            bits = ((long) (exponent + 1023) << 52) | fraction;
        } else {
            BigInteger significand = divideAndRound(numerator, denominator, 1074);
            bits = significand.longValue();
        }

        if (negative) {
            bits |= Long.MIN_VALUE;
        }
        return Double.valueOf(Double.longBitsToDouble(bits));
    }

    private static int floorBinaryExponent(BigInteger numerator, BigInteger denominator) {
        int exponent = numerator.bitLength() - denominator.bitLength();
        int comparison;
        if (exponent >= 0) {
            comparison = numerator.compareTo(denominator.shiftLeft(exponent));
        } else {
            comparison = numerator.shiftLeft(-exponent).compareTo(denominator);
        }
        return comparison < 0 ? exponent - 1 : exponent;
    }

    private static BigInteger divideAndRound(
            BigInteger numerator,
            BigInteger denominator,
            int binaryScale) {
        BigInteger scaledNumerator = numerator;
        BigInteger scaledDenominator = denominator;
        if (binaryScale >= 0) {
            scaledNumerator = numerator.shiftLeft(binaryScale);
        } else {
            scaledDenominator = denominator.shiftLeft(-binaryScale);
        }

        return divideAndRound(scaledNumerator, scaledDenominator);
    }

    private static BigInteger divideAndRound(
            BigInteger numerator,
            BigInteger denominator) {
        BigInteger[] quotientAndRemainder =
                numerator.divideAndRemainder(denominator);
        int halfComparison =
                quotientAndRemainder[1].shiftLeft(1).compareTo(denominator);
        if (halfComparison > 0
                || (halfComparison == 0 && quotientAndRemainder[0].testBit(0))) {
            return quotientAndRemainder[0].add(BigInteger.ONE);
        }
        return quotientAndRemainder[0];
    }

    private static double promoteToDouble(Number value) {
        double converted = value.doubleValue();
        if (value instanceof BigInteger && !Double.isFinite(converted)) {
            throw floatingPointOverflow();
        }
        return converted;
    }

    private static ArithmeticException floatingPointOverflow() {
        return new ArithmeticException(FLOAT_OVERFLOW_MESSAGE);
    }

    private static String formatPythonFloat(double value) {
        if (Double.isNaN(value)) {
            return "nan";
        }
        if (value == Double.POSITIVE_INFINITY) {
            return "inf";
        }
        if (value == Double.NEGATIVE_INFINITY) {
            return "-inf";
        }
        if (value == 0.0d) {
            return Double.doubleToRawLongBits(value) == Double.doubleToRawLongBits(-0.0d)
                    ? "-0.0"
                    : "0.0";
        }

        long rawBits = Double.doubleToRawLongBits(value);
        long magnitudeBits = rawBits & Long.MAX_VALUE;
        DecimalCandidate candidate = shortestDecimal(magnitudeBits);
        return presentPythonFloat(candidate, rawBits < 0L);
    }

    private static DecimalCandidate shortestDecimal(long magnitudeBits) {
        BigInteger scaledValue = scaledBinaryValue(magnitudeBits);
        BigInteger previousValue = scaledBinaryValue(magnitudeBits - 1);
        BigInteger lowerBoundary = scaledValue.add(previousValue).shiftRight(1);
        BigInteger upperBoundary;
        if (magnitudeBits == MAX_FINITE_MAGNITUDE_BITS) {
            upperBoundary =
                    scaledValue.add(scaledValue.subtract(previousValue).shiftRight(1));
        } else {
            BigInteger nextValue = scaledBinaryValue(magnitudeBits + 1);
            upperBoundary = scaledValue.add(nextValue).shiftRight(1);
        }
        boolean includesBoundaries = (magnitudeBits & 1L) == 0L;

        double positiveValue = Double.longBitsToDouble(magnitudeBits);
        BigDecimal exactValue = new BigDecimal(positiveValue);
        int decimalExponent = exactValue.precision() - exactValue.scale() - 1;
        DecimalCandidate best = null;

        // At most 17 significant decimal digits are needed to identify a binary64 value.
        for (int precision = 1; precision <= 17; precision++) {
            int candidateExponent = decimalExponent - precision + 1;
            BigInteger nearest =
                    nearestDecimalCoefficient(scaledValue, candidateExponent);
            for (int offset = -2; offset <= 2; offset++) {
                BigInteger coefficient = nearest.add(BigInteger.valueOf(offset));
                if (coefficient.signum() <= 0) {
                    continue;
                }

                DecimalCandidate candidate =
                        normalizeCandidate(coefficient, candidateExponent);
                if (!roundsToValue(
                        candidate,
                        lowerBoundary,
                        upperBoundary,
                        includesBoundaries)) {
                    continue;
                }
                if (isBetterCandidate(candidate, best, scaledValue)) {
                    best = candidate;
                }
            }
        }

        if (best == null) {
            throw new IllegalStateException("Unable to render binary64 value");
        }
        return best;
    }

    private static BigInteger scaledBinaryValue(long magnitudeBits) {
        int encodedExponent = (int) (magnitudeBits >>> 52);
        BigInteger significand =
                BigInteger.valueOf(magnitudeBits & FRACTION_MASK);
        if (encodedExponent == 0) {
            return significand.shiftLeft(1);
        }
        return significand.add(TWO_POW_52).shiftLeft(encodedExponent);
    }

    private static BigInteger nearestDecimalCoefficient(
            BigInteger scaledValue,
            int decimalExponent) {
        BigInteger numerator = scaledValue;
        BigInteger denominator = TWO_POW_1075;
        if (decimalExponent < 0) {
            numerator = numerator.multiply(BigInteger.TEN.pow(-decimalExponent));
        } else if (decimalExponent > 0) {
            denominator = denominator.multiply(BigInteger.TEN.pow(decimalExponent));
        }
        return divideAndRound(numerator, denominator);
    }

    private static DecimalCandidate normalizeCandidate(
            BigInteger coefficient,
            int decimalExponent) {
        BigInteger normalized = coefficient;
        int normalizedExponent = decimalExponent;
        while (normalized.mod(BigInteger.TEN).signum() == 0) {
            normalized = normalized.divide(BigInteger.TEN);
            normalizedExponent++;
        }
        return new DecimalCandidate(normalized, normalizedExponent);
    }

    private static boolean roundsToValue(
            DecimalCandidate candidate,
            BigInteger lowerBoundary,
            BigInteger upperBoundary,
            boolean includesBoundaries) {
        int lowerComparison = compareToBoundary(candidate, lowerBoundary);
        int upperComparison = compareToBoundary(candidate, upperBoundary);
        return (lowerComparison > 0 || (includesBoundaries && lowerComparison == 0))
                && (upperComparison < 0 || (includesBoundaries && upperComparison == 0));
    }

    private static int compareToBoundary(
            DecimalCandidate candidate,
            BigInteger scaledBoundary) {
        if (candidate.exponent >= 0) {
            BigInteger scaledCandidate =
                    candidate.coefficient
                            .multiply(BigInteger.TEN.pow(candidate.exponent))
                            .multiply(TWO_POW_1075);
            return scaledCandidate.compareTo(scaledBoundary);
        }
        BigInteger scaledCandidate = candidate.coefficient.multiply(TWO_POW_1075);
        BigInteger scaledBoundaryWithDecimalDenominator =
                scaledBoundary.multiply(BigInteger.TEN.pow(-candidate.exponent));
        return scaledCandidate.compareTo(scaledBoundaryWithDecimalDenominator);
    }

    private static boolean isBetterCandidate(
            DecimalCandidate candidate,
            DecimalCandidate current,
            BigInteger scaledValue) {
        if (current == null || candidate.digitCount < current.digitCount) {
            return true;
        }
        if (candidate.digitCount > current.digitCount) {
            return false;
        }

        int distanceComparison = compareDistance(candidate, current, scaledValue);
        if (distanceComparison != 0) {
            return distanceComparison < 0;
        }
        boolean candidateEven = !candidate.coefficient.testBit(0);
        boolean currentEven = !current.coefficient.testBit(0);
        return candidateEven && !currentEven;
    }

    private static int compareDistance(
            DecimalCandidate left,
            DecimalCandidate right,
            BigInteger scaledValue) {
        DecimalDistance leftDistance = distanceFromValue(left, scaledValue);
        DecimalDistance rightDistance = distanceFromValue(right, scaledValue);
        return leftDistance.numerator.multiply(rightDistance.denominator)
                .compareTo(
                        rightDistance.numerator.multiply(leftDistance.denominator));
    }

    private static DecimalDistance distanceFromValue(
            DecimalCandidate candidate,
            BigInteger scaledValue) {
        if (candidate.exponent >= 0) {
            BigInteger candidateNumerator =
                    candidate.coefficient
                            .multiply(BigInteger.TEN.pow(candidate.exponent))
                            .multiply(TWO_POW_1075);
            return new DecimalDistance(
                    candidateNumerator.subtract(scaledValue).abs(),
                    TWO_POW_1075);
        }

        BigInteger decimalDenominator = BigInteger.TEN.pow(-candidate.exponent);
        BigInteger candidateNumerator = candidate.coefficient.multiply(TWO_POW_1075);
        BigInteger valueNumerator = scaledValue.multiply(decimalDenominator);
        return new DecimalDistance(
                candidateNumerator.subtract(valueNumerator).abs(),
                TWO_POW_1075.multiply(decimalDenominator));
    }

    private static String presentPythonFloat(
            DecimalCandidate candidate,
            boolean negative) {
        String digits = candidate.coefficient.toString();
        int scientificExponent = digits.length() + candidate.exponent - 1;
        StringBuilder formatted = new StringBuilder();
        if (negative) {
            formatted.append('-');
        }

        if (scientificExponent >= 16 || scientificExponent < -4) {
            formatted.append(digits.charAt(0));
            if (digits.length() > 1) {
                formatted.append('.').append(digits.substring(1));
            }
            formatted.append('e').append(scientificExponent >= 0 ? '+' : '-');
            int exponentMagnitude = Math.abs(scientificExponent);
            if (exponentMagnitude < 10) {
                formatted.append('0');
            }
            return formatted.append(exponentMagnitude).toString();
        }

        int decimalPoint = digits.length() + candidate.exponent;
        if (decimalPoint <= 0) {
            formatted.append("0.");
            appendZeros(formatted, -decimalPoint);
            return formatted.append(digits).toString();
        }
        if (decimalPoint < digits.length()) {
            return formatted
                    .append(digits, 0, decimalPoint)
                    .append('.')
                    .append(digits, decimalPoint, digits.length())
                    .toString();
        }
        formatted.append(digits);
        appendZeros(formatted, decimalPoint - digits.length());
        return formatted.append(".0").toString();
    }

    private static void appendZeros(StringBuilder output, int count) {
        for (int index = 0; index < count; index++) {
            output.append('0');
        }
    }

    private static final class DecimalCandidate {
        private final BigInteger coefficient;
        private final int exponent;
        private final int digitCount;

        private DecimalCandidate(BigInteger coefficient, int exponent) {
            this.coefficient = coefficient;
            this.exponent = exponent;
            this.digitCount = coefficient.toString().length();
        }
    }

    private static final class DecimalDistance {
        private final BigInteger numerator;
        private final BigInteger denominator;

        private DecimalDistance(BigInteger numerator, BigInteger denominator) {
            this.numerator = numerator;
            this.denominator = denominator;
        }
    }

    static void run(String[] args, PrintStream output) throws Exception {
        Node ast = Parser.parse(args[0]);
        Number result = computeExact(ast);
        output.println(formatResult(result));
    }

    public static void main(String[] args) throws Exception {
        run(args, System.out);
    }
}
