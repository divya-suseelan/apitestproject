package endpoint;


import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import io.restassured.response.Response;
import response.GetEmployeeResponse;

import java.net.MalformedURLException;

public class GetEmployeeEndpoint extends Endpoint{

    private static final String BASE_PATH = "api/v1";
    private static final String PATH = "employees";

    public GetEmployeeEndpoint() {
        super(BASE_PATH, PATH);
    }

    public Response getRequest() throws MalformedURLException {
        return get();
    }

    public GetEmployeeResponse getLastResponse() throws JsonProcessingException {
        return this.getObjectMapper().readValue(getLastResponseBody(),GetEmployeeResponse.class);

    }
}
