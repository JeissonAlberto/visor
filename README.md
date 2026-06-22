# Visor — Monitor de Red
> by **Jasol Group** · Saravena, Arauca, Colombia

**Visor** es una herramienta de monitoreo de red ligera, sin dependencias externas, inspirada en Zabbix. Pensada para técnicos de ISP y soporte NOC que necesitan visibilidad rápida de su infraestructura.

---

## ⚡ Características

| Feature | Descripción |
|---|---|
| 📡 Monitoreo de dispositivos | Ping por IP, dominio o MAC (ARP) |
| 🌐 Verificación de servicios web | HTTP con código de respuesta y latencia |
| 📶 Test de calidad de internet | Latencia avg/min/max, jitter y pérdida de paquetes |
| 🗺️ Escaneo de rango IP | Descubre hosts activos en una subred CIDR |
| 📧 Alertas por correo | Gmail SMTP — notifica caídas y recuperaciones |
| 📋 Reportes automáticos | Guarda TXT o JSON en `/reports` |
| 🧙 Asistente de configuración | `python main.py --setup` guía paso a paso |
| 🎨 Colores en consola | Interfaz legible, compatible Win/Linux/macOS |

---

## 🚀 Inicio rápido

```bash
# 1. Clona el repositorio
git clone https://github.com/JeissonAlberto/visor.git
cd visor

# 2. (Opcional) Configura con el asistente
python main.py --setup

# 3. Edita manualmente si prefieres
#    config/device.py    → tus dispositivos y URLs
#    config/smtp_config.py → correo para alertas

# 4. Ejecuta
python main.py
```

**Requisitos:** Python 3.10+ · Sin dependencias externas (solo stdlib)

---

## 📁 Estructura

```
visor/
├── main.py                  ← Punto de entrada
├── config/
│   ├── device.py            ← 📝 TUS dispositivos y servicios web
│   ├── smtp_config.py       ← 📝 Correo para alertas
│   └── settings.py          ← Configuración general
├── core/
│   ├── monitor.py           ← Escaneo de dispositivos
│   ├── red.py               ← Ping, ARP, escaneo de rangos
│   ├── web_service.py       ← Verificación HTTP
│   ├── test_internet.py     ← Test de calidad de internet
│   ├── mail.py              ← Alertas por correo
│   └── colores.py           ← Estilos de consola
├── ui/
│   ├── menu.py              ← Menú interactivo
│   └── setup_wizard.py      ← Asistente de configuración
├── utils/
│   └── reportes.py          ← Generación y gestión de reportes
└── reports/                 ← Reportes generados (gitignoreado)
```

---

## 🖥️ Uso desde línea de comandos

```bash
python main.py              # Menú interactivo
python main.py --scan       # Escaneo único rápido
python main.py --web        # Solo servicios web
python main.py --internet   # Solo test de internet
python main.py --setup      # Asistente de configuración
python main.py --report     # Ver último reporte
python main.py --version    # Ver versión
```

---

## ⚙️ Configuración

### Dispositivos (`config/device.py`)

```python
DISPOSITIVOS = [
    {"nombre": "Router",       "ip": "192.168.1.1",  "mac": "",                  "tipo": "lan",      "grupo": "Red principal"},
    {"nombre": "AP TP-Link 1", "ip": "",              "mac": "B0:BE:76:2D:E1:59", "tipo": "lan",      "grupo": "Red principal"},
    {"nombre": "Servidor Web", "ip": "mipagina.com",  "mac": "",                  "tipo": "servidor", "grupo": "Producción"},
]

SERVICIOS_WEB = [
    {"nombre": "Mi sitio",  "url": "https://mipagina.com"},
]

RANGO_SCAN = "192.168.1.0/24"
```

### Alertas de correo (`config/smtp_config.py`)

```python
SMTP_USER    = "mi_correo@gmail.com"
SMTP_PASS    = "xxxx xxxx xxxx xxxx"   # Contraseña de aplicación Gmail
DESTINATARIO = "noc@empresa.com"
```

> Obtén tu contraseña de aplicación en: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

---

## 📜 Historial de versiones

| Versión | Cambios |
|---|---|
| **v2.0** | Refactor completo · CLI con flags · Escaneo de rangos CIDR · Jitter · Reportes JSON/TXT · Asistente de configuración · Colores multiplataforma |
| **v1.0** | Versión original ([jsamrngs/zabbixcito](https://github.com/jsamrngs/zabbixcito)) — menú básico, ping, ARP, alertas email |

---

## 👤 Créditos

- **v1.0 original:** [@jsamrngs](https://github.com/jsamrngs/zabbixcito)
- **v2.0 Visor:** [Jasol Group](https://site.zapia.com/6bdicjlq) · Saravena, Arauca, Colombia

---

*Visor v2.0 — Python 3.10+ · Solo stdlib · Open source*
