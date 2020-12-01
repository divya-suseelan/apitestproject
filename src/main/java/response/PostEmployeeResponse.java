package response;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import model.PostData;

import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)

public class PostEmployeeResponse {
    private String status;
    @JsonProperty("data")
    private List<PostData> data;
    private String message;

}
