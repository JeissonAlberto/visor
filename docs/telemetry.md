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

## Configuración segura

```powershell
$env:VISOR_TELEMETRY_ENABLED = "1"
$env:VISOR_TELEMETRY_URL = "http://127.0.0.1:3049/events"
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
