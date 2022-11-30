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

scheduler:
  spreadtime: 30

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

For a complete list of configuration options, see below.

## Run with Docker

| Item       | Description                |
| ---------- | -------------------------- |
| Image Name | `qjake/pricekeeper:latest` |
| Port(s)    | `9600`                     |
| Mount(s)   | `/app/config.yaml`         |
| Volume(s)  | *None*                     |

### Example

```
docker run -d -p 9600:9600 -v /path/to/your/config.yaml:/app/config.yaml --name pricekeeper qjake/pricekeeper:latest
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

## Configuration File Reference

### Section: `storage`

**Type:** object

| Key | Type | Required | Value |
| -- | -- | -- | -- |
| `type` | string | ✅ | `azure` (Currently, only Azure Tables are supported.)
| `account` | string | ✅  | Azure Storage account name (do not include ".table.core.windows.net") |
| `key` | string | ✅  | Azure Storage Accout access key (not a SAS, and not the connection string) |
| `table` | string | ✅  | The name of the table to store prices in. If it does not exist, it will be created automatically. |

### Section: `scheduler`

**Type:** object

| Key | Type | Required | Value |
| -- | -- | -- | -- |
| `spreadtime` | int |  | Number of random seconds to add to a job to spread multiple jobs out that would otherwise run at the same time. (Sometimes referred to as "jitter".) Omit to disable random spread.

### Section: `rules`

**Type:** array

| Key | Type | Required | Templatable | Value |
| -- | -- | --| -- | -- |
| `name` | string | ✅ | | A distinct name for this rule. Do not include any special (URL-unsafe) characters. |
| `category` | string | ✅ | ✅ | A category to file this rule under, for visually grouping rules. Rules with the exact same category name are displayed together. (e.g. "Amazon" or "Google") |
| `url` | string | ✅ | ✅ | The URL to fetch that contains the price. The price must be in the source/response body of the page (dynamic prices rendered via JS will not work or will require a different/creative solution). Doesn't have to be HTML - you can fetch a public API endpoint too.
| `hours` | string | ✅ | ✅ | A cron-like expression for which hours to run the price fetch job. (e.g. `'*'` or `'9,12,15'` or `'*/3'`)
| `mins` | string | | ✅ | A cron-like expression for which minutes to run the price fetch job. Defaults to `'0'`.
| `selector` | string \| array[string] | ✅ (or `regex`) | ✅ | One or more CSS selectors to look for a price value inside. The text value of all of the matched elements is taken as a single string, and a decimal value is extracted from the text. If multiple selectors are specified, they are executed from top to bottom until a price is found.
| `regex` | string \| array[string] | ✅ (or `selector`) | ✅ | One or more regular expressions to look for a price value. **The first capture group should contain a price-like value.** (If you need other capture groups in your expression, make sure they are non-capture groups [`(?:...)`].) If multiple expressions are specified, they are executed from top to bottom until a price is found.
| `divide` | bool | | ✅ | `true` if the price is in a non-decimal format like `2000` but should be interpreted as `$20.00`. The value will be divided by 100.
| `referer` | string | | ✅ | If set, will send an HTTP `Referer` header with this value.
| `template` | string | | | If set, will apply a template to this rule. See the template section below for more information.

### Section: `cache` (optional)

**Type:** object

You may want to track prices from a public API endpoint, or a page with multiple prices on it. Cache calls to a specific URL to improve performance.

The key is the URL and the value is the amount of seconds to cache that URL for.

For example:

```yaml
cache:
  https://example.org/store/prices: 600 # 5 mins
  https://example.com/product/listing: 120 # 2 mins
```

### Section: `templates` (optional)

**Type:** object

Templates are used to apply common attributes to multiple rules. For example, the selector `'.a-price .a-offscreen'` can apply to most, if not all, Amazon listings. So instead of duplicating the rule many times, you can apply a template to it instead.

Define a template by giving it a name, as the key of a dictionary.

The properties inside the template definition will be copied to each rule that inherits from this template.

### Example

The original `config.yaml` example at the top of this Readme contains duplicated information. We can rewrite this example using templates to avoid duplication:

```yaml
storage:
  type: azure
  account: mystorageaccountname
  key: abcde............................67890==
  table: prices

scheduler:
  spreadtime: 30

rules:
  - name: Complete Guide to Docker for Beginners
    template: amazon
    url: https://www.amazon.com/dp/B08BW5Y73D/

  - name: Learning Python 5th Edition
    template: amazon
    url: https://www.amazon.com/dp/1449355730/

  - name: Pixel 7 Pro
    template: google
    url: https://store.google.com/product/pixel_7_pro

  - name: Pixel 7 Pro Case
    template: google
    url: https://store.google.com/product/casemate_tough_clear_cases

templates:
  amazon:
    category: Amazon
    hours: '*'
    selector: '.a-price .a-offscreen'

  google:
    category: Google
    hours: '0,12'
    regex:
      - meta itemprop="lowPrice" content="(.+?)"
      - meta itemprop="price" content="(.+?)"
```
