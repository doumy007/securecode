package cl.codelco.domain;

import java.util.List;

public class ResponseCliente {
    private List<Data> data;
    private List<String> message;
    private int status;

    public List<Data> getData() {
        return data;
    }

    public void setData(List<Data> data) {
        this.data = data;
    }

    public List<String> getMessage() {
        return message;
    }

    public void setMessage(List<String> message) {
        this.message = message;
    }

    public int getStatus() {
        return status;
    }

    public void setStatus(int status) {
        this.status = status;
    }

    public static class Data {
        private String uuu_creation_date;
        private String uuu_record_last_update_date;
        private String CLI_PARTYNUMBER_TB32;
        private String LI_RECORDNO_TB50;
        private String PATH1;
        private String CLI_RFC_TB120;
        private String PATH2;
        private String CLI_CODIGOIMP_TB50;
        private List<LineItem> _bp_lineitems;
        private String CLI_ESTABLISHEDDATE_DOP;
        private String record_no;
        private String CLI_RAZON_SOCIAL_TB500;
        private String CLI_NOMBRECOMERCIAL_TB500;
        private String creator_id;
        private int CLI_NADJUNTOS_INT;
        private String CLI_TERMINATIONDATE_DOP;
        private String uuu_dm_publish_path;
        private String PRCLI_CREARCLIENTE_BPC;
        private String uuu_dm_record_info_path;
        private String status;
        private String CLI_NUMCLI_TB50;

        public String getUuu_creation_date() {
            return uuu_creation_date;
        }

        public void setUuu_creation_date(String uuu_creation_date) {
            this.uuu_creation_date = uuu_creation_date;
        }

        public String getUuu_record_last_update_date() {
            return uuu_record_last_update_date;
        }

        public void setUuu_record_last_update_date(String uuu_record_last_update_date) {
            this.uuu_record_last_update_date = uuu_record_last_update_date;
        }

        public String getCLI_PARTYNUMBER_TB32() {
            return CLI_PARTYNUMBER_TB32;
        }

        public void setCLI_PARTYNUMBER_TB32(String CLI_PARTYNUMBER_TB32) {
            this.CLI_PARTYNUMBER_TB32 = CLI_PARTYNUMBER_TB32;
        }

        public String getLI_RECORDNO_TB50() {
            return LI_RECORDNO_TB50;
        }

        public void setLI_RECORDNO_TB50(String LI_RECORDNO_TB50) {
            this.LI_RECORDNO_TB50 = LI_RECORDNO_TB50;
        }

        public String getPATH1() {
            return PATH1;
        }

        public void setPATH1(String PATH1) {
            this.PATH1 = PATH1;
        }

        public String getCLI_RFC_TB120() {
            return CLI_RFC_TB120;
        }

        public void setCLI_RFC_TB120(String CLI_RFC_TB120) {
            this.CLI_RFC_TB120 = CLI_RFC_TB120;
        }

        public String getPATH2() {
            return PATH2;
        }

        public void setPATH2(String PATH2) {
            this.PATH2 = PATH2;
        }

        public String getCLI_CODIGOIMP_TB50() {
            return CLI_CODIGOIMP_TB50;
        }

        public void setCLI_CODIGOIMP_TB50(String CLI_CODIGOIMP_TB50) {
            this.CLI_CODIGOIMP_TB50 = CLI_CODIGOIMP_TB50;
        }

        public List<LineItem> get_bp_lineitems() {
            return _bp_lineitems;
        }

        public void set_bp_lineitems(List<LineItem> _bp_lineitems) {
            this._bp_lineitems = _bp_lineitems;
        }

        public String getCLI_ESTABLISHEDDATE_DOP() {
            return CLI_ESTABLISHEDDATE_DOP;
        }

        public void setCLI_ESTABLISHEDDATE_DOP(String CLI_ESTABLISHEDDATE_DOP) {
            this.CLI_ESTABLISHEDDATE_DOP = CLI_ESTABLISHEDDATE_DOP;
        }

        public String getRecord_no() {
            return record_no;
        }

        public void setRecord_no(String record_no) {
            this.record_no = record_no;
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

        public String getCreator_id() {
            return creator_id;
        }

        public void setCreator_id(String creator_id) {
            this.creator_id = creator_id;
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

        public String getUuu_dm_publish_path() {
            return uuu_dm_publish_path;
        }

        public void setUuu_dm_publish_path(String uuu_dm_publish_path) {
            this.uuu_dm_publish_path = uuu_dm_publish_path;
        }

        public String getPRCLI_CREARCLIENTE_BPC() {
            return PRCLI_CREARCLIENTE_BPC;
        }

        public void setPRCLI_CREARCLIENTE_BPC(String PRCLI_CREARCLIENTE_BPC) {
            this.PRCLI_CREARCLIENTE_BPC = PRCLI_CREARCLIENTE_BPC;
        }

        public String getUuu_dm_record_info_path() {
            return uuu_dm_record_info_path;
        }

        public void setUuu_dm_record_info_path(String uuu_dm_record_info_path) {
            this.uuu_dm_record_info_path = uuu_dm_record_info_path;
        }

        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public String getCLI_NUMCLI_TB50() {
            return CLI_NUMCLI_TB50;
        }

        public void setCLI_NUMCLI_TB50(String CLI_NUMCLI_TB50) {
            this.CLI_NUMCLI_TB50 = CLI_NUMCLI_TB50;
        }

        // Add getters and setters for the rest of the fields

        public static class LineItem {
            private String CLIE_InvoiceCurrency_SPD;
            private String CLI_PAIS_TB16;
            private String CLI_CUSTOMERTYPE_TB4;
            private String CLI_REFBANCARIA_TB50;
            private String CONT_FUTURO_SPD;
            private String CLI_eMail_TB255;
            private String uuu_tab_id;
            private String CONT_INTER_SPD;
            private String LI_RECORDNO_TB50;
            private String FACT_CPAGO_SPD;
            private String CLI_CUENTACONTABLE_SPD;
            private String CONT_UNINEGOCIO_PKBP;
            private String FACT_MPAGO_SPD;
            private String CLI_PRINCIPAL_ICB;
            private String CLI_ACCOUNTINFORMATION_TB50;
            private String CLI_PersonFirstName_TB255;
            private String CLI_DELEGACION_TB120;
            private String CONT_CODECOMBINATION_TB50;
            private String CLI_ESTABLISHEDDATE_DOP;
            private String CLI_TERMINATIONDATE_DOP;
            private String CLI_REGIMEN_FISCAL_SPD;
            private String CONT_LINEA_SPD;
            private String CLI_SITEUSECODE_TB50;
            private String CLI_CIUDAD_TB120;
            private String UN_NAME_TB4;
            private String CLI_CODZIP_TB120;
            private String CLI_PAIS_SPD;
            private String CLI_ESTADO_TB120;
            private String CLI_DIRECPRINC_TB255;
            private String CLI_CUSTOMERCLASS_TB250;
            private String CLI_LOCATION_TB250;
            private String CLI_ACCOUNTNUMBER_TB50;
            private String CLIE_NUMEROPROYECTO_SPD;
            private String CLI_LOCALIDAD_TB120;
            private String CLI_USOCFDI_SPD;
            private String hidden_shortdesc;
            private String CLI_PARTYSITENUMBER_TB50;
            private String CONT_CENTRO_SPD;
            private String CONT_UNIDAD_SPD;
            private int tab_id;
            private String CLI_PersonLastName_TB255;
            private String CLI_ACCOUNTNAME_TB255;
            private String CLI_PARTYSITENAME_TB255;
            private String CLI_COLONIA_TB120;
            private String CLI_CUSTOMERCLASS_SPD;
            private String short_desc;
            private int li_num;
            private String FACT_FPAGO_SPD;

            public String getCLIE_InvoiceCurrency_SPD() {
                return CLIE_InvoiceCurrency_SPD;
            }

            public void setCLIE_InvoiceCurrency_SPD(String CLIE_InvoiceCurrency_SPD) {
                this.CLIE_InvoiceCurrency_SPD = CLIE_InvoiceCurrency_SPD;
            }

            public String getCLI_PAIS_TB16() {
                return CLI_PAIS_TB16;
            }

            public void setCLI_PAIS_TB16(String CLI_PAIS_TB16) {
                this.CLI_PAIS_TB16 = CLI_PAIS_TB16;
            }

            public String getCLI_CUSTOMERTYPE_TB4() {
                return CLI_CUSTOMERTYPE_TB4;
            }

            public void setCLI_CUSTOMERTYPE_TB4(String CLI_CUSTOMERTYPE_TB4) {
                this.CLI_CUSTOMERTYPE_TB4 = CLI_CUSTOMERTYPE_TB4;
            }

            public String getCLI_REFBANCARIA_TB50() {
                return CLI_REFBANCARIA_TB50;
            }

            public void setCLI_REFBANCARIA_TB50(String CLI_REFBANCARIA_TB50) {
                this.CLI_REFBANCARIA_TB50 = CLI_REFBANCARIA_TB50;
            }

            public String getCONT_FUTURO_SPD() {
                return CONT_FUTURO_SPD;
            }

            public void setCONT_FUTURO_SPD(String CONT_FUTURO_SPD) {
                this.CONT_FUTURO_SPD = CONT_FUTURO_SPD;
            }

            public String getCLI_eMail_TB255() {
                return CLI_eMail_TB255;
            }

            public void setCLI_eMail_TB255(String CLI_eMail_TB255) {
                this.CLI_eMail_TB255 = CLI_eMail_TB255;
            }

            public String getUuu_tab_id() {
                return uuu_tab_id;
            }

            public void setUuu_tab_id(String uuu_tab_id) {
                this.uuu_tab_id = uuu_tab_id;
            }

            public String getCONT_INTER_SPD() {
                return CONT_INTER_SPD;
            }

            public void setCONT_INTER_SPD(String CONT_INTER_SPD) {
                this.CONT_INTER_SPD = CONT_INTER_SPD;
            }

            public String getLI_RECORDNO_TB50() {
                return LI_RECORDNO_TB50;
            }

            public void setLI_RECORDNO_TB50(String LI_RECORDNO_TB50) {
                this.LI_RECORDNO_TB50 = LI_RECORDNO_TB50;
            }

            public String getFACT_CPAGO_SPD() {
                return FACT_CPAGO_SPD;
            }

            public void setFACT_CPAGO_SPD(String FACT_CPAGO_SPD) {
                this.FACT_CPAGO_SPD = FACT_CPAGO_SPD;
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

            public String getFACT_MPAGO_SPD() {
                return FACT_MPAGO_SPD;
            }

            public void setFACT_MPAGO_SPD(String FACT_MPAGO_SPD) {
                this.FACT_MPAGO_SPD = FACT_MPAGO_SPD;
            }

            public String getCLI_PRINCIPAL_ICB() {
                return CLI_PRINCIPAL_ICB;
            }

            public void setCLI_PRINCIPAL_ICB(String CLI_PRINCIPAL_ICB) {
                this.CLI_PRINCIPAL_ICB = CLI_PRINCIPAL_ICB;
            }

            public String getCLI_ACCOUNTINFORMATION_TB50() {
                return CLI_ACCOUNTINFORMATION_TB50;
            }

            public void setCLI_ACCOUNTINFORMATION_TB50(String CLI_ACCOUNTINFORMATION_TB50) {
                this.CLI_ACCOUNTINFORMATION_TB50 = CLI_ACCOUNTINFORMATION_TB50;
            }

            public String getCLI_PersonFirstName_TB255() {
                return CLI_PersonFirstName_TB255;
            }

            public void setCLI_PersonFirstName_TB255(String CLI_PersonFirstName_TB255) {
                this.CLI_PersonFirstName_TB255 = CLI_PersonFirstName_TB255;
            }

            public String getCLI_DELEGACION_TB120() {
                return CLI_DELEGACION_TB120;
            }

            public void setCLI_DELEGACION_TB120(String CLI_DELEGACION_TB120) {
                this.CLI_DELEGACION_TB120 = CLI_DELEGACION_TB120;
            }

            public String getCONT_CODECOMBINATION_TB50() {
                return CONT_CODECOMBINATION_TB50;
            }

            public void setCONT_CODECOMBINATION_TB50(String CONT_CODECOMBINATION_TB50) {
                this.CONT_CODECOMBINATION_TB50 = CONT_CODECOMBINATION_TB50;
            }

            public String getCLI_ESTABLISHEDDATE_DOP() {
                return CLI_ESTABLISHEDDATE_DOP;
            }

            public void setCLI_ESTABLISHEDDATE_DOP(String CLI_ESTABLISHEDDATE_DOP) {
                this.CLI_ESTABLISHEDDATE_DOP = CLI_ESTABLISHEDDATE_DOP;
            }

            public String getCLI_TERMINATIONDATE_DOP() {
                return CLI_TERMINATIONDATE_DOP;
            }

            public void setCLI_TERMINATIONDATE_DOP(String CLI_TERMINATIONDATE_DOP) {
                this.CLI_TERMINATIONDATE_DOP = CLI_TERMINATIONDATE_DOP;
            }

            public String getCLI_REGIMEN_FISCAL_SPD() {
                return CLI_REGIMEN_FISCAL_SPD;
            }

            public void setCLI_REGIMEN_FISCAL_SPD(String CLI_REGIMEN_FISCAL_SPD) {
                this.CLI_REGIMEN_FISCAL_SPD = CLI_REGIMEN_FISCAL_SPD;
            }

            public String getCONT_LINEA_SPD() {
                return CONT_LINEA_SPD;
            }

            public void setCONT_LINEA_SPD(String CONT_LINEA_SPD) {
                this.CONT_LINEA_SPD = CONT_LINEA_SPD;
            }

            public String getCLI_SITEUSECODE_TB50() {
                return CLI_SITEUSECODE_TB50;
            }

            public void setCLI_SITEUSECODE_TB50(String CLI_SITEUSECODE_TB50) {
                this.CLI_SITEUSECODE_TB50 = CLI_SITEUSECODE_TB50;
            }

            public String getCLI_CIUDAD_TB120() {
                return CLI_CIUDAD_TB120;
            }

            public void setCLI_CIUDAD_TB120(String CLI_CIUDAD_TB120) {
                this.CLI_CIUDAD_TB120 = CLI_CIUDAD_TB120;
            }

            public String getUN_NAME_TB4() {
                return UN_NAME_TB4;
            }

            public void setUN_NAME_TB4(String UN_NAME_TB4) {
                this.UN_NAME_TB4 = UN_NAME_TB4;
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

            public String getCLI_ESTADO_TB120() {
                return CLI_ESTADO_TB120;
            }

            public void setCLI_ESTADO_TB120(String CLI_ESTADO_TB120) {
                this.CLI_ESTADO_TB120 = CLI_ESTADO_TB120;
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

            public String getCLI_LOCATION_TB250() {
                return CLI_LOCATION_TB250;
            }

            public void setCLI_LOCATION_TB250(String CLI_LOCATION_TB250) {
                this.CLI_LOCATION_TB250 = CLI_LOCATION_TB250;
            }

            public String getCLI_ACCOUNTNUMBER_TB50() {
                return CLI_ACCOUNTNUMBER_TB50;
            }

            public void setCLI_ACCOUNTNUMBER_TB50(String CLI_ACCOUNTNUMBER_TB50) {
                this.CLI_ACCOUNTNUMBER_TB50 = CLI_ACCOUNTNUMBER_TB50;
            }

            public String getCLIE_NUMEROPROYECTO_SPD() {
                return CLIE_NUMEROPROYECTO_SPD;
            }

            public void setCLIE_NUMEROPROYECTO_SPD(String CLIE_NUMEROPROYECTO_SPD) {
                this.CLIE_NUMEROPROYECTO_SPD = CLIE_NUMEROPROYECTO_SPD;
            }

            public String getCLI_LOCALIDAD_TB120() {
                return CLI_LOCALIDAD_TB120;
            }

            public void setCLI_LOCALIDAD_TB120(String CLI_LOCALIDAD_TB120) {
                this.CLI_LOCALIDAD_TB120 = CLI_LOCALIDAD_TB120;
            }

            public String getCLI_USOCFDI_SPD() {
                return CLI_USOCFDI_SPD;
            }

            public void setCLI_USOCFDI_SPD(String CLI_USOCFDI_SPD) {
                this.CLI_USOCFDI_SPD = CLI_USOCFDI_SPD;
            }

            public String getHidden_shortdesc() {
                return hidden_shortdesc;
            }

            public void setHidden_shortdesc(String hidden_shortdesc) {
                this.hidden_shortdesc = hidden_shortdesc;
            }

            public String getCLI_PARTYSITENUMBER_TB50() {
                return CLI_PARTYSITENUMBER_TB50;
            }

            public void setCLI_PARTYSITENUMBER_TB50(String CLI_PARTYSITENUMBER_TB50) {
                this.CLI_PARTYSITENUMBER_TB50 = CLI_PARTYSITENUMBER_TB50;
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

            public int getTab_id() {
                return tab_id;
            }

            public void setTab_id(int tab_id) {
                this.tab_id = tab_id;
            }

            public String getCLI_PersonLastName_TB255() {
                return CLI_PersonLastName_TB255;
            }

            public void setCLI_PersonLastName_TB255(String CLI_PersonLastName_TB255) {
                this.CLI_PersonLastName_TB255 = CLI_PersonLastName_TB255;
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

            public String getCLI_COLONIA_TB120() {
                return CLI_COLONIA_TB120;
            }

            public void setCLI_COLONIA_TB120(String CLI_COLONIA_TB120) {
                this.CLI_COLONIA_TB120 = CLI_COLONIA_TB120;
            }

            public String getCLI_CUSTOMERCLASS_SPD() {
                return CLI_CUSTOMERCLASS_SPD;
            }

            public void setCLI_CUSTOMERCLASS_SPD(String CLI_CUSTOMERCLASS_SPD) {
                this.CLI_CUSTOMERCLASS_SPD = CLI_CUSTOMERCLASS_SPD;
            }

            public String getShort_desc() {
                return short_desc;
            }

            public void setShort_desc(String short_desc) {
                this.short_desc = short_desc;
            }

            public int getLi_num() {
                return li_num;
            }

            public void setLi_num(int li_num) {
                this.li_num = li_num;
            }

            public String getFACT_FPAGO_SPD() {
                return FACT_FPAGO_SPD;
            }

            public void setFACT_FPAGO_SPD(String FACT_FPAGO_SPD) {
                this.FACT_FPAGO_SPD = FACT_FPAGO_SPD;
            }

            // Add getters and setters for line item fields
        }
    }
}