package aaa;

import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

public class MyServiceTest {

    @Test
    public void testVerifyInteraction() {
        // 1. Create a mock
        ExternalApi mockApi = mock(ExternalApi.class);

        // 2. Inject into service
        MyService service = new MyService(mockApi);

        // 3. Call method
        service.fetchData();

        // 4. Verify interaction happened
        verify(mockApi).getData();  
    }
}
