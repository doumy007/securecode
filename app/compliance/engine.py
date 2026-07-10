from app.compliance.standards.owasp import OWASPRules
from app.compliance.standards.nist_csf import NISTCSFRules
from app.compliance.standards.nist_800_82 import NIST80082Rules
from app.compliance.standards.iso_27001 import ISO27001Rules
from app.compliance.standards.cis import CISRules
from app.compliance.standards.mitre_attck import MITREAttckRules
from app.compliance.risk_calculator import RiskCalculator
import logging
from typing import Optional

logger = logging.getLogger("securecode.compliance")


class ComplianceEngine:
    def __init__(self):
        self.rulesets = {
            "owasp": OWASPRules(),
            "nist_csf": NISTCSFRules(),
            "nist_800_82": NIST80082Rules(),
            "iso_27001": ISO27001Rules(),
            "cis": CISRules(),
            "mitre_attck": MITREAttckRules(),
        }
        self.risk_calculator = RiskCalculator()
        self.knowledge_base = self._build_knowledge_base()

    def _build_knowledge_base(self) -> dict:
        return {
            "SQL Injection": {
                "owasp": [{"categoria": "A03:2021-Injection", "referencia": "OWASP Top 10 A03"}],
                "cwe": ["CWE-89: SQL Injection"],
                "nist_csf": ["PR.DS: Data Security"],
                "nist_800_82": ["SI-10: Information Input Validation"],
                "iso_27001": ["A.8.2: Information classification"],
                "cis": ["CIS Control 6: Access Control Management"],
                "mitre_attck": ["T1190: Exploit Public-Facing Application"],
            },
            "XSS": {
                "owasp": [{"categoria": "A03:2021-Injection", "referencia": "OWASP Top 10 A03"}],
                "cwe": ["CWE-79: Cross-site Scripting"],
                "nist_csf": ["PR.AC: Identity Management and Access Control"],
                "nist_800_82": ["SI-10: Information Input Validation"],
                "iso_27001": ["A.8.2: Information classification"],
                "cis": ["CIS Control 6: Access Control Management"],
            },
            "Hardcoded Secret": {
                "owasp": [{"categoria": "A07:2021-Identification and Authentication Failures", "referencia": "OWASP Top 10 A07"}],
                "cwe": ["CWE-798: Use of Hard-coded Credentials"],
                "nist_csf": ["PR.AC: Identity Management and Access Control"],
                "nist_800_82": ["IA-5: Authenticator Management"],
                "iso_27001": ["A.9.2: User access management"],
                "cis": ["CIS Control 5: Account Management"],
            },
            "Command Injection": {
                "owasp": [{"categoria": "A03:2021-Injection", "referencia": "OWASP Top 10 A03"}],
                "cwe": ["CWE-78: OS Command Injection"],
                "nist_csf": ["PR.PT: Protective Technology"],
                "nist_800_82": ["SI-10: Information Input Validation"],
                "iso_27001": ["A.8.2: Information classification"],
            },
            "Path Traversal": {
                "owasp": [{"categoria": "A01:2021-Broken Access Control", "referencia": "OWASP Top 10 A01"}],
                "cwe": ["CWE-22: Improper Limitation of a Pathname"],
                "nist_csf": ["PR.AC: Access Control"],
                "nist_800_82": ["AC-3: Access Enforcement"],
                "iso_27001": ["A.9.1: Access control policy"],
            },
            "Insecure Cryptography": {
                "owasp": [{"categoria": "A02:2021-Cryptographic Failures", "referencia": "OWASP Top 10 A02"}],
                "cwe": ["CWE-327: Use of a Broken or Risky Cryptographic Algorithm"],
                "nist_csf": ["PR.DS: Data Security"],
                "nist_800_82": ["SC-13: Cryptographic Protection"],
                "iso_27001": ["A.10.1: Cryptographic controls"],
            },
            "Insecure Deserialization": {
                "owasp": [{"categoria": "A08:2021-Software and Data Integrity Failures", "referencia": "OWASP Top 10 A08"}],
                "cwe": ["CWE-502: Deserialization of Untrusted Data"],
                "nist_csf": ["PR.DS: Data Security"],
                "nist_800_82": ["SI-10: Information Input Validation"],
                "iso_27001": ["A.8.2: Information classification"],
            },
            "CVE": {
                "nist_csf": ["ID.RA: Risk Assessment"],
                "nist_800_82": ["RA-5: Vulnerability Scanning"],
                "iso_27001": ["A.12.6: Technical vulnerability management"],
                "cis": ["CIS Control 7: Continuous Vulnerability Management"],
            },
            "Docker - Root User": {
                "nist_csf": ["PR.AC: Access Control"],
                "nist_800_82": ["AC-6: Least Privilege"],
                "cis": ["CIS Docker Benchmark 4.1: Ensure container runs as non-root user"],
            },
            "Docker - Latest Tag": {
                "nist_csf": ["ID.RA: Risk Assessment"],
                "nist_800_82": ["SA-10: Developer Configuration Management"],
            },
            "Weak Hash": {
                "owasp": [{"categoria": "A02:2021-Cryptographic Failures", "referencia": "OWASP Top 10 A02"}],
                "cwe": ["CWE-328: Use of Weak Hash"],
                "nist_csf": ["PR.DS: Data Security"],
                "nist_800_82": ["SC-13: Cryptographic Protection"],
            },
            "K8s - Privileged Container": {
                "nist_csf": ["PR.AC: Access Control"],
                "nist_800_82": ["AC-6: Least Privilege"],
                "cis": ["CIS Kubernetes Benchmark 5.2.1: Ensure privileged containers are not used"],
            },
        }

    def evaluate(self, ai_analysis: dict) -> dict:
        results = {}
        overall_scores = []

        for vuln_type in self.knowledge_base:
            mappings = self.knowledge_base[vuln_type]
            results[vuln_type] = []

            for standard, rules in mappings.items():
                if isinstance(rules, list):
                    for rule in rules:
                        if isinstance(rule, dict):
                            results[vuln_type].append({
                                "estandar": standard.upper(),
                                "categoria": rule.get("categoria", ""),
                                "referencia": rule.get("referencia", ""),
                            })
                        else:
                            results[vuln_type].append({
                                "estandar": standard.upper(),
                                "categoria": rule,
                                "referencia": rule,
                            })

        total_controls = sum(len(v) for v in results.values())
        results["overall_score"] = self.risk_calculator.calculate_compliance_score(results)

        for standard_name, ruleset in self.rulesets.items():
            standard_results = ruleset.evaluate(self.knowledge_base)
            results[standard_name] = standard_results
            if "score" in standard_results:
                overall_scores.append(standard_results["score"])

        if overall_scores:
            results["overall_score"] = sum(overall_scores) / len(overall_scores)

        return results
