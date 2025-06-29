package log;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class App {
    private static final Logger logger = LoggerFactory.getLogger(App.class);

    public String performTask(boolean causeError) {
        if (causeError) {
            logger.error("An error occurred during task execution.");
            return "Error";
        } else {
            logger.warn("This is just a warning - no real problem.");
            return "Warning";
        }
    }
}
