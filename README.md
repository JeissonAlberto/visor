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
| 🌍 Vigilancia pública | Comprueba continuamente redes sociales, bancos y portales oficiales configurados |

---

## 🚀 Instalación: clonar y escribir `visor`

La instalación crea un entorno aislado dentro del repositorio, instala el comando y lo
registra en el PATH del usuario. No necesitas activar entornos virtuales, ejecutar `pip`
ni editar archivos de configuración.

### Windows
```powershell
git clone https://github.com/JeissonAlberto/visor.git
cd visor
.\instalar.bat
```

Después abre una terminal nueva. Desde cualquier carpeta podrás ejecutar:

```powershell
visor
visor --version
```

### Linux / macOS
```bash
git clone https://github.com/JeissonAlberto/visor.git
cd visor
chmod +x instalar.sh visor
./instalar.sh
```

Después de la instalación, desde cualquier carpeta:

```bash
visor
visor --version
```

El instalador usa `.venv/` dentro del repositorio, no modifica el Python del sistema y
no instala dependencias externas de Visor. Si mueves el repositorio después de instalar,
vuelve a ejecutar el instalador para actualizar la ruta del comando.

**Requisito:** Python 3.10+.

---

## ▶️ Uso

```bash
visor                # Menú interactivo principal
visor --scan         # Escaneo único de dispositivos
visor --web          # Verificar servicios web
visor --internet     # Test de calidad de internet
visor --watch        # Monitoreo continuo LAN + servicios públicos
visor --setup        # Asistente de configuración
visor --report       # Ver último reporte
visor --version      # Ver versión
```

El diagnóstico interactivo de calidad acepta entre **1 y 120 paquetes** por medición;
se rechazan cantidades inválidas antes de iniciar tráfico de red.

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

### API de Proxmox y TLS

La conexión a Proxmox valida por defecto los certificados contra la CA del sistema.
Para usar una CA interna o el certificado de la instalación, indica su ruta sin
incluir secretos en el repositorio:

```bash
export VISOR_PROXMOX_CA_FILE="/ruta/a/proxmox-ca.pem"
```

Las instalaciones antiguas con certificado autofirmado pueden usar temporalmente
`VISOR_PROXMOX_INSECURE_TLS=1`, pero esta opción desactiva la validación TLS y no
se recomienda en producción. Para hosts configurados por IP se mantiene la
validación de la cadena, aunque no se puede comprobar la coincidencia del nombre.

### Vigilancia pública continua

El modo `visor --watch` comprueba la disponibilidad HTTP de los servicios incluidos en
estas categorías: redes sociales, bancos colombianos y portales oficiales de Saravena,
Arauca y Sisbén. Si un servicio cambia de disponible a caído, o se recupera, Visor genera
una alerta de transición y la registra en pantalla/correo si el correo está configurado.

La lista inicial incluye únicamente páginas públicas. Visor **no** inicia sesión en
WhatsApp, bancos, redes sociales o portales estatales; no lee chats, saldos, movimientos,
contraseñas ni documentos personales. Para ampliar la vigilancia se agregan URLs públicas
en `core/web_service.py` o en `config/device.py`. No se rastrea automáticamente todo
internet ni todos los dominios `.gov`, porque eso sería impreciso y podría generar tráfico
indebido: se trabaja con una lista explícita de portales autorizados.

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

