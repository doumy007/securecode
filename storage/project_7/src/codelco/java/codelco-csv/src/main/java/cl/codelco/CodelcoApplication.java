package cl.codelco;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication
@EnableFeignClients
public class CodelcoApplication {

    public static void main(String[] args) {
        SpringApplication.run(CodelcoApplication.class, args);
    }

}
