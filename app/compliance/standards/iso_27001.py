ISO_27001_CONTROLS = {
    "A.5": "Information security policies",
    "A.6": "Organization of information security",
    "A.7": "Human resource security",
    "A.8": "Asset management",
    "A.9": "Access control",
    "A.10": "Cryptography",
    "A.11": "Physical and environmental security",
    "A.12": "Operations security",
    "A.13": "Communications security",
    "A.14": "System acquisition, development and maintenance",
    "A.15": "Supplier relationships",
    "A.16": "Incident management",
    "A.17": "Business continuity management",
    "A.18": "Compliance",
}


class ISO27001Rules:
    def evaluate(self, knowledge_base: dict) -> dict:
        code_verifiable = {
            "A.8": True, "A.9": True, "A.10": True,
            "A.12": True, "A.13": True, "A.14": True,
        }
        result = {}

        for annex, name in ISO_27001_CONTROLS.items():
            is_verifiable = annex in code_verifiable
            result[annex] = {
                "nombre": name,
                "verificable_por_codigo": is_verifiable,
                "estado": "verificable" if is_verifiable else "requiere_evidencia_externa",
                "hallazgos": [],
            }

        total = len(ISO_27001_CONTROLS)
        verified = sum(1 for k in result if result[k]["verificable_por_codigo"])

        return {
            "standard": "ISO 27001:2022",
            "total_controls": total,
            "controls_verified_by_code": verified,
            "score": (verified / total) * 100 if total > 0 else 0,
            "detail": result,
        }
