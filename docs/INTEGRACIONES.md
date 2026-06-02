# 🔌 Integraciones

> Webhook entrante para disparar flows + `notify.send` para emitir notificaciones.

![Integraciones](assets/cover-automa-pc.svg)

Dos vías para conectar Automa con el resto del mundo: webhook entrante para disparar flows desde sistemas externos, y la acción `notify.send` para emitir notificaciones al final de un flow.

## Webhook De Entrada

Endpoint: `POST /api/hook/<folder>`.

### Configuración

1. Define el secreto `AUTOMA_WEBHOOK_TOKEN` (env var o `secrets/secrets.json`).
2. Reinicia el panel.

```bash
export AUTOMA_WEBHOOK_TOKEN=$(openssl rand -hex 32)
automa-panel
```

Si el secreto no está definido, el endpoint responde `401` siempre. Esto es deliberado: no queremos un endpoint abierto.

### Uso

```bash
curl -X POST \
     -H "X-Automa-Token: $AUTOMA_WEBHOOK_TOKEN" \
     http://127.0.0.1:8787/api/hook/05_system_healthcheck
```

Respuesta:

```json
{"ok": true, "run_id": "20260501T140530123456Z", "status": "completed", "flow_id": "system_healthcheck"}
```

### Recomendaciones de despliegue

- Mantén el panel atado a `127.0.0.1` y exponlo a través de un reverse proxy (Caddy, nginx) con TLS.
- Genera un token largo y rotalo periódicamente.
- Si necesitas múltiples consumidores con permisos diferentes, usa tokens distintos en proxies distintos (un único secreto por ahora).

## Notificaciones De Salida

Acción `notify.send`. Backends:

### `log`

```json
{"id": "notif", "action": "notify.send", "params": {"message": "healthcheck OK"}}
```

Imprime a stdout. Útil para depurar.

### `file`

```json
{
  "id": "audit",
  "action": "notify.send",
  "params": {
    "message": "auditoría {audit_id} completada",
    "backend": "file",
    "target": "output/reports/audit_log.tsv"
  }
}
```

Append timestamp + mensaje. Bueno para registros offline.

### `webhook`

```json
{
  "id": "slack_alert",
  "action": "notify.send",
  "params": {
    "message": "Healthcheck FAIL en {snapshot.platform}",
    "backend": "webhook",
    "target": "https://hooks.slack.com/services/T000/B000/XXXXX",
    "token": "@secret:SLACK_HOOK_TOKEN"
  },
  "when": {"path": "decision.status", "operator": "eq", "value": "alerta"}
}
```

POST JSON a la URL. Si `token` se prefija con `@secret:`, el valor se resuelve desde la bóveda y se envía como `Authorization: Bearer ...`. El payload es:

```json
{"text": "<message>", "timestamp": "<iso>", ...extra}
```

### Conexión típica con Slack/Discord

Slack incoming webhooks aceptan `{"text": "..."}` directamente, sin token adicional — basta poner la URL del webhook como `target` y omitir `token`.

Discord también acepta `content` en lugar de `text`. Para esto, pasa `extra`:

```json
"params": {
  "backend": "webhook",
  "target": "https://discord.com/api/webhooks/...",
  "message": "alert",
  "extra": {"content": "alert"}
}
```

## Patrón Disparador → Pipeline → Notificación

```text
sistema externo --POST hook--> Automa --ejecuta flow--> notify.send (Slack)
```

El flow puede usar `transitions` con `when` para decidir si notificar o no en función del resultado.

## Métricas Como Integración

Si tu plataforma de observabilidad ya scrapea Prometheus, apunta el scraper a `http://<host>:8787/metrics`. Para dashboards más ricos, consume `/api/metrics` desde tu propio backend.

Detalle en [METRICAS.md](METRICAS.md).
