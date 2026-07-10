package cl.codelco.service;

import cl.codelco.service.ExcelCargaService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class AutoRun implements CommandLineRunner {

    private final ExcelCargaService service;

    public AutoRun(ExcelCargaService service) {
        this.service = service;
    }

    @Override
    public void run(String... args) {
        System.out.println("🚀 Ejecutando carga automática...");

        service.cargarArchivo();

        System.out.println("✅ Carga finalizada");

        System.exit(0); // 🔥 CIERRA LA APP AUTOMÁTICAMENTE
    }
}
