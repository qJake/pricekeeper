import re
from datetime import datetime, timedelta
from types import SimpleNamespace
from azure.data.tables import TableServiceClient, TableEntity
from azure.core.credentials import AzureNamedKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from utils import get_rowkey_datestamp, convert_date_rowkey


MAX_RESULTS = 1000

class LogCategory:
    CAT_REQUESTS = 'Requests'
    CAT_SPARKLINES = 'Sparklines'
    CAT_JOBS = 'Jobs'
    CAT_PRUNING = 'Pruning'
    CAT_SYSTEM = 'System'

def store_price(price: float, name: str, cat: str, config: SimpleNamespace):
    if hasattr(config, 'storage'):
        if hasattr(config.storage, 'type') and config.storage.type == 'azure':
            priceTbl = init_table_price(config)
            priceTbl.create_entity({
                'PartitionKey': name,
                'RowKey': str(get_rowkey_datestamp()),
                'Price': price
            })

            currTbl = init_table_current(config)
            currTbl.upsert_entity({
                'PartitionKey': 'current',
                'RowKey': name,
                'Price': price,
                'Category': cat
            })

def store_sparkline(config: SimpleNamespace, name: str, spark: str):
    sparkTbl = init_table_sparklines(config)
    sparkTbl.upsert_entity({
        'PartitionKey': 'current',
        'RowKey': name,
        'SparkImage': spark
    })

def get_sparklines(config: SimpleNamespace) -> dict:
    sparkTbl = init_table_sparklines(config)
    sparks = sparkTbl.list_entities(results_per_page=MAX_RESULTS)
    sparkDict = {}
    for s in next(sparks.by_page()):
        sparkDict[s['RowKey']] = s['SparkImage'].decode('utf8')
    return sparkDict

def get_sparkline(config: SimpleNamespace, name: str) -> str:
    try:
        sparkTbl = init_table_sparklines(config)
        spark = sparkTbl.get_entity('current', name)
        return spark['SparkImage'] if 'SparkImage' in spark else None
    except ResourceNotFoundError:
        return None

def get_price_summary(config: SimpleNamespace, names: list) -> list[dict]:
    items = []
    currTbl = init_table_current(config)

    pr = currTbl.list_entities(results_per_page=MAX_RESULTS)
    for row in next(pr.by_page()):
        if row['RowKey'] in names:
            cfgRule = next(iter([r for r in config.rules if row['RowKey'] == r.name]), None)
            items.append({
                'name': row['RowKey'],
                'price': row['Price'],
                'category': row['Category'],
                'link': cfgRule.link if hasattr(cfgRule, 'link') else None
            })

    return items

def get_price_history(config: SimpleNamespace, name: str) -> list[dict]:
    prices = []
    priceTbl = init_table_price(config)
    rows = priceTbl.query_entities(f"PartitionKey eq @name", parameters={'name': name})
    for r in rows:
        prices.append({
            'y': r['Price'],
            'x': convert_timestamp(r)
        })
    return prices

def get_recent_prices(config: SimpleNamespace, name: str, hours: int=72) -> tuple[int, int]:
    priceTbl = init_table_price(config)
    rows = priceTbl.query_entities(f"PartitionKey eq @name and RowKey le @rk", parameters={'name': name, 'rk': str(convert_date_rowkey(datetime.utcnow() - timedelta(hours=hours)))})
    x = []
    y = []
    for r in sorted(next(rows.by_page()), reverse=True, key=lambda r: r['RowKey']):
        x.append(r['RowKey'])
        y.append(r['Price'])
    return (x, y)

def add_log_entry(config: SimpleNamespace, cat: str, msg: str, stack: str=None):
    logTbl = init_table_log(config)
    logTbl.create_entity({
        'PartitionKey': cat,
        'RowKey': str(get_rowkey_datestamp(1000)),
        'Message': msg,
        'Stack': stack
    })

def get_log_entries(config: SimpleNamespace, count: int = MAX_RESULTS) -> list[dict]:
    logTbl = init_table_log(config)
    return next(logTbl.list_entities(results_per_page=count).by_page())
    

# def get_adjacent_rows(config: SimpleNamespace, name: str, rowKey: int):
#     priceTbl = init_table(config)
    
#     # Query the table to find the next highest and next lowest row keys
#     query = f"PartitionKey eq @partitionKey and RowKey ge @rowKey"
#     results = priceTbl.query_entities(query, parameters={'partitionKey': name, 'rowKey': rowKey}, select='RowKey')

#     # Get the row keys from the query results
#     row_keys = [r.RowKey for r in results['items']]

#     # Find the next highest and next lowest row keys
#     next_highest = None
#     next_lowest = None
#     for key in row_keys:
#         if key > rowKey and (next_highest is None or key < next_highest):
#             next_highest = key
#         elif key < rowKey and (next_lowest is None or key > next_lowest):
#             next_lowest = key

#     return next_highest, next_lowest


def init_table_price(config: SimpleNamespace):
    creds = AzureNamedKeyCredential(config.storage.account, config.storage.key)
    tblService = TableServiceClient(endpoint=f"https://{config.storage.account}.table.core.windows.net/", credential=creds)
    tblName = tblname_prices(config.storage.table if hasattr(config.storage, 'table') else None)
    return tblService.create_table_if_not_exists(tblName)

def init_table_current(config: SimpleNamespace):
    creds = AzureNamedKeyCredential(config.storage.account, config.storage.key)
    tblService = TableServiceClient(endpoint=f"https://{config.storage.account}.table.core.windows.net/", credential=creds)
    tblName = tblname_current(config.storage.table if hasattr(config.storage, 'table') else None)
    return tblService.create_table_if_not_exists(tblName)

def init_table_sparklines(config: SimpleNamespace):
    creds = AzureNamedKeyCredential(config.storage.account, config.storage.key)
    tblService = TableServiceClient(endpoint=f"https://{config.storage.account}.table.core.windows.net/", credential=creds)
    tblName = tblname_sparklines(config.storage.table if hasattr(config.storage, 'table') else None)
    return tblService.create_table_if_not_exists(tblName)

def init_table_log(config: SimpleNamespace):
    creds = AzureNamedKeyCredential(config.storage.account, config.storage.key)
    tblService = TableServiceClient(endpoint=f"https://{config.storage.account}.table.core.windows.net/", credential=creds)
    tblName = tblname_log(config.storage.table if hasattr(config.storage, 'table') else None)
    return tblService.create_table_if_not_exists(tblName)

def tblname_prices(base: str):
    return f"{(base if base is not None else '')}prices"

def tblname_current(base: str):
    return f"{(base if base is not None else '')}current"

def tblname_sparklines(base: str):
    return f"{(base if base is not None else '')}sparklines"

def tblname_log(base: str):
    return f"{(base if base is not None else '')}log"

def convert_timestamp(row: TableEntity) -> str:
    ts = row.metadata['timestamp'].tables_service_value
    ts = re.sub('\\.\d+Z', 'Z', ts)
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").strftime('%Y-%m-%d %H:%M:%S')
