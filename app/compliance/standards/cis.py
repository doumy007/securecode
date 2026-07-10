CIS_CONTROLS = {
    "CIS Control 1": "Inventory and Control of Enterprise Assets",
    "CIS Control 2": "Inventory and Control of Software Assets",
    "CIS Control 3": "Data Protection",
    "CIS Control 4": "Secure Configuration of Enterprise Assets and Software",
    "CIS Control 5": "Account Management",
    "CIS Control 6": "Access Control Management",
    "CIS Control 7": "Continuous Vulnerability Management",
    "CIS Control 8": "Audit Log Management",
    "CIS Control 9": "Email and Web Browser Protections",
    "CIS Control 10": "Malware Defenses",
    "CIS Control 11": "Data Recovery",
    "CIS Control 12": "Network Infrastructure Management",
    "CIS Control 13": "Network Monitoring and Defense",
    "CIS Control 14": "Security Awareness and Skills Training",
    "CIS Control 15": "Service Provider Management",
    "CIS Control 16": "Application Software Security",
    "CIS Control 17": "Incident Response Management",
    "CIS Control 18": "Penetration Testing",
}


class CISRules:
    def evaluate(self, knowledge_base: dict) -> dict:
        code_verifiable = {
            "CIS Control 5": True,
            "CIS Control 6": True,
            "CIS Control 7": True,
            "CIS Control 8": True,
            "CIS Control 16": True,
        }

        result = {}
        for ctrl_id, name in CIS_CONTROLS.items():
            is_verifiable = ctrl_id in code_verifiable
            result[ctrl_id] = {
                "nombre": name,
                "verificable_por_codigo": is_verifiable,
            }

        total = len(CIS_CONTROLS)
        verified = sum(1 for k in result if result[k]["verificable_por_codigo"])

        return {
            "standard": "CIS Controls v8",
            "total_controls": total,
            "controls_verified_by_code": verified,
            "score": (verified / total) * 100 if total > 0 else 0,
            "detail": result,
        }
