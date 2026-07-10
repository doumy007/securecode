package cl.codelco.service;

import org.apache.poi.ss.usermodel.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.io.FileInputStream;
import java.io.InputStream;
import java.sql.Types;

@Service
public class ExcelCargaService {

    private final JdbcTemplate jdbcTemplate;

    @Value("${app.file.path}")
    private String filePath;

    public ExcelCargaService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void cargarArchivo() {

        String sql = """
            INSERT INTO externoaconex (
                `No. de documento`, `Revisión`, `Título`, `Tipo`, `Estatus`, `Archivo`,
                `Fecha del hito`, `Fecha prevista de envío`, `Creado por`, `Notas adicionales`,
                `Adherencia Metodologica`, `Area Emisora`, `Código División`,
                `Código/Nombre Alternativo`, `Emisor/Origen`, `Especialidad`,
                `Estatus de Revisión`, `Fase`, `Gerencia/API`, `Nro. de Contrato`,
                `Proveedor`, `Rendición`, `Tipo de Documento`, `WBS`, `Sustituir`,
                `PathdeArchivo`, `enviado`, `procesado`, `peso`,
                `fecha_inicio`, `fecha_termino`, `existe_doc`, `version`
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """;

        try (InputStream is = new FileInputStream(filePath);
             Workbook workbook = WorkbookFactory.create(is)) {

            Sheet sheet = workbook.getSheetAt(0);

            for (int i = 1; i <= sheet.getLastRowNum(); i++) {

                Row row = sheet.getRow(i);
                if (row == null) continue;

                try {
                    jdbcTemplate.update(sql,
                            getString(row, 0),
                            getString(row, 1),
                            getString(row, 2),
                            getString(row, 3),
                            getString(row, 4),
                            getString(row, 5),
                            getString(row, 6),
                            getString(row, 7),
                            getString(row, 8),
                            getString(row, 9),
                            getString(row, 10),
                            getString(row, 11),
                            getString(row, 12),
                            getString(row, 13),
                            getString(row, 14),
                            getString(row, 15),
                            getString(row, 16),
                            getString(row, 17),
                            getString(row, 18),
                            getString(row, 19),
                            getString(row, 20),
                            getString(row, 21),
                            getString(row, 22),
                            getString(row, 23),
                            getString(row, 24),
                            getString(row, 25),
                            getInt(row, 26),
                            getInt(row, 27),
                            getInt(row, 28),
                            getDate(row, 29), // 🔥 FIX
                            getDate(row, 30), // 🔥 FIX
                            getInt(row, 31),
                            getInt(row, 32)
                    );

                } catch (Exception e) {
                    System.out.println("⚠ Error en fila " + (i + 1) + ": " + e.getMessage());
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // =========================
    // HELPERS 🔥 IMPORTANTES
    // =========================

    private String getString(Row row, int index) {
        Cell cell = row.getCell(index);
        if (cell == null) return null;

        cell.setCellType(CellType.STRING);
        String value = cell.getStringCellValue().trim();

        if (value.isEmpty() || value.equalsIgnoreCase("NULL")) {
            return null; // 🔥 CLAVE
        }

        return value;
    }

    private Integer getInt(Row row, int index) {
        String value = getString(row, index);
        if (value == null) return 0;
        return Integer.parseInt(value);
    }

    private Object getDate(Row row, int index) {
        String value = getString(row, index);

        if (value == null) {
            return null; // 🔥 ESTO EVITA EL ERROR
        }

        return value; // si luego quieres parsear a Date real te lo hago
    }
}