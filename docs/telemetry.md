# Telemetría de Visor y Jitsu

Visor define un evento estable `visor.telemetry.v1` para enviar métricas a un
backend de ingestión como Jitsu. La integración es **opt-in** y no se activa
por instalar Visor.

## Evento de topología

El tipo inicial es `topology.path_sample` e incluye:

- `event_id`, `event_type`, `source` y `observed_at`.
- Resumen de nodos, conexiones y saltos L3.
- Por salto: pérdida porcentual, latencia promedio y alcanzabilidad.
- Identificadores de destino anonimizados mediante SHA-256 truncado por defecto.

No se incluyen contraseñas, tokens, variables de entorno ni salidas completas
de comandos. Las IP/host originales solo se incluyen si la instalación NOC lo
habilita conscientemente.

## Prueba local sin Jitsu

En una primera terminal, inicia el receptor seguro de localhost:

```powershell
python .\scripts\telemetry_test_adapter.py --port 3049 --once
```

En otra terminal, activa el envío del monitor de topología durante una muestra:

```powershell
$env:VISOR_TELEMETRY_ENABLED = "1"
$env:VISOR_TELEMETRY_URL = "http://127.0.0.1:3049/events"
python .\main.py --topology-watch 8.8.8.8 --watch-interval 10 --watch-cycles 1
```

El evento se guardará en `reports/telemetry_test_events.jsonl`. El receptor
solo escucha en localhost y valida el esquema `visor.telemetry.v1`.

## Configuración segura

```powershell
$env:VISOR_TELEMETRY_ENABLED = "1"
$env:VISOR_TELEMETRY_URL = "https://tu-endpoint-de-ingestión/events"
$env:VISOR_TELEMETRY_TOKEN = "token-de-prueba"
```

En una integración real se debe usar HTTPS, autenticación con alcance mínimo,
retención limitada y un endpoint de ingestión dedicado. Para una primera
prueba se recomienda un adaptador local, no Jitsu en producción.

El cliente no hace reintentos infinitos ni imprime el token. Si la telemetría
está desactivada, no realiza ninguna conexión.

## Integración por fases

1. Probar `core.telemetry` contra un receptor HTTP local.
2. Validar el esquema y la retención en un entorno aislado de Jitsu.
3. Conectar únicamente muestras del monitor de topología.
4. Agregar eventos MikroTik/Proxmox después de revisar su contenido.
5. Aprobar por separado cualquier despliegue productivo.
