package client;

import com.fasterxml.jackson.core.JsonProcessingException;
import endpoint.GetEmployeeEndpoint;
import endpoint.PostEmployeeEndpoint;
import io.restassured.response.Response;
import model.*;
import request.CreateEmployeeRequest;

import java.net.MalformedURLException;
import java.util.List;

public class EmployeeClient {

    private GetEmployeeEndpoint getEmployeeEndpoint;
    private PostEmployeeEndpoint postEmployeeEndpoint;

    public EmployeeClient() {
        getEmployeeEndpoint = new GetEmployeeEndpoint();
        postEmployeeEndpoint = new PostEmployeeEndpoint();
    }

    public Response getEmployeeRequest() throws MalformedURLException, JsonProcessingException {
        return getEmployeeEndpoint.getRequest();
    }

    public String getEmployeeRequestStatus() throws MalformedURLException, JsonProcessingException {
        return getEmployeeEndpoint.getLastResponse().getStatus();
    }

    public List<Datum> getEmployeeData() throws MalformedURLException, JsonProcessingException {
        return getEmployeeEndpoint.getLastResponse().getData();
    }

    public Response AddEmployeeRequest(CreateEmployeeRequest employeeRequest) throws MalformedURLException, JsonProcessingException {
        EmployeeDetails.INSTANCE.setEmployeeName(employeeRequest.getEmployeeName());
        EmployeeDetails.INSTANCE.setEmployeeSalary(employeeRequest.getEmployeeSalary());
        EmployeeDetails.INSTANCE.setEmployeeAge(employeeRequest.getEmployeeAge());

        return postEmployeeEndpoint.postRequest();
    }

    public String getPostEmployeeStatus() throws JsonProcessingException {
        return postEmployeeEndpoint.getLastResponse().getStatus();
    }

    public String getPostEmployeeMessage() throws JsonProcessingException {
        return postEmployeeEndpoint.getLastResponse().getMessage();
    }

    public List<PostData> getNewEmployeeDetails() throws MalformedURLException, JsonProcessingException {
        return postEmployeeEndpoint.getLastResponse().getData();
    }
}
