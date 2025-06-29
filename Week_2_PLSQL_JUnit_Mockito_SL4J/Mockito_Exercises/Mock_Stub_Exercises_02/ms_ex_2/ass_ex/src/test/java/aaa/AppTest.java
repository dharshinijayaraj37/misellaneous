package aaa;

import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

public class AppTest {

    @Test
    public void testApiInteraction() {
        // Step 1: Create a mock of ExternalApi
        ExternalApi mockApi = mock(ExternalApi.class);

        // Step 2: Stub the method (optional, just for completeness)
        when(mockApi.getData()).thenReturn("Mocked Data");

        // Step 3: Inject mock into App
        App app = new App(mockApi);

        // Step 4: Call method
        String result = app.getProcessedData();

        // Step 5: Verify interaction
        verify(mockApi).getData(); // ✅ Test passes if called

        // Optional: Assert result
        assertEquals("Mocked Data", result);
    }
}
