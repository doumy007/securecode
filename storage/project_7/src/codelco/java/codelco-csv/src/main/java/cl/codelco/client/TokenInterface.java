package cl.codelco.client;

import cl.codelco.domain.TokenResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;


@FeignClient(name = "${service.login.name}",url = "${unifier.url_rest}")
public interface TokenInterface {
    @GetMapping(value = "/service/v1/login",produces = {MediaType.APPLICATION_JSON_VALUE},headers = "Authorization=Basic ${unifier.interlock}")
    TokenResponse retrieveToken();



}
