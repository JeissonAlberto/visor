"""
core/guardian_ai.py — Asistente de Pentesting y Remediación para Visor v2.9.
Inspirado en Guardian-CLI (AI-powered pentesting automation).
"""

from core.raptor_eye import THREAT_VECTORS

def generate_remediation_plan(findings):
    """
    Simula la lógica de orquestación de Guardian-AI.
    Analiza hallazgos y genera una hoja de ruta de remediación.
    """
    plan = []
    
    for finding in findings:
        risk = finding.get("risk", "UNKNOWN")
        port = finding.get("port")
        desc = finding.get("desc")
        
        remediation = "No hay acción recomendada específica."
        tools = []
        
        if port == 3389: # RDP
            remediation = "Cerrar puerto 3389 en firewall o usar VPN/Gateway de Escritorio Remoto con MFA."
            tools = ["nmap --script rdp-enum-encryption", "hydra (audit de fuerza bruta)"]
        elif port == 445: # SMB
            remediation = "Deshabilitar SMBv1, aplicar parches de seguridad (MS17-010) y restringir acceso por IP."
            tools = ["nmap --script smb-vuln-ms17-010", "smbclient -L"]
        elif port == 23: # Telnet
            remediation = "Migrar inmediatamente a SSH (puerto 22). Telnet transmite credenciales en texto plano."
            tools = ["ssh-keygen", "config t -> line vty 0 4 -> transport input ssh"]
        elif port == 5555: # ADB
            remediation = "Desactivar la depuración por red en el dispositivo o bloquear puerto 5555."
            tools = ["adb disconnect", "iptables -A INPUT -p tcp --dport 5555 -j DROP"]
        elif port == 3306: # MySQL
            remediation = "Restringir bind-address a 127.0.0.1 y auditar usuarios con contraseñas débiles."
            tools = ["mysql_secure_installation", "nmap --script mysql-audit"]

        plan.append({
            "vector": desc,
            "risk": risk,
            "port": port,
            "remediation": remediation,
            "suggested_tools": tools
        })
        
    return plan
