import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.EnumMap;
import java.util.Map;

public final class Compute {
    private static final int MAX_DOUBLE_SIGNIFICANT_DIGITS = 17;
    private static final int MAX_DOUBLE_EXPONENT = 1023;
    private static final int MIN_NORMAL_DOUBLE_EXPONENT = -1022;
    private static final int MIN_SUBNORMAL_DOUBLE_EXPONENT = -1074;
    private static final BigInteger TWO_TO_52 = BigInteger.ONE.shiftLeft(52);
    private static final BigInteger TWO_TO_53 = BigInteger.ONE.shiftLeft(53);

    public static final Map<TokenType, NumericOperation> operations =
            new EnumMap<TokenType, NumericOperation>(TokenType.class);

    static {
        operations.put(TokenType.T_PLUS, (left, right) -> {
            if (areIntegral(left, right)) {
                return toBigInteger(left).add(toBigInteger(right));
            }
            return left.doubleValue() + right.doubleValue();
        });
        operations.put(TokenType.T_MINUS, (left, right) -> {
            if (areIntegral(left, right)) {
                return toBigInteger(left).subtract(toBigInteger(right));
            }
            return left.doubleValue() - right.doubleValue();
        });
        operations.put(TokenType.T_MULT, (left, right) -> {
            if (areIntegral(left, right)) {
                return toBigInteger(left).multiply(toBigInteger(right));
            }
            return left.doubleValue() * right.doubleValue();
        });
        operations.put(TokenType.T_DIV, (left, right) -> {
            if (areIntegral(left, right)) {
                return divideIntegralOperands(
                        toBigInteger(left), toBigInteger(right));
            }
            double divisor = right.doubleValue();
            if (divisor == 0.0d) {
                throw new ArithmeticException("division by zero");
            }
            return left.doubleValue() / divisor;
        });
    }

    private Compute() {
    }

    public static double compute(Node node) {
        return computeExact(node).doubleValue();
    }

    public static Number computeExact(Node node) {
        if (node == null) {
            throw new IllegalArgumentException("Node must not be null");
        }

        if (node.getTokenType() == TokenType.T_NUM) {
            Object value = node.getValue();
            if (!(value instanceof Number)) {
                throw new IllegalArgumentException("Number node value must be a Number");
            }
            return (Number) value;
        }

        if (node.getChildren().size() < 2) {
            throw new IllegalArgumentException(
                    "Non-number node must have at least two children: "
                            + node.getTokenType());
        }

        Number leftResult = computeExact(node.getChildren().get(0));
        Number rightResult = computeExact(node.getChildren().get(1));
        return applyOperation(node.getTokenType(), leftResult, rightResult);
    }

    private static Number applyOperation(
            TokenType tokenType, Number leftResult, Number rightResult) {
        if (tokenType == null) {
            throw new IllegalArgumentException("Unsupported operation: null");
        }

        NumericOperation operation = operations.get(tokenType);
        if (operation == null) {
            throw new IllegalArgumentException("Unsupported operation: " + tokenType);
        }

        Number result = operation.apply(leftResult, rightResult);
        if (result == null) {
            throw new IllegalStateException("Operation returned null: " + tokenType);
        }
        return result;
    }

    private static boolean areIntegral(Number left, Number right) {
        return isIntegral(left) && isIntegral(right);
    }

    private static boolean isIntegral(Number value) {
        return value instanceof BigInteger
                || value instanceof Byte
                || value instanceof Short
                || value instanceof Integer
                || value instanceof Long;
    }

    private static BigInteger toBigInteger(Number value) {
        if (value instanceof BigInteger) {
            return (BigInteger) value;
        }
        return BigInteger.valueOf(value.longValue());
    }

    static double divideIntegralOperands(BigInteger dividend, BigInteger divisor) {
        if (dividend == null || divisor == null) {
            throw new IllegalArgumentException(
                    "Division operands must not be null");
        }
        if (divisor.signum() == 0) {
            throw new ArithmeticException("division by zero");
        }

        boolean negative =
                (dividend.signum() < 0) ^ (divisor.signum() < 0);
        BigInteger numerator = dividend.abs();
        BigInteger denominator = divisor.abs();
        if (numerator.signum() == 0) {
            return signedZero(negative);
        }

        int bitLengthDifference =
                numerator.bitLength() - denominator.bitLength();
        if (bitLengthDifference > MAX_DOUBLE_EXPONENT + 1) {
            throw integerDivisionOverflow();
        }
        if (bitLengthDifference
                < MIN_SUBNORMAL_DOUBLE_EXPONENT - 1) {
            return signedZero(negative);
        }

        int exponent = floorBinaryExponent(
                numerator, denominator, bitLengthDifference);
        if (exponent > MAX_DOUBLE_EXPONENT) {
            throw integerDivisionOverflow();
        }

        long magnitudeBits;
        if (exponent < MIN_NORMAL_DOUBLE_EXPONENT) {
            BigInteger significand = divideAndRoundNearestEven(
                    numerator.shiftLeft(-MIN_SUBNORMAL_DOUBLE_EXPONENT),
                    denominator);
            magnitudeBits = significand.longValue();
        } else {
            int shift = 52 - exponent;
            BigInteger scaledNumerator = numerator;
            BigInteger scaledDenominator = denominator;
            if (shift >= 0) {
                scaledNumerator = scaledNumerator.shiftLeft(shift);
            } else {
                scaledDenominator =
                        scaledDenominator.shiftLeft(-shift);
            }

            BigInteger significand = divideAndRoundNearestEven(
                    scaledNumerator, scaledDenominator);
            if (significand.equals(TWO_TO_53)) {
                significand = TWO_TO_52;
                exponent++;
                if (exponent > MAX_DOUBLE_EXPONENT) {
                    throw integerDivisionOverflow();
                }
            }

            long exponentBits = (long) (exponent + 1023) << 52;
            long fractionBits =
                    significand.subtract(TWO_TO_52).longValue();
            magnitudeBits = exponentBits | fractionBits;
        }

        long signBit = negative ? Long.MIN_VALUE : 0L;
        return Double.longBitsToDouble(signBit | magnitudeBits);
    }

    private static int floorBinaryExponent(
            BigInteger numerator,
            BigInteger denominator,
            int bitLengthDifference) {
        int comparison;
        if (bitLengthDifference >= 0) {
            comparison = numerator.compareTo(
                    denominator.shiftLeft(bitLengthDifference));
        } else {
            comparison = numerator.shiftLeft(-bitLengthDifference)
                    .compareTo(denominator);
        }
        return comparison < 0
                ? bitLengthDifference - 1
                : bitLengthDifference;
    }

    private static BigInteger divideAndRoundNearestEven(
            BigInteger numerator, BigInteger denominator) {
        BigInteger[] quotientAndRemainder =
                numerator.divideAndRemainder(denominator);
        BigInteger quotient = quotientAndRemainder[0];
        int halfComparison = quotientAndRemainder[1]
                .shiftLeft(1)
                .compareTo(denominator);
        if (halfComparison > 0
                || (halfComparison == 0 && quotient.testBit(0))) {
            return quotient.add(BigInteger.ONE);
        }
        return quotient;
    }

    private static double signedZero(boolean negative) {
        return Double.longBitsToDouble(negative ? Long.MIN_VALUE : 0L);
    }

    private static ArithmeticException integerDivisionOverflow() {
        return new ArithmeticException(
                "integer division result too large for a float");
    }

    static String formatNonFinite(double value) {
        if (Double.isNaN(value)) {
            return "nan";
        }
        if (value == Double.POSITIVE_INFINITY) {
            return "inf";
        }
        if (value == Double.NEGATIVE_INFINITY) {
            return "-inf";
        }
        throw new IllegalArgumentException("Value must be non-finite");
    }

    static String formatResult(Node ast, double result) {
        if (Double.isNaN(result) || Double.isInfinite(result)) {
            return formatPythonNumber(Double.valueOf(result));
        }
        if (containsDivision(ast) || result != Math.rint(result)) {
            return formatPythonNumber(Double.valueOf(result));
        }
        return formatPythonNumber(
                BigDecimal.valueOf(result).toBigIntegerExact());
    }

    static String formatPythonNumber(Number result) {
        if (result == null) {
            throw new IllegalArgumentException("Result must not be null");
        }
        if (isIntegral(result)) {
            return toBigInteger(result).toString();
        }

        double value = result.doubleValue();
        if (Double.isNaN(value) || Double.isInfinite(value)) {
            return formatNonFinite(value);
        }
        if (value == 0.0d) {
            return Double.doubleToRawLongBits(value) < 0 ? "-0.0" : "0.0";
        }

        BigDecimal decimal = shortestRoundTripDecimal(value).stripTrailingZeros();
        int exponent = decimal.precision() - decimal.scale() - 1;
        if (exponent >= -4 && exponent <= 15) {
            String fixed = decimal.toPlainString();
            return fixed.indexOf('.') >= 0 ? fixed : fixed + ".0";
        }

        String digits = decimal.abs().unscaledValue().toString();
        StringBuilder formatted = new StringBuilder();
        if (value < 0.0d) {
            formatted.append('-');
        }
        formatted.append(digits.charAt(0));
        if (digits.length() > 1) {
            formatted.append('.').append(digits.substring(1));
        }
        formatted.append('e').append(exponent >= 0 ? '+' : '-');

        int absoluteExponent = Math.abs(exponent);
        if (absoluteExponent < 10) {
            formatted.append('0');
        }
        return formatted.append(absoluteExponent).toString();
    }

    private static BigDecimal shortestRoundTripDecimal(double value) {
        // Python selects the shortest nearest-even decimal that round-trips.
        BigDecimal exact = new BigDecimal(value);
        long expectedBits = Double.doubleToRawLongBits(value);

        for (int precision = 1;
                precision <= MAX_DOUBLE_SIGNIFICANT_DIGITS;
                precision++) {
            BigDecimal candidate = exact.round(
                    new MathContext(precision, RoundingMode.HALF_EVEN));
            double roundTrip = Double.parseDouble(candidate.toString());
            if (Double.doubleToRawLongBits(roundTrip) == expectedBits) {
                return candidate;
            }
        }

        throw new IllegalStateException(
                "Unable to format finite double: " + value);
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

    public static void main(String[] args) throws ParserException {
        Node ast = Parser.parse(args[0]);
        Number result = computeExact(ast);
        System.out.println(formatPythonNumber(result));
    }
}
