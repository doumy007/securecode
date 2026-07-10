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
public class EventItem {
    @JsonProperty("workflow_from")
    private String workflowFrom;

    @JsonProperty("old_status")
    private String oldStatus;

    @JsonProperty("workflow_action")
    private String workflowAction;

    @JsonProperty("workflow_to")
    private String workflowTo;

    @JsonProperty("object_type")
    private String objectType;

    @JsonProperty("new_status")
    private String newStatus;

    @JsonProperty("shell_number")
    private String shellNumber;

    @JsonProperty("object_prefix")
    private String objectPrefix;

    @JsonProperty("project_id")
    private int projectId;

    @JsonProperty("object_name")
    private String objectName;

    @JsonProperty("record_no")
    private String recordNo;

    @JsonProperty("event_date")
    private String eventDate;

    @JsonProperty("object_subtype")
    private String objectSubtype;
}
