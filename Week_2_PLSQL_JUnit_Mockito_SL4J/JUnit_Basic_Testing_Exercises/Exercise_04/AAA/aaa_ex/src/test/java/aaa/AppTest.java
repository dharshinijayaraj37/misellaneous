package aaa;

import org.junit.jupiter.api.*;

import static org.junit.jupiter.api.Assertions.*;

public class AppTest {

    private int a;
    private int b;

    @BeforeEach
    void setUp() {
        // Arrange: setup test variables
        a = 10;
        b = 5;
        System.out.println("Setup complete.");
    }

    @AfterEach
    void tearDown() {
        // Teardown: clean up if needed
        a = 0;
        b = 0;
        System.out.println("Teardown complete.");
    }

    @Test
    void testAddition() {
        // Act
        int result = a + b;

        // Assert
        assertEquals(15, result);
    }

    @Test
    void testSubtraction() {
        int result = a - b;
        assertEquals(5, result);
    }

    @Test
    void testMultiplication() {
        int result = a * b;
        assertEquals(50, result);
    }

    @Test
    void testDivision() {
        int result = a / b;
        assertEquals(2, result);
    }
}
