package cl.codelco.domain;

import java.util.List;

public class ResponseLine {

    private List<Message> messages;
    private int status;

    public ResponseLine(List<Message> messages, int status) {
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
        private List<BpLineItem> _bpLineItems;
        private String recordNo;

        public Message() {
        }

        public String get_recordStatus() {
            return _recordStatus;
        }

        public void set_recordStatus(String _recordStatus) {
            this._recordStatus = _recordStatus;
        }

        public List<BpLineItem> get_bpLineItems() {
            return _bpLineItems;
        }

        public void set_bpLineItems(List<BpLineItem> _bpLineItems) {
            this._bpLineItems = _bpLineItems;
        }

        public String getRecordNo() {
            return recordNo;
        }

        public void setRecordNo(String recordNo) {
            this.recordNo = recordNo;
        }

    }

    public static class BpLineItem {

        private String CLIE_InvoiceCurrency_SPD;
        private String CLI_DIRECPRINC_TB255;
        private String CLI_CUSTOMERCLASS_TB250;
        private String CLI_eMail_TB255;
        private String CLIE_NUMEROPROYECTO_SPD;
        private String CONT_CENTRO_SPD;
        private String CONT_UNIDAD_SPD;
        private String CLI_CUENTACONTABLE_SPD;
        private String CONT_UNINEGOCIO_PKBP;
        private String CLI_PersonFirstName_TB255;
        private String CLI_PersonLastName_TB255;
        private String CLI_DELEGACION_TB120;
        private String CLI_ESTABLISHEDDATE_DOP;
        private String CLI_COLONIA_TB120;
        private String CLI_TERMINATIONDATE_DOP;
        private String CONT_LINEA_SPD;
        private int li_num;
        private String CLI_CODZIP_TB120;
        private String CLI_PAIS_SPD;

        public BpLineItem() {
        }

        public String getCLIE_InvoiceCurrency_SPD() {
            return CLIE_InvoiceCurrency_SPD;
        }

        public void setCLIE_InvoiceCurrency_SPD(String CLIE_InvoiceCurrency_SPD) {
            this.CLIE_InvoiceCurrency_SPD = CLIE_InvoiceCurrency_SPD;
        }

        public String getCLI_DIRECPRINC_TB255() {
            return CLI_DIRECPRINC_TB255;
        }

        public void setCLI_DIRECPRINC_TB255(String CLI_DIRECPRINC_TB255) {
            this.CLI_DIRECPRINC_TB255 = CLI_DIRECPRINC_TB255;
        }

        public String getCLI_CUSTOMERCLASS_TB250() {
            return CLI_CUSTOMERCLASS_TB250;
        }

        public void setCLI_CUSTOMERCLASS_TB250(String CLI_CUSTOMERCLASS_TB250) {
            this.CLI_CUSTOMERCLASS_TB250 = CLI_CUSTOMERCLASS_TB250;
        }

        public String getCLI_eMail_TB255() {
            return CLI_eMail_TB255;
        }

        public void setCLI_eMail_TB255(String CLI_eMail_TB255) {
            this.CLI_eMail_TB255 = CLI_eMail_TB255;
        }

        public String getCLIE_NUMEROPROYECTO_SPD() {
            return CLIE_NUMEROPROYECTO_SPD;
        }

        public void setCLIE_NUMEROPROYECTO_SPD(String CLIE_NUMEROPROYECTO_SPD) {
            this.CLIE_NUMEROPROYECTO_SPD = CLIE_NUMEROPROYECTO_SPD;
        }

        public String getCONT_CENTRO_SPD() {
            return CONT_CENTRO_SPD;
        }

        public void setCONT_CENTRO_SPD(String CONT_CENTRO_SPD) {
            this.CONT_CENTRO_SPD = CONT_CENTRO_SPD;
        }

        public String getCONT_UNIDAD_SPD() {
            return CONT_UNIDAD_SPD;
        }

        public void setCONT_UNIDAD_SPD(String CONT_UNIDAD_SPD) {
            this.CONT_UNIDAD_SPD = CONT_UNIDAD_SPD;
        }

        public String getCLI_CUENTACONTABLE_SPD() {
            return CLI_CUENTACONTABLE_SPD;
        }

        public void setCLI_CUENTACONTABLE_SPD(String CLI_CUENTACONTABLE_SPD) {
            this.CLI_CUENTACONTABLE_SPD = CLI_CUENTACONTABLE_SPD;
        }

        public String getCONT_UNINEGOCIO_PKBP() {
            return CONT_UNINEGOCIO_PKBP;
        }

        public void setCONT_UNINEGOCIO_PKBP(String CONT_UNINEGOCIO_PKBP) {
            this.CONT_UNINEGOCIO_PKBP = CONT_UNINEGOCIO_PKBP;
        }

        public String getCLI_PersonFirstName_TB255() {
            return CLI_PersonFirstName_TB255;
        }

        public void setCLI_PersonFirstName_TB255(String CLI_PersonFirstName_TB255) {
            this.CLI_PersonFirstName_TB255 = CLI_PersonFirstName_TB255;
        }

        public String getCLI_PersonLastName_TB255() {
            return CLI_PersonLastName_TB255;
        }

        public void setCLI_PersonLastName_TB255(String CLI_PersonLastName_TB255) {
            this.CLI_PersonLastName_TB255 = CLI_PersonLastName_TB255;
        }

        public String getCLI_DELEGACION_TB120() {
            return CLI_DELEGACION_TB120;
        }

        public void setCLI_DELEGACION_TB120(String CLI_DELEGACION_TB120) {
            this.CLI_DELEGACION_TB120 = CLI_DELEGACION_TB120;
        }

        public String getCLI_ESTABLISHEDDATE_DOP() {
            return CLI_ESTABLISHEDDATE_DOP;
        }

        public void setCLI_ESTABLISHEDDATE_DOP(String CLI_ESTABLISHEDDATE_DOP) {
            this.CLI_ESTABLISHEDDATE_DOP = CLI_ESTABLISHEDDATE_DOP;
        }

        public String getCLI_COLONIA_TB120() {
            return CLI_COLONIA_TB120;
        }

        public void setCLI_COLONIA_TB120(String CLI_COLONIA_TB120) {
            this.CLI_COLONIA_TB120 = CLI_COLONIA_TB120;
        }

        public String getCLI_TERMINATIONDATE_DOP() {
            return CLI_TERMINATIONDATE_DOP;
        }

        public void setCLI_TERMINATIONDATE_DOP(String CLI_TERMINATIONDATE_DOP) {
            this.CLI_TERMINATIONDATE_DOP = CLI_TERMINATIONDATE_DOP;
        }

        public String getCONT_LINEA_SPD() {
            return CONT_LINEA_SPD;
        }

        public void setCONT_LINEA_SPD(String CONT_LINEA_SPD) {
            this.CONT_LINEA_SPD = CONT_LINEA_SPD;
        }

        public int getLi_num() {
            return li_num;
        }

        public void setLi_num(int li_num) {
            this.li_num = li_num;
        }

        public String getCLI_CODZIP_TB120() {
            return CLI_CODZIP_TB120;
        }

        public void setCLI_CODZIP_TB120(String CLI_CODZIP_TB120) {
            this.CLI_CODZIP_TB120 = CLI_CODZIP_TB120;
        }

        public String getCLI_PAIS_SPD() {
            return CLI_PAIS_SPD;
        }

        public void setCLI_PAIS_SPD(String CLI_PAIS_SPD) {
            this.CLI_PAIS_SPD = CLI_PAIS_SPD;
        }

        // Getters and setters for all BpLineItem fields

    }
}
