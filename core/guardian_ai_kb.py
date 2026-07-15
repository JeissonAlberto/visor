"""
core/guardian_ai_kb.py — Base de Conocimiento de Remediación para Visor v5.1.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia
"""

REMEDIATION_KB = {
    3389: {
        "nombre": "RDP Expuesto", "riesgo": "CRÍTICO",
        "descripcion": "Puerto RDP visible. Vector #1 de Ransomware.",
        "impacto": "Acceso total al sistema.",
        "remediacion": [
            "Cerrar puerto 3389 en firewall MikroTik.",
            "Usar VPN antes de exponer RDP.",
            "Habilitar NLA y bloquear cuentas tras 5 intentos.",
        ],
        "comandos": ["/ip firewall filter add chain=input protocol=tcp dst-port=3389 src-address-list=!LAN action=drop"],
        "referencias": ["CVE-2019-0708", "CISA Alert AA21-321A"],
    },
    445: {
        "nombre": "SMB Expuesto", "riesgo": "CRÍTICO",
        "descripcion": "Vulnerable a EternalBlue (WannaCry, NotPetya).",
        "impacto": "Movimiento lateral y cifrado masivo de archivos.",
        "remediacion": ["Deshabilitar SMBv1.", "Aplicar parche MS17-010.", "Bloquear puertos 139/445 en perímetro."],
        "comandos": ["Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force"],
        "referencias": ["CVE-2017-0144", "MS17-010"],
    },
    23:   {"nombre": "Telnet Activo", "riesgo": "CRÍTICO", "descripcion": "Transmite credenciales en texto plano.", "impacto": "Captura con Wireshark trivial.", "remediacion": ["Migrar a SSH.", "/ip service disable telnet"], "comandos": ["/ip service disable telnet"], "referencias": ["RFC-0854"]},
    21:   {"nombre": "FTP sin cifrar", "riesgo": "ALTO", "descripcion": "Credenciales en texto plano.", "impacto": "Robo de credenciales.", "remediacion": ["Migrar a SFTP."], "comandos": ["/ip service disable ftp"], "referencias": ["RFC-0959"]},
    22:   {"nombre": "SSH Expuesto", "riesgo": "MEDIO", "descripcion": "Riesgo de fuerza bruta.", "impacto": "Acceso root si contraseña débil.", "remediacion": ["Cambiar puerto.", "Deshabilitar login por contraseña.", "Instalar fail2ban."], "comandos": ["Port 2222", "PasswordAuthentication no"], "referencias": ["CIS SSH Benchmark"]},
    80:   {"nombre": "HTTP sin TLS", "riesgo": "MEDIO", "descripcion": "Tráfico en texto plano.", "impacto": "Interceptación de sesiones.", "remediacion": ["Migrar a HTTPS.", "Usar Let's Encrypt."], "comandos": ["sudo certbot --nginx -d dominio.com"], "referencias": ["OWASP A02:2021"]},
    3306: {"nombre": "MySQL Expuesto", "riesgo": "ALTO", "descripcion": "BD accesible en red.", "impacto": "Exfiltración de datos.", "remediacion": ["bind-address=127.0.0.1", "Usar túnel SSH."], "comandos": ["sudo mysql_secure_installation"], "referencias": ["CIS MySQL Benchmark"]},
    5900: {"nombre": "VNC Abierto", "riesgo": "ALTO", "descripcion": "VNC sin cifrado.", "impacto": "Control total del escritorio.", "remediacion": ["Usar VNC solo via túnel SSH."], "comandos": ["ssh -L 5901:localhost:5900 user@host"], "referencias": ["CVE-2006-2369"]},
    5555: {"nombre": "ADB Debug", "riesgo": "CRÍTICO", "descripcion": "Android Debug Bridge expuesto.", "impacto": "Control total del dispositivo.", "remediacion": ["Desactivar USB Debugging.", "adb kill-server"], "comandos": ["adb kill-server"], "referencias": ["Android Security Bulletin"]},
    8291: {"nombre": "Winbox MikroTik", "riesgo": "ALTO", "descripcion": "Puerto Winbox expuesto. CVE conocidas.", "impacto": "Acceso completo al router.", "remediacion": ["Limitar a IPs admin.", "Actualizar RouterOS."], "comandos": ["/ip service set winbox address=192.168.1.0/24"], "referencias": ["CVE-2018-14847"]},
}

DEFAULT_REMEDIATION = {
    "remediacion": ["Auditar si este puerto es necesario.", "Si no, cerrar en firewall.", "Mantener servicio actualizado."],
    "comandos": ["/ip firewall filter add chain=input dst-port=<puerto> action=drop"],
}
