# NeatPush

<p align="center">
  <a href="https://mangapill.com">
    <img src="https://mangapill.com/static/favicon/android-chrome-512x512.png" alt="MangaPill">
  </a>
</p>

## Local Dev

```bash
conda create --name neatpush python=3.10.7 --yes

conda activate neatpush

pip install --editable ".[dev,qa,test]"
```

## Deploy

```bash
docker build --platform linux/amd64 -t guigze/neatpush:latest .

docker push guigze/neatpush:latest

kubectl apply -k k8s/
```


## Buggy Edgedb

- Might complain port is already used on restart:
```bash
launchctl remove edgedb-server-neatpush
```
