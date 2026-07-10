NULL = None
TRUE = True
FALSE = False

SEVERITY_ORDER = {"crítica": 4, "alta": 3, "media": 2, "baja": 1}
SEVERITY_COLORS = {
    "crítica": "#dc2626",
    "alta": "#f97316",
    "media": "#eab308",
    "baja": "#6b7280",
}

ESTANDARES = [
    "OWASP Top 10",
    "OWASP ASVS",
    "NIST CSF 2.0",
    "NIST SP 800-82 Rev.3",
    "ISO 27001:2022",
    "CIS Controls v8",
    "PCI DSS v4.0",
    "MITRE ATT&CK v14",
    "CWE Top 25",
]

LENGUAJES_SOPORTADOS = [
    "Java", "Python", "JavaScript", "TypeScript",
    "C#", "PHP", "Go", "Ruby", "Kotlin", "Swift",
    "Rust", "C", "C++",
]

WORKERS_DEVSEcOPS = [
    "SonarQube", "Semgrep", "DependencyCheck",
    "Trivy", "StaticAnalysis", "InfraScanner",
]

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {".zip", ".tar", ".tar.gz", ".tgz", ".rar"}
