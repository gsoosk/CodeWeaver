import java.math.BigInteger;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

public final class Compute {
    private static final String INTEGER_CONVERSION_OVERFLOW =
            "int too large to convert to float";
    private static final String INTEGER_DIVISION_OVERFLOW =
            "integer division result too large for a float";
    private static final Map<TokenType, NumericOperation> OPERATIONS;

    static {
        Map<TokenType, NumericOperation> operations =
                new EnumMap<TokenType, NumericOperation>(TokenType.class);
        operations.put(TokenType.T_PLUS, NumericResult::add);
        operations.put(TokenType.T_MINUS, NumericResult::subtract);
        operations.put(TokenType.T_MULT, NumericResult::multiply);
        operations.put(TokenType.T_DIV, NumericResult::divide);
        OPERATIONS = Collections.unmodifiableMap(operations);
    }

    private Compute() {
    }

    public static double compute(Node node) {
        return computeExact(node).asDouble();
    }

    public static PythonNumericValue computeExact(Node node) {
        return evaluate(node);
    }

    private static NumericResult evaluate(Node node) {
        if (node == null) {
            throw new IllegalArgumentException("Node must not be null");
        }

        if (node.getTokenType() == TokenType.T_NUM) {
            if (!(node.getValue() instanceof Number)) {
                throw new IllegalArgumentException("Numeric node value must be a number");
            }
            return NumericResult.from((Number) node.getValue());
        }

        NumericOperation operation = OPERATIONS.get(node.getTokenType());
        if (operation == null) {
            throw new IllegalArgumentException(
                    "Unsupported node type: " + node.getTokenType());
        }

        List<Node> children = node.getChildren();
        if (children == null || children.size() != 2) {
            throw new IllegalArgumentException(
                    "Operator node must have exactly two children");
        }

        NumericResult leftResult = evaluate(children.get(0));
        NumericResult rightResult = evaluate(children.get(1));
        return operation.apply(leftResult, rightResult);
    }

    static void run(String[] args, Consumer<String> output) throws ParserException {
        Node ast = Parser.parse(args[0]);
        PythonNumericValue result = computeExact(ast);
        output.accept(result.isInteger()
                ? result.asBigInteger().toString()
                : PythonFloatFormatter.format(result.asDouble()));
    }

    public static void main(String[] args) throws ParserException {
        run(args, System.out::println);
    }

    private interface NumericOperation {
        NumericResult apply(NumericResult left, NumericResult right);
    }

    private static final class NumericResult implements PythonNumericValue {
        private final BigInteger integerValue;
        private final double floatingValue;
        private final boolean floating;

        private NumericResult(BigInteger integerValue, double floatingValue, boolean floating) {
            this.integerValue = integerValue;
            this.floatingValue = floatingValue;
            this.floating = floating;
        }

        static NumericResult from(Number value) {
            if (value instanceof BigInteger) {
                return integer((BigInteger) value);
            }
            if (value instanceof Byte
                    || value instanceof Short
                    || value instanceof Integer
                    || value instanceof Long) {
                return integer(BigInteger.valueOf(value.longValue()));
            }

            double converted = value.doubleValue();
            if (!(value instanceof Double)
                    && !(value instanceof Float)
                    && (Double.isInfinite(converted) || Double.isNaN(converted))) {
                throw new ArithmeticException("number too large to convert to float");
            }
            return floating(converted);
        }

        static NumericResult integer(BigInteger value) {
            return new NumericResult(value, 0.0d, false);
        }

        static NumericResult floating(double value) {
            return new NumericResult(null, value, true);
        }

        NumericResult add(NumericResult right) {
            if (!floating && !right.floating) {
                return integer(integerValue.add(right.integerValue));
            }
            return floating(asDouble() + right.asDouble());
        }

        NumericResult subtract(NumericResult right) {
            if (!floating && !right.floating) {
                return integer(integerValue.subtract(right.integerValue));
            }
            return floating(asDouble() - right.asDouble());
        }

        NumericResult multiply(NumericResult right) {
            if (!floating && !right.floating) {
                return integer(integerValue.multiply(right.integerValue));
            }
            return floating(asDouble() * right.asDouble());
        }

        NumericResult divide(NumericResult right) {
            if (!floating && !right.floating) {
                if (right.integerValue.signum() == 0) {
                    throw new ArithmeticException("division by zero");
                }
                return floating(integerRatioToDouble(
                        integerValue, right.integerValue, INTEGER_DIVISION_OVERFLOW));
            }

            double leftDouble = asDouble();
            double rightDouble = right.asDouble();
            if (rightDouble == 0.0d) {
                throw new ArithmeticException("division by zero");
            }
            return floating(leftDouble / rightDouble);
        }

        @Override
        public boolean isInteger() {
            return !floating;
        }

        @Override
        public BigInteger asBigInteger() {
            if (floating) {
                throw new IllegalStateException(
                        "Floating value has no exact integer representation");
            }
            return integerValue;
        }

        @Override
        public double asDouble() {
            return floating
                    ? floatingValue
                    : integerRatioToDouble(
                            integerValue, BigInteger.ONE, INTEGER_CONVERSION_OVERFLOW);
        }

        private static double integerRatioToDouble(
                BigInteger numerator, BigInteger denominator, String overflowMessage) {
            boolean negative =
                    (numerator.signum() < 0) != (denominator.signum() < 0);
            BigInteger numeratorMagnitude = numerator.abs();
            BigInteger denominatorMagnitude = denominator.abs();

            if (numeratorMagnitude.signum() == 0) {
                return signedZero(negative);
            }

            int exponent =
                    numeratorMagnitude.bitLength() - denominatorMagnitude.bitLength();
            if (compareToScaledDenominator(
                    numeratorMagnitude, denominatorMagnitude, exponent) < 0) {
                exponent--;
            }

            if (exponent > 1023) {
                throw new ArithmeticException(overflowMessage);
            }
            if (exponent < -1075) {
                return signedZero(negative);
            }

            long magnitudeBits;
            if (exponent >= -1022) {
                int shift = 52 - exponent;
                BigInteger dividend = numeratorMagnitude;
                BigInteger divisor = denominatorMagnitude;
                if (shift >= 0) {
                    dividend = dividend.shiftLeft(shift);
                } else {
                    divisor = divisor.shiftLeft(-shift);
                }

                BigInteger significand = roundedQuotient(dividend, divisor);
                if (significand.bitLength() > 53) {
                    significand = significand.shiftRight(1);
                    exponent++;
                    if (exponent > 1023) {
                        throw new ArithmeticException(overflowMessage);
                    }
                }

                long fraction = significand.longValue() - (1L << 52);
                magnitudeBits = ((long) (exponent + 1023) << 52) | fraction;
            } else {
                BigInteger significand = roundedQuotient(
                        numeratorMagnitude.shiftLeft(1074), denominatorMagnitude);
                magnitudeBits = significand.longValue();
            }

            long bits = negative ? magnitudeBits | Long.MIN_VALUE : magnitudeBits;
            return Double.longBitsToDouble(bits);
        }

        private static int compareToScaledDenominator(
                BigInteger numerator, BigInteger denominator, int exponent) {
            if (exponent >= 0) {
                return numerator.compareTo(denominator.shiftLeft(exponent));
            }
            return numerator.shiftLeft(-exponent).compareTo(denominator);
        }

        private static BigInteger roundedQuotient(
                BigInteger dividend, BigInteger divisor) {
            BigInteger[] quotientAndRemainder = dividend.divideAndRemainder(divisor);
            BigInteger quotient = quotientAndRemainder[0];
            int halfwayComparison =
                    quotientAndRemainder[1].shiftLeft(1).compareTo(divisor);
            if (halfwayComparison > 0
                    || (halfwayComparison == 0 && quotient.testBit(0))) {
                quotient = quotient.add(BigInteger.ONE);
            }
            return quotient;
        }

        private static double signedZero(boolean negative) {
            return negative ? -0.0d : 0.0d;
        }
    }
}
