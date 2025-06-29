package ms;


import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.Test;

public class AppTest {

    @Test
    public void testUseApi_withMock() {
        // Arrange: Create and stub the mock
        ExternalApi mockApi = mock(ExternalApi.class);
        when(mockApi.getData()).thenReturn("Mock Response");

        // Act: Inject into App
        App app = new App(mockApi);
        String result = app.useApi();

        // Assert
        assertEquals("Mock Response", result);
    }
}
