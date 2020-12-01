package model;

import lombok.Getter;
import lombok.Setter;
import request.CreateEmployeeRequest;

@Getter
@Setter
public class EmployeeDetails {

    public static EmployeeDetails INSTANCE;

    static {
        INSTANCE = new EmployeeDetails();

    }

    private String employeeName;
    private String employeeSalary;
    private String employeeAge;

    public CreateEmployeeRequest getEmpRequest() {
        CreateEmployeeRequest req = new CreateEmployeeRequest();
        req.setEmployeeName(this.employeeName);
        req.setEmployeeSalary(this.employeeSalary);
        req.setEmployeeAge(this.employeeAge);
        return req;
    }
}

