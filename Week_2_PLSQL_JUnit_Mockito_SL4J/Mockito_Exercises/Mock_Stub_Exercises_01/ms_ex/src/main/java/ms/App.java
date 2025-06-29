package ms;


public class App {

    private ExternalApi api;

    public App(ExternalApi api) {
        this.api = api;
    }

    public String useApi() {
        return api.getData();  // Calls the external dependency
    }
}
