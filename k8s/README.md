## K8S - Kustomize

## Env Files to generate secrets

### `.env.worker`

```bash
EDGEDB_DSN=xxxxx

TWILIO_ENABLED=xxxxx
TWILIO_ACCOUNT_SID=xxxxx
TWILIO_SERVICE_SID=xxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_NUM_FROM=xxxxx
TWILIO_NUM_TO=xxxxx
```

### `.env.edgedb`

```bash
EDGEDB_SERVER_PASSWORD=xxxxx
```

## Access Edgedb

```bash
kubectl port-forward -n hdd svc/neatpush-edgedb 5657:5656
```

```bash
edgedb instance link neatpush_k8s --dsn edgedb://edgedb:edgedb@127.0.0.1:5657/edgedb --non-interactive --overwrite --trust-tls-cert

edgedb migration apply -I neatpush_k8s
```
