package cl.codelco.domain;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

import java.util.List;


@Getter
@Setter
@EqualsAndHashCode
@ToString
@NoArgsConstructor
@Data
public class EventResponse {

    @JsonProperty("data")
    private Eventdata eventdata;

    @JsonProperty("message")
    private List<String> message;

    @JsonProperty("status")
    private int status;
}
