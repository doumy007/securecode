from typing import Optional


class OWASPRules:
    def evaluate(self, knowledge_base: dict) -> dict:
        categories = {
            "A01:2021-Broken Access Control": {
                "description": "Los mecanismos de control de acceso fallan con frecuencia",
                "controls_verified": ["Path Traversal", "Privilege Escalation"],
            },
            "A02:2021-Cryptographic Failures": {
                "description": "Fallos en criptografía que exponen datos sensibles",
                "controls_verified": ["Insecure Cryptography", "Weak Hash"],
            },
            "A03:2021-Injection": {
                "description": "Inyección SQL, OS Command, LDAP injection",
                "controls_verified": ["SQL Injection", "Command Injection", "XSS"],
            },
            "A04:2021-Insecure Design": {
                "description": "Fallas en el diseño de seguridad de la aplicación",
                "controls_verified": [],
            },
            "A05:2021-Security Misconfiguration": {
                "description": "Configuraciones de seguridad incorrectas o incompletas",
                "controls_verified": ["Docker - Root User", "Docker - Latest Tag"],
            },
            "A06:2021-Vulnerable and Outdated Components": {
                "description": "Uso de componentes con vulnerabilidades conocidas",
                "controls_verified": ["CVE"],
            },
            "A07:2021-Identification and Authentication Failures": {
                "description": "Fallos en autenticación y gestión de identidades",
                "controls_verified": ["Hardcoded Secret"],
            },
            "A08:2021-Software and Data Integrity Failures": {
                "description": "Fallos en integridad de software y datos",
                "controls_verified": ["Insecure Deserialization"],
            },
            "A09:2021-Security Logging and Monitoring Failures": {
                "description": "Fallos en logging y monitoreo de seguridad",
                "controls_verified": [],
            },
            "A10:2021-Server-Side Request Forgery (SSRF)": {
                "description": "Solicitudes del lado del servidor no validadas",
                "controls_verified": [],
            },
        }

        matched = []
        for vuln_type, mappings in knowledge_base.items():
            for mapping in mappings:
                if isinstance(mapping, dict):
                    for _, category in mapping.items():
                        if isinstance(category, str) and category.startswith("A0") and ":2021" in category:
                            matched.append({
                                "vulnerabilidad": vuln_type,
                                "categoria_owasp": category,
                            })

        found_categories = set(m["categoria_owasp"] for m in matched)
        total_categories = len(categories)
        verified = len(found_categories)
        score = (verified / total_categories) * 100 if total_categories > 0 else 0

        return {
            "standard": "OWASP Top 10 (2021)",
            "total_categories": total_categories,
            "categories_with_findings": verified,
            "score": score,
            "matched_vulnerabilities": matched,
            "categories_detail": {
                cat: {
                    "status": "affected" if cat in found_categories else "not_affected",
                    "description": info["description"],
                    "verified_controls": info["controls_verified"],
                }
                for cat, info in categories.items()
            },
        }
