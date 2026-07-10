package cl.codelco.controller;

import cl.codelco.service.ExcelCargaService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CargaController {

    private final ExcelCargaService service;

    public CargaController(ExcelCargaService service) {
        this.service = service;
    }

    @GetMapping("/cargar")
    public String cargarExternos() {
        service.cargarArchivo();
        return "✅ Carga completada";
    }
}