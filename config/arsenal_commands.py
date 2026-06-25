"""
config/arsenal_commands.py — Biblioteca de comandos rápidos para Jasol Group.
Inspirado en el formato de Arsenal-NG.
"""

ARSENAL_LIBRARY = [
    {
        "categoria": "Diagnóstico de Red (L3)",
        "comandos": [
            {
                "titulo": "Ping Infinito con Timestamp",
                "cmd": "ping {{target}} -t | cmd /q /v /c \"(pause&pause)>nul & for /l %a in () do (set /p \"data=\" && echo (!date! !time!) !data!)\"",
                "desc": "Ideal para monitorear caídas intermitentes con registro de hora."
            },
            {
                "titulo": "Traza de Ruta Detallada (MTR Style)",
                "cmd": "pathping -n {{target}}",
                "desc": "Combina ping y tracert para identificar pérdida de paquetes por salto."
            },
            {
                "titulo": "Escaneo de DNS (NSLOOKUP)",
                "cmd": "nslookup {{domain}} {{dns_server|8.8.8.8}}",
                "desc": "Verifica resolución de nombres usando un servidor específico."
            }
        ]
    },
    {
        "categoria": "Soporte Windows / Client-Side",
        "comandos": [
            {
                "titulo": "Limpieza total de Red (Stack Reset)",
                "cmd": "ipconfig /release && ipconfig /flushdns && ipconfig /renew && netsh int ip reset && netsh winsock reset",
                "desc": "Resetea todo el stack de red del cliente. Requiere Admin."
            },
            {
                "titulo": "Verificar tabla ARP local",
                "cmd": "arp -a",
                "desc": "Muestra la caché ARP para detectar conflictos de IP o suplantación de MAC."
            }
        ]
    },
    {
        "categoria": "Gestión Mikrotik / Ubiquiti (SSH)",
        "comandos": [
            {
                "titulo": "Monitoreo de Tráfico Interfaz (Mikrotik)",
                "cmd": "ssh {{user|admin}}@{{target}} \"/interface monitor-traffic {{interface|ether1}}\"",
                "desc": "Ver tráfico en tiempo real vía SSH."
            },
            {
                "titulo": "Ver Logs del Sistema (Mikrotik)",
                "cmd": "ssh {{user|admin}}@{{target}} \"/log print follow-only\"",
                "desc": "Streaming de logs para depurar desconexiones."
            }
        ]
    }
]
