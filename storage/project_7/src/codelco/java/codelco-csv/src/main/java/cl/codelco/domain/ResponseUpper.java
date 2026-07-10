package cl.codelco.domain;

import java.util.List;

public class ResponseUpper {

    private List<Message> messages;
    private int status;

    public ResponseUpper(List<Message> messages, int status) {
        this.messages = messages;
        this.status = status;
    }

    public List<Message> getMessages() {
        return messages;
    }

    public void setMessages(List<Message> messages) {
        this.messages = messages;
    }

    public int getStatus() {
        return status;
    }

    public void setStatus(int status) {
        this.status = status;
    }

    public static class Message {

        private String _recordStatus;
        private String CLI_ESTABLISHEDDATE_DOP;
        private String CLI_RAZON_SOCIAL_TB500;
        private String CLI_NOMBRECOMERCIAL_TB500;
        private int CLI_NADJUNTOS_INT;
        private String CLI_TERMINATIONDATE_DOP;
        private String CLI_RFC_TB120;
        private int rest_audit_id;

        public Message() {
        }

        public Message(String _recordStatus, String CLI_ESTABLISHEDDATE_DOP, String CLI_RAZON_SOCIAL_TB500, String CLI_NOMBRECOMERCIAL_TB500, int CLI_NADJUNTOS_INT, String CLI_TERMINATIONDATE_DOP, String CLI_RFC_TB120, int rest_audit_id) {
            this._recordStatus = _recordStatus;
            this.CLI_ESTABLISHEDDATE_DOP = CLI_ESTABLISHEDDATE_DOP;
            this.CLI_RAZON_SOCIAL_TB500 = CLI_RAZON_SOCIAL_TB500;
            this.CLI_NOMBRECOMERCIAL_TB500 = CLI_NOMBRECOMERCIAL_TB500;
            this.CLI_NADJUNTOS_INT = CLI_NADJUNTOS_INT;
            this.CLI_TERMINATIONDATE_DOP = CLI_TERMINATIONDATE_DOP;
            this.CLI_RFC_TB120 = CLI_RFC_TB120;
            this.rest_audit_id = rest_audit_id;
        }

        public String get_recordStatus() {
            return _recordStatus;
        }

        public void set_recordStatus(String _recordStatus) {
            this._recordStatus = _recordStatus;
        }

        public String getCLI_ESTABLISHEDDATE_DOP() {
            return CLI_ESTABLISHEDDATE_DOP;
        }

        public void setCLI_ESTABLISHEDDATE_DOP(String CLI_ESTABLISHEDDATE_DOP) {
            this.CLI_ESTABLISHEDDATE_DOP = CLI_ESTABLISHEDDATE_DOP;
        }

        public String getCLI_RAZON_SOCIAL_TB500() {
            return CLI_RAZON_SOCIAL_TB500;
        }

        public void setCLI_RAZON_SOCIAL_TB500(String CLI_RAZON_SOCIAL_TB500) {
            this.CLI_RAZON_SOCIAL_TB500 = CLI_RAZON_SOCIAL_TB500;
        }

        public String getCLI_NOMBRECOMERCIAL_TB500() {
            return CLI_NOMBRECOMERCIAL_TB500;
        }

        public void setCLI_NOMBRECOMERCIAL_TB500(String CLI_NOMBRECOMERCIAL_TB500) {
            this.CLI_NOMBRECOMERCIAL_TB500 = CLI_NOMBRECOMERCIAL_TB500;
        }

        public int getCLI_NADJUNTOS_INT() {
            return CLI_NADJUNTOS_INT;
        }

        public void setCLI_NADJUNTOS_INT(int CLI_NADJUNTOS_INT) {
            this.CLI_NADJUNTOS_INT = CLI_NADJUNTOS_INT;
        }

        public String getCLI_TERMINATIONDATE_DOP() {
            return CLI_TERMINATIONDATE_DOP;
        }

        public void setCLI_TERMINATIONDATE_DOP(String CLI_TERMINATIONDATE_DOP) {
            this.CLI_TERMINATIONDATE_DOP = CLI_TERMINATIONDATE_DOP;
        }

        public String getCLI_RFC_TB120() {
            return CLI_RFC_TB120;
        }

        public void setCLI_RFC_TB120(String CLI_RFC_TB120) {
            this.CLI_RFC_TB120 = CLI_RFC_TB120;
        }

        public int getRest_audit_id() {
            return rest_audit_id;
        }

        public void setRest_audit_id(int rest_audit_id) {
            this.rest_audit_id = rest_audit_id;
        }

    }

}

