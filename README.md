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
| 🧙 Asistente de configuración | `visor --setup` guía paso a paso |
| 🎨 Colores en consola | Interfaz legible, compatible Win/Linux/macOS |
| 🗺️ Topología verificada | Mapa LAN + ruta L3 con evidencias ARP, ICMP, gateway y traceroute |
| 📶 Clientes Wi-Fi | Detecta clientes de la LAN y confirma asociaciones mediante AP/MikroTik configurado |

---

## 🚀 Instalación (una sola vez)

### Windows
```powershell
git clone https://github.com/JeissonAlberto/visor.git
cd visor
.\instalar.bat
```

### Linux / macOS
```bash
git clone https://github.com/JeissonAlberto/visor.git
cd visor
chmod +x instalar.sh
./instalar.sh
```

> Después de instalar, **cierra y vuelve a abrir la terminal**. El comando `visor` quedará disponible en cualquier carpeta.

**Requisitos:** Python 3.10+ · Sin dependencias externas (solo stdlib)

---

## ▶️ Uso

```bash
visor                # Menú interactivo principal
visor --scan         # Escaneo único de dispositivos
visor --web          # Verificar servicios web
visor --internet     # Test de calidad de internet
visor --setup        # Asistente de configuración
visor --report       # Ver último reporte
visor --version      # Ver versión
```

---

## 📁 Estructura

```
visor/
├── instalar.bat             ← Instalador automático Windows
├── instalar.sh              ← Instalador automático Linux/macOS
├── main.py                  ← Punto de entrada
├── setup.py / pyproject.toml← Registro del comando "visor"
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

### Alertas de correo (sin secretos en Git)

Configura las credenciales mediante variables de entorno:

```bash
export VISOR_SMTP_USER="mi_correo@gmail.com"
export VISOR_SMTP_PASS="xxxx xxxx xxxx xxxx"
export VISOR_SMTP_DESTINATARIO="noc@empresa.com"
# Opcional: VISOR_SMTP_SERVER y VISOR_SMTP_PORT (por defecto Gmail/465)
```

También puedes usar `visor --setup`: el asistente guarda la configuración en
`config/smtp_config_local.py`, un archivo excluido de Git. Obtén tu contraseña
de aplicación en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

Las credenciales de infraestructura siguen el mismo criterio:
`VISOR_MIKROTIK_PASS`, `VISOR_PROXMOX_PASS`, `VISOR_PROXMOX_TOKEN_ID` y
`VISOR_PROXMOX_TOKEN_SECRET`.

---

## 📜 Historial de versiones

| Versión | Cambios |
|---|---|
| **v2.0** | Refactor completo · Comando `visor` global · Instaladores automáticos · CLI con flags · Escaneo CIDR · Jitter · Reportes JSON/TXT · Asistente de configuración |
| **v1.0** | Versión original ([jsamrngs/zabbixcito](https://github.com/jsamrngs/zabbixcito)) — menú básico, ping, ARP, alertas email |

---

## 👤 Créditos

- **v1.0 original:** [@jsamrngs](https://github.com/jsamrngs/zabbixcito)
- **v2.0 Visor:** [Jasol Group](https://site.zapia.com/oiki3u0z) · Saravena, Arauca, Colombia

---

*Visor v2.0 — Python 3.10+ · Solo stdlib · Open source*


#### Clientes Wi-Fi

La búsqueda LAN también incluye equipos conectados por Wi-Fi si están en la misma
subred. Para confirmar el medio inalámbrico y obtener interfaz, señal, tasas y
uptime, configura el AP/MikroTik autorizado mediante variables de entorno:

```powershell
$env:VISOR_WIFI_ROUTER_HOST="IP_DEL_AP_O_MIKROTIK"
$env:VISOR_MIKROTIK_PASS="tu_clave"
```

La tabla de asociaciones solo se consulta si ambas variables están configuradas.
Si no se dispone del AP, el equipo se reporta como `lan_no_clasificado`: ARP no
permite afirmar si la conexión remota es cableada o inalámbrica.

### Topología verificada

Para obtener un mapa conservador de la red desde el equipo donde ejecutas Visor:

```bash
visor --topology
visor --topology 1.1.1.1
```

El comando descubre equipos LAN, identifica la ruta por defecto, traza la ruta L3
hacia el destino y conserva la ficha disponible de cada equipo: IP, MAC, fabricante,
hostname, puertos observados, riesgo, evidencias y verificaciones. Genera archivos
JSON, TXT y Graphviz DOT en `reports/`.

Visor no inventa conexiones entre equipos. ARP confirma vecindad L2 desde la estación,
pero no el puerto físico del switch; traceroute confirma un camino L3 observado, pero
no una conexión física. Las conexiones parciales o con timeout quedan marcadas como
no verificadas.



### Monitor 24/7 estilo PingPlotter

Para observar continuamente latencia y pérdida por salto, Visor incluye un
monitor multiplataforma basado en `traceroute` y `ping`. No modifica equipos:
solo toma muestras ICMP y actualiza los archivos vivos en `reports/`.

```powershell
python .\main.py --topology-watch 8.8.8.8 --watch-interval 60
```

`--watch-interval` está expresado en segundos y `--watch-cycles N` permite
limitar el número de muestras. Con `--watch-cycles 0` permanece activo hasta
presionar `Ctrl+C`. Se actualizan `topology_live.drawio`, `topology_live.json`,
`topology_live.txt`, además del historial JSONL y CSV. El draw.io incluye el
promedio ICMP y porcentaje de pérdida por salto.

