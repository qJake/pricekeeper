from datetime import datetime
import re
from types import SimpleNamespace
from azure.data.tables import TableServiceClient, TableEntity
from azure.core.credentials import AzureNamedKeyCredential


def store_price(price: float, name: str, config: SimpleNamespace):
    if hasattr(config, 'storage'):
        if hasattr(config.storage, 'type') and config.storage.type == 'azure':
            priceTbl = init_table(config)
            priceTbl.create_entity({
                'PartitionKey': name,
                'RowKey': str(int((datetime(2999, 12, 31, 0, 0, 0, 0) - datetime.utcnow()).total_seconds() * 10)),
                'Price': price
            })

def get_price_summary(config: SimpleNamespace, names: list) -> list[dict]:
    items = []
    priceTbl = init_table(config)
    for n in names:
        pr = priceTbl.query_entities(f"PartitionKey eq @name", parameters={'name': n})
        for row in pr:
            items.append({
                'name': n,
                'price': row['Price']
            })
            break
    return items

def get_price_history(config: SimpleNamespace, name: str) -> list[dict]:
    prices = []
    priceTbl = init_table(config)
    rows = priceTbl.query_entities(f"PartitionKey eq @name", parameters={'name': name})
    for r in rows:
        prices.append({
            'y': r['Price'],
            'x': convert_timestamp(r)
        })
    return prices

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

def init_table(config: SimpleNamespace):
    creds = AzureNamedKeyCredential(config.storage.account, config.storage.key)
    tblService = TableServiceClient(endpoint=f"https://{config.storage.account}.table.core.windows.net/", credential=creds)
    return tblService.create_table_if_not_exists(config.storage.table)

def convert_timestamp(row: TableEntity) -> str:
    ts = row.metadata['timestamp'].tables_service_value
    ts = re.sub('\\.\d+Z', 'Z', ts)
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").strftime('%Y-%m-%d %H:%M:%S')
