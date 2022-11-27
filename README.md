# 💸 PriceKeeper

A private, automated, cloud-enabled price tracker.

## Create Your Config File

Make a file called `config.yaml` and store it somewhere safe, like `~/pricekeeper/config.yaml`.

Use this as a jumping off point:

```yaml
storage:
  type: azure
  account: mystorageaccountname
  key: abcde............................67890==
  table: prices

rules:
  - name: Complete Guide to Docker for Beginners
    category: Amazon
    selector: '.a-price .a-offscreen'
    url: https://www.amazon.com/dp/B08BW5Y73D/
    hours: '*'
  - name: Learning Python 5th Edition
    category: Amazon
    selector: '.a-price .a-offscreen'
    template: amazon
    url: https://www.amazon.com/dp/1449355730/
    hours: 0,3,6,9,12,15,18,21
  - name: Pixel 7 Pro
    category: Google
    regex:
      - meta itemprop="lowPrice" content="(.+?)"
      - meta itemprop="price" content="(.+?)"
    url: https://store.google.com/product/pixel_7_pro
    hours: '0,12'
  - name: Pixel 7 Pro Case
    category: Google
    regex:
      - meta itemprop="lowPrice" content="(.+?)"
      - meta itemprop="price" content="(.+?)"
    url: https://store.google.com/product/casemate_tough_clear_cases
    hours: '0,12'

```

## Run with Docker

| Item       | Description                |
| ---------- | -------------------------- |
| Image Name | `qjake/pricekeeper:latest` |
| Port(s)    | `9600`                     |
| Mount(s)   | `/app/config.yaml`         |
| Volume(s)  | *None*                     |

### Example

```
docker run -p 9600:9600 -v /path/to/your/config.yaml:/app/config.yaml qjake/pricekeeper:latest
```

## Run with Docker Compose

Sample `docker-compose.yml`:

```yaml
version: "3.9"
services:
  pricekeeper:
    container_name: pricekeeper
    restart: unless-stopped
    image: qjake/pricekeeper:latest
    volumes:
      - /path/to/your/config.yaml:/app/config.yaml
    ports:
      - "9600:9600"
    # Optional, if you want to include a health check
    healthcheck:
      test: curl -s --fail http://127.0.0.1:9600/_health || exit 1
      interval: 10s
      retries: 3
      start_period: 5s
      timeout: 5s
```