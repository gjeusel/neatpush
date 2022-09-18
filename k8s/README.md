## K8S - Kustomize

- `.env.worker`: contains `EDGEDB_DSN` env var
- `.env.edgedb`: contains `EDGEDB_SERVER_PASSWORD` env var


## Access Edgedb

```bash
kubectl port-forward -n hdd svc/neatpush-edgedb 5657:5656
```

```bash
edgedb instance link neatpush_k8s --dsn edgedb://edgedb:edgedb@127.0.0.1:5657/edgedb --non-interactive --overwrite --trust-tls-cert
```

```bash
edgedb migration apply -I neatpush_k8s
```
