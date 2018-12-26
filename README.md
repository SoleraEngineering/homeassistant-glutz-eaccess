# Glutz eAccess Integration for Home Assistant


## Home Asssistant Configuration

In `configuration.yml`:
```yaml
glutz:
  url: http://192.1.2.3:8080/rpc/
  proxy: http://http-proxy:9090
  username: glutz-api-username
  password: glutz-api-password
```



## Developer Setup

1. Install Python 3 `export PATH=/usr/local/bin:/usr/local/sbin:$PATH; brew install python`
1. Upgrade Pip `pip install --upgrade pip`
1. Install Pipenv `pip install --user pipenv`
1. Install Virtualenv `pip install virtualenv`

