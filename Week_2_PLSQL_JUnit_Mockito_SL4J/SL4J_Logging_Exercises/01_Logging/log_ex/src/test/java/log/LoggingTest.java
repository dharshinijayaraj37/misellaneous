package log;

import org.junit.jupiter.api.Test;

public class LoggingTest {

    @Test
    public void testLoggingRuns() {
        // Simply check that the method runs without crashing
        Logging.main(new String[]{});
    }
}
