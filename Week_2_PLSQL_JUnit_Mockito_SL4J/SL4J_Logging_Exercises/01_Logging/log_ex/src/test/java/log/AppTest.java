package log;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

public class AppTest {

    @Test
    public void testReturnsErrorWhenTrue() {
        App app = new App();
        String result = app.performTask(true);
        assertEquals("Error", result);
    }

    @Test
    public void testReturnsWarningWhenFalse() {
        App app = new App();
        String result = app.performTask(false);
        assertEquals("Warning", result);
    }
}
