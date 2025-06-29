package aaa;

import org.junit.jupiter.api.*;

import static org.junit.jupiter.api.Assertions.*;

public class CalculatorTest {

    private Calculator calculator;

    @BeforeEach
    void setUp() {
        calculator = new Calculator(); // Arrange
        System.out.println("Setup done.");
    }

    @AfterEach
    void tearDown() {
        calculator = null;
        System.out.println("Teardown done.");
    }

    @Test
    void testAdd() {
        // Act
        int result = calculator.add(10, 5);

        // Assert
        assertEquals(15, result);
    }

    @Test
    void testSubtract() {
        int result = calculator.subtract(20, 8);
        assertEquals(12, result);
    }
}
