package response;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import model.Datum;

import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class GetEmployeeResponse {
    @JsonProperty("status")
    private String status;
    @JsonProperty("data")
    private List<Datum> data;
}
