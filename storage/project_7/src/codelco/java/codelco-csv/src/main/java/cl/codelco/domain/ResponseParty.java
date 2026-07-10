package cl.codelco.domain;

import java.util.List;

public class ResponseParty {
    private List<Data> data;
    private List<Message> message;
    private int status;

    public List<Data> getData() {
        return data;
    }

    public void setData(List<Data> data) {
        this.data = data;
    }

    public List<Message> getMessage() {
        return message;
    }

    public void setMessage(List<Message> message) {
        this.message = message;
    }

    public int getStatus() {
        return status;
    }

    public void setStatus(int status) {
        this.status = status;
    }

    public static class Data {
        // Empty for this JSON structure
    }

    public static class Message {
        private String _record_status;
        private List<LineItem> _bp_lineitems;
        private String record_no;
        private int rest_audit_id;

        public String get_record_status() {
            return _record_status;
        }

        public void set_record_status(String _record_status) {
            this._record_status = _record_status;
        }

        public List<LineItem> get_bp_lineitems() {
            return _bp_lineitems;
        }

        public void set_bp_lineitems(List<LineItem> _bp_lineitems) {
            this._bp_lineitems = _bp_lineitems;
        }

        public String getRecord_no() {
            return record_no;
        }

        public void setRecord_no(String record_no) {
            this.record_no = record_no;
        }

        public int getRest_audit_id() {
            return rest_audit_id;
        }

        public void setRest_audit_id(int rest_audit_id) {
            this.rest_audit_id = rest_audit_id;
        }

        public static class LineItem {
            private String CLI_eMail_TB255;
            private String CLI_ACCOUNTNAME_TB255;
            private String CLI_PARTYSITENAME_TB255;

            public String getCLI_eMail_TB255() {
                return CLI_eMail_TB255;
            }

            public void setCLI_eMail_TB255(String CLI_eMail_TB255) {
                this.CLI_eMail_TB255 = CLI_eMail_TB255;
            }

            public String getCLI_ACCOUNTNAME_TB255() {
                return CLI_ACCOUNTNAME_TB255;
            }

            public void setCLI_ACCOUNTNAME_TB255(String CLI_ACCOUNTNAME_TB255) {
                this.CLI_ACCOUNTNAME_TB255 = CLI_ACCOUNTNAME_TB255;
            }

            public String getCLI_PARTYSITENAME_TB255() {
                return CLI_PARTYSITENAME_TB255;
            }

            public void setCLI_PARTYSITENAME_TB255(String CLI_PARTYSITENAME_TB255) {
                this.CLI_PARTYSITENAME_TB255 = CLI_PARTYSITENAME_TB255;
            }
        }
    }
}