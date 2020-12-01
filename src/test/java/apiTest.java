import client.EmployeeClient;
import com.fasterxml.jackson.core.JsonProcessingException;
import org.junit.Test;
import request.CreateEmployeeRequest;

import java.net.MalformedURLException;

import static org.junit.Assert.assertEquals;

public class apiTest {

    private EmployeeClient employeeClient;

    @Test
    public void testGetEmployee() throws MalformedURLException, JsonProcessingException {
        employeeClient = new EmployeeClient();
        employeeClient.getEmployeeRequest();

        assertEquals("success",employeeClient.getEmployeeRequestStatus());
        assertEquals("4",employeeClient.getEmployeeData().get(3).getId());
        assertEquals("Cedric Kelly",employeeClient.getEmployeeData().get(3).getEmployeeName());
        assertEquals("433060",employeeClient.getEmployeeData().get(3).getEmployeeSalary());
        assertEquals("22",employeeClient.getEmployeeData().get(3).getEmployeeAge());

    }

    @Test
    public void testPostEmployee() throws MalformedURLException, JsonProcessingException {
        employeeClient = new EmployeeClient();

        CreateEmployeeRequest employeeRequest = new CreateEmployeeRequest();
        employeeRequest.setEmployeeName("John Smith");
        employeeRequest.setEmployeeSalary("377000");
        employeeRequest.setEmployeeAge("28");

        employeeClient.AddEmployeeRequest(employeeRequest);

        assertEquals("success",employeeClient.getPostEmployeeStatus());
        assertEquals("Successfully! Record has been added.",employeeClient.getPostEmployeeMessage());
        assertEquals(employeeRequest.getEmployeeName(),employeeClient.getNewEmployeeDetails().get(0).getEmployeeName());
        assertEquals(employeeRequest.getEmployeeSalary(),employeeClient.getNewEmployeeDetails().get(0).getEmployeeSalary());
        assertEquals(employeeRequest.getEmployeeAge(),employeeClient.getNewEmployeeDetails().get(0).getEmployeeAge());

    }
}
