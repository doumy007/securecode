import math


CVSS_METRICS = {
    "SQL Injection": {"AV": "N", "AC": "L", "PR": "L", "UI": "N", "S": "C", "C": "H", "I": "H", "A": "H"},
    "XSS": {"AV": "N", "AC": "L", "PR": "N", "UI": "R", "S": "C", "C": "L", "I": "L", "A": "N"},
    "Hardcoded Secret": {"AV": "L", "AC": "L", "PR": "L", "UI": "N", "S": "C", "C": "H", "I": "H", "A": "N"},
    "Command Injection": {"AV": "N", "AC": "L", "PR": "L", "UI": "N", "S": "C", "C": "H", "I": "H", "A": "H"},
    "Path Traversal": {"AV": "N", "AC": "L", "PR": "L", "UI": "N", "S": "C", "C": "H", "I": "N", "A": "N"},
    "Insecure Cryptography": {"AV": "N", "AC": "L", "PR": "N", "UI": "R", "S": "C", "C": "H", "I": "N", "A": "N"},
    "Insecure Deserialization": {"AV": "N", "AC": "L", "PR": "N", "UI": "N", "S": "C", "C": "H", "I": "H", "A": "H"},
    "Docker - Root User": {"AV": "L", "AC": "L", "PR": "L", "UI": "N", "S": "C", "C": "H", "I": "H", "A": "H"},
    "Weak Hash": {"AV": "N", "AC": "L", "PR": "N", "UI": "R", "S": "C", "C": "L", "I": "L", "A": "N"},
}


class RiskCalculator:
    def calculate_cvss_v3(self, metrics: dict) -> float:
        av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
        ac = {"L": 0.77, "H": 0.44}
        pr = {"N": 0.85, "L": 0.62, "H": 0.27}
        ui = {"N": 0.85, "R": 0.62}
        s = {"U": 0, "C": 1}
        c = {"H": 0.56, "L": 0.22, "N": 0}
        i = {"H": 0.56, "L": 0.22, "N": 0}
        a = {"H": 0.56, "L": 0.22, "N": 0}

        iss = 1 - ((1 - c[metrics["C"]]) * (1 - i[metrics["I"]]) * (1 - a[metrics["A"]]))
        if s[metrics["S"]] == 0:
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15

        exploitability = 8.22 * av[metrics["AV"]] * ac[metrics["AC"]] * pr[metrics["PR"]] * ui[metrics["UI"]]

        if s[metrics["S"]] == 0:
            cvss = round(min(impact + exploitability, 10), 1)
        else:
            cvss = round(min(1.08 * (impact + exploitability), 10), 1)

        return max(0, cvss)

    def calculate_all(self, analysis: dict) -> dict:
        results = {}
        for vuln_type, metrics in CVSS_METRICS.items():
            cvss = self.calculate_cvss_v3(metrics)
            severity = self._severity_from_cvss(cvss)
            results[vuln_type] = {
                "cvss_score": cvss,
                "severidad": severity,
                "impacto": self._calculate_impact(metrics),
                "probabilidad": self._calculate_likelihood(metrics),
                "prioridad": "alta" if cvss >= 7.0 else "media" if cvss >= 4.0 else "baja",
            }
        return results

    def _severity_from_cvss(self, cvss: float) -> str:
        if cvss >= 9.0:
            return "crítica"
        if cvss >= 7.0:
            return "alta"
        if cvss >= 4.0:
            return "media"
        return "baja"

    def _calculate_impact(self, metrics: dict) -> str:
        impact_values = {
            "C": metrics.get("C", "N"),
            "I": metrics.get("I", "N"),
            "A": metrics.get("A", "N"),
        }
        high_count = sum(1 for v in impact_values.values() if v == "H")
        if high_count >= 2:
            return "alto"
        if high_count >= 1:
            return "medio"
        return "bajo"

    def _calculate_likelihood(self, metrics: dict) -> str:
        av = metrics.get("AV", "N")
        ac = metrics.get("AC", "L")
        pr = metrics.get("PR", "N")

        score = 0
        if av == "N":
            score += 3
        elif av == "A":
            score += 2
        else:
            score += 1

        if ac == "L":
            score += 2
        else:
            score += 1

        if pr == "N":
            score += 3
        elif pr == "L":
            score += 2
        else:
            score += 1

        if score >= 6:
            return "alta"
        if score >= 4:
            return "media"
        return "baja"

    def calculate_compliance_score(self, compliance_results: dict) -> float:
        total_checks = 0
        passed_checks = 0

        for vuln_type, mappings in compliance_results.items():
            if vuln_type == "overall_score":
                continue
            if isinstance(mappings, list) and len(mappings) > 0:
                total_checks += 1
                passed_checks += 1

        return round((passed_checks / max(total_checks, 1)) * 100, 1)
