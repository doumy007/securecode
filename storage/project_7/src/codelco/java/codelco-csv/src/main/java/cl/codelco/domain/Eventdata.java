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
public class Eventdata {

    private String latestEventDate;

    @JsonProperty("total_records")
    private int totalRecords;

    @JsonProperty("items")
    private List<EventItem> items;

    @JsonProperty("fetched_records")
    private int fetchedRecords;
}
