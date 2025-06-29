package aaa;

public class App {

    private ExternalApi api;

    public App(ExternalApi api) {
        this.api = api;
    }

    public String getProcessedData() {
        return api.getData(); // Calls the external API
    }
}
