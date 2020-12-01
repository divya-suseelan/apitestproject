package endpoint;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.RestAssured;
import io.restassured.builder.RequestSpecBuilder;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import lombok.Getter;

import java.net.MalformedURLException;
import java.net.URL;


public abstract class Endpoint {

    protected static final String CONTENT_TYPE_HEADER_NAME = "Content-Type";

    @Getter
    private ObjectMapper objectMapper;
    @Getter
    private String basePath;
    @Getter
    private String path;
    private String baseURL = "http://dummy.restapiexample.com";
    protected Response lastResponse;

    public Endpoint(String basePath, String path){
        this.objectMapper = new ObjectMapper();
        this.basePath = basePath;
        this.path = path;
    }

    public URL getURL() throws MalformedURLException {
        String path = baseURL+"/"+this.basePath+"/"+this.path;
        return new URL(path);
    }

    public Response get() throws MalformedURLException {
        RequestSpecification requestSpecification = RestAssured.given();
        lastResponse = requestSpecification.get(this.getURL());
        return lastResponse;
    }

    public String getLastResponseBody(){
        return this.lastResponse.body().asString();
    }

    public Response post(String body, String contentType) throws MalformedURLException {
        RequestSpecification requestSpecification = new RequestSpecBuilder()
                .addHeader(CONTENT_TYPE_HEADER_NAME,contentType)
                .setBody(body)
                .setPort(80)
                .build();

        return post(requestSpecification);
    }

    public Response post(RequestSpecification requestSpecification) throws MalformedURLException {
        lastResponse = RestAssured.with()
                .spec(requestSpecification)
                .log().all()
                .post(this.getURL());

        return lastResponse;

    }

}
