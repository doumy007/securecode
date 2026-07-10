CONTROLES_NIST_CSF = {
    "Govern": {
        "GV.OC": "Organizational Context",
        "GV.RM": "Risk Management Strategy",
        "GV.RR": "Roles and Responsibilities",
        "GV.PO": "Policy",
        "GV.SC": "Supply Chain Risk Management",
    },
    "Identify": {
        "ID.AM": "Asset Management",
        "ID.RA": "Risk Assessment",
        "ID.IM": "Improvement",
    },
    "Protect": {
        "PR.AC": "Identity Management and Access Control",
        "PR.AW": "Awareness and Training",
        "PR.DS": "Data Security",
        "PR.PT": "Protective Technology",
        "PR.IR": "Information Protection Processes and Procedures",
        "PR.MA": "Maintenance",
    },
    "Detect": {
        "DE.AE": "Anomalies and Events",
        "DE.CM": "Continuous Monitoring",
        "DE.DP": "Detection Processes",
    },
    "Respond": {
        "RS.MA": "Incident Management",
        "RS.CO": "Communications",
        "RS.AN": "Analysis",
        "RS.MI": "Mitigation",
    },
    "Recover": {
        "RC.RP": "Recovery Plan",
        "RC.IM": "Improvements",
        "RC.CO": "Communications",
    },
}


class NISTCSFRules:
    def evaluate(self, knowledge_base: dict) -> dict:
        result = {}
        for function, categories in CONTROLES_NIST_CSF.items():
            result[function] = {}
            for cat_id, cat_name in categories.items():
                result[function][cat_id] = self._evaluate_category(cat_id, knowledge_base)

        total = sum(len(cats) for cats in CONTROLES_NIST_CSF.values())
        verified = sum(
            1 for func in result.values() for cat in func.values() if cat.get("verificable_por_codigo")
        )

        return {
            "standard": "NIST CSF 2.0",
            "total_controls": total,
            "controls_verified_by_code": verified,
            "score": (verified / total) * 100 if total > 0 else 0,
            "detail": result,
        }

    def _evaluate_category(self, cat_id: str, knowledge_base: dict) -> dict:
        code_verifiable_categories = {
            "PR.AC": True, "PR.DS": True, "PR.PT": True,
            "DE.AE": True, "DE.CM": True,
            "ID.RA": True,
        }

        is_verifiable = cat_id in code_verifiable_categories

        return {
            "verificable_por_codigo": is_verifiable,
            "estado": "verificable" if is_verifiable else "requiere_evidencia_externa",
            "hallazgos": [],
            "nota": "" if is_verifiable else "NO ES POSIBLE VALIDAR CON EL CÓDIGO - Requiere políticas, procedimientos y evidencia documental",
        }
