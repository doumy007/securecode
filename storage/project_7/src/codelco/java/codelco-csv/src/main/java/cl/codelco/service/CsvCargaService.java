package cl.codelco.service;

import org.apache.commons.csv.*;
import org.apache.commons.io.input.BOMInputStream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.BatchPreparedStatementSetter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@Service
public class CsvCargaService {

    private final JdbcTemplate jdbcTemplate;

    @Value("${app.file.path}")
    private String filePath;

    public CsvCargaService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public String cargar() {

        List<CSVRecord> records = new ArrayList<>();

        try (
                InputStream is = new FileInputStream(filePath);
                Reader reader = new InputStreamReader(new BOMInputStream(is), StandardCharsets.UTF_8);
                CSVParser parser = new CSVParser(reader,
                        CSVFormat.DEFAULT
                                .withDelimiter('\t')
                                .withFirstRecordAsHeader()
                                .withIgnoreEmptyLines()
                                .withTrim())
        ) {

            parser.forEach(records::add);

        } catch (Exception e) {
            return "Error leyendo archivo: " + e.getMessage();
        }

        String sql = """
            INSERT INTO externoaconex (
            `No. de documento`,`Revisión`,`Título`,`Tipo`,`Estatus`,`Archivo`,
            `Fecha del hito`,`Fecha prevista de envío`,`Creado por`,
            `Notas adicionales`,`Adherencia Metodologica`,`Area Emisora`,
            `Código División`,`Código/Nombre Alternativo`,`Emisor/Origen`,
            `Especialidad`,`Estatus de Revisión`,`Fase`,`Gerencia/API`,
            `Nro. de Contrato`,`Proveedor`,`Rendición`,`Tipo de Documento`,
            `WBS`,`Sustituir`,`PathdeArchivo`,
            `Copia de Archivo a Disco F`,
            `enviado`,`procesado`,`peso`,
            `fecha_inicio`,`fecha_termino`,`existe_doc`,`version`
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """;

        int batchSize = 500;

        for (int i = 0; i < records.size(); i += batchSize) {

            int end = Math.min(i + batchSize, records.size());
            List<CSVRecord> batch = records.subList(i, end);

            jdbcTemplate.batchUpdate(sql, new BatchPreparedStatementSetter() {

                @Override
                public void setValues(PreparedStatement ps, int index) throws SQLException {

                    CSVRecord r = batch.get(index);

                    ps.setString(1, get(r, 0));
                    ps.setString(2, get(r, 1));
                    ps.setString(3, get(r, 2));
                    ps.setString(4, get(r, 3));
                    ps.setString(5, get(r, 4));
                    ps.setString(6, get(r, 5));
                    ps.setString(7, get(r, 6));
                    ps.setString(8, get(r, 7));
                    ps.setString(9, get(r, 8));
                    ps.setString(10, get(r, 9));
                    ps.setString(11, get(r, 10));
                    ps.setString(12, get(r, 11));
                    ps.setString(13, get(r, 12));
                    ps.setString(14, get(r, 13));
                    ps.setString(15, get(r, 14));
                    ps.setString(16, get(r, 15));
                    ps.setString(17, get(r, 16));
                    ps.setString(18, get(r, 17));
                    ps.setString(19, get(r, 18));
                    ps.setString(20, get(r, 19));
                    ps.setString(21, get(r, 20));
                    ps.setString(22, get(r, 21));
                    ps.setString(23, get(r, 22));
                    ps.setString(24, get(r, 23));
                    ps.setString(25, get(r, 24));
                    ps.setString(26, get(r, 25));

                    // copia disco F
                    ps.setString(27, get(r, 25));

                    ps.setInt(28, parseInt(get(r, 26)));
                    ps.setString(29, get(r, 27));
                    ps.setLong(30, parseLong(get(r, 28)));

                    ps.setTimestamp(31, null);
                    ps.setTimestamp(32, null);

                    ps.setInt(33, parseInt(get(r, 31)));
                    ps.setString(34, get(r, 32));
                }

                @Override
                public int getBatchSize() {
                    return batch.size();
                }
            });
        }

        return "Carga completada: " + records.size() + " registros";
    }

    private String get(CSVRecord r, int i) {
        try {
            String v = r.get(i);
            return (v == null || v.isBlank() || v.equalsIgnoreCase("NULL")) ? null : v.trim();
        } catch (Exception e) {
            return null;
        }
    }

    private int parseInt(String v) {
        try {
            return v != null ? Integer.parseInt(v) : 0;
        } catch (Exception e) {
            return 0;
        }
    }

    private long parseLong(String v) {
        try {
            return v != null ? Long.parseLong(v) : 0;
        } catch (Exception e) {
            return 0;
        }
    }
}