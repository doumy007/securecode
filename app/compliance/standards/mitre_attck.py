MITRE_ATTACK_TECHNIQUES = {
    "T1190": "Exploit Public-Facing Application",
    "T1195": "Supply Chain Compromise",
    "T1078": "Valid Accounts",
    "T1134": "Access Token Manipulation",
    "T1548": "Abuse Elevation Control Mechanism",
    "T1550": "Use Alternate Authentication Material",
    "T1562": "Impair Defenses",
    "T1574": "Hijack Execution Flow",
    "T1059": "Command and Scripting Interpreter",
    "T1204": "User Execution",
    "T1505": "Server Software Component",
    "T1192": "Spearphishing Link",
}


class MITREAttckRules:
    def evaluate(self, knowledge_base: dict) -> dict:
        mapped = []
        sql_injection = knowledge_base.get("SQL Injection", {})
        for mapping in sql_injection.get("mitre_attck", []):
            mapped.append(mapping)

        return {
            "standard": "MITRE ATT&CK v14",
            "total_techniques": len(MITRE_ATTACK_TECHNIQUES),
            "matched_techniques": mapped,
            "techniques_matched_count": len(mapped),
            "score": (len(mapped) / len(MITRE_ATTACK_TECHNIQUES)) * 100 if MITRE_ATTACK_TECHNIQUES else 0,
        }
