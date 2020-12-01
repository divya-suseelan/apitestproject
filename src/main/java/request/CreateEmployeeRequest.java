package request;

import lombok.Data;


@Data
public class CreateEmployeeRequest {

    private String employeeName;
    private String employeeSalary;
    private String employeeAge;

}
