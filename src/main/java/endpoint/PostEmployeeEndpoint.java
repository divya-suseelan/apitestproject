package endpoint;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import io.restassured.response.Response;
import model.EmployeeDetails;
import response.PostEmployeeResponse;

import java.net.MalformedURLException;

public class PostEmployeeEndpoint extends Endpoint {

    private static final String BASE_PATH = "api/v1";
    private static final String PATH = "create";


    public PostEmployeeEndpoint() {
        super(BASE_PATH, PATH);
    }

    public Response postRequest() throws JsonProcessingException, MalformedURLException {
        String requestBody = this.getObjectMapper().writeValueAsString(EmployeeDetails.INSTANCE.getEmpRequest());
        return post(requestBody,"application/json");
    }

    public PostEmployeeResponse getLastResponse() throws JsonProcessingException {
        this.getObjectMapper().configure(DeserializationFeature.ACCEPT_SINGLE_VALUE_AS_ARRAY,true);
        return this.getObjectMapper().readValue(getLastResponseBody(), PostEmployeeResponse.class);
    }



}