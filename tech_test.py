from typing import Dict, Any

import requests
import json
import base64
import time
from datetime import datetime

# Set Shopify API variables
SHOPIFY_URL = "paucek-considine6869.myshopify.com/"
SHOPIFY_ORDERS_ENDPOINT = "admin/orders"
SHOPIFY_PRODUCTS_ENDPOINT = "admin/products"
SHOPIFY_API_AUTH = "490f41edd92a10c5b3a407586a9afddc:37146826a987bc7d64eedc6ccab575ea"
SHOPIFY_API_QUERY_STRING = {"created_at_min":"2016-01-01T00:00:00","created_at_max":"2016-12-31T11:59:59"
,"financial_status":"paid"}

# Set Klaviyo API variables
KLAVIYO_API_URL = "https://a.klaviyo.com/api/track"
KLAVIYO_PUBLIC_API_KEY = "Luq7Ti"
KLAVIYO_API_QUERY_STRING = {"data":""}

def construct_customer_properties(shopify_order):

    """
    Assemble the customer information from a given Shopify order
    Args:
    shopify_order (obj): order object from Shopify order request
    Returns:
    customer_properties (obj): customer properties object for Klaviyo server-side Track request
    """

    customer = shopify_order.get("customer",{})
    customer_address = customer.get("default_address",{})
    customer_properties: Dict[str, Any] = {
    "$email": customer.get("email",""),
    "$first_name": customer.get("first_name",""),
    "$last_name": customer.get("last_name",""),
    "$phone_number": customer_address.get("phone",""),
    "$address1": customer_address.get("address1",""),
    "$address2": customer_address.get("address2",""),
    "$city": customer_address.get("city",""),
    "$zip": customer_address.get("zip",""),
    "$region": customer_address.get("province",""),
    "$country": customer_address.get("country","")
    }
    return customer_properties

def construct_order(shopify_order,products):
    """
    Assemble the order information from a given Shopify order and product info
    Args:
    shopify_order (obj): order object from Shopify order request
    products (obj): product properties for the Klaviyo Ordered
    Product/Placed Order payload from function construct_product
    Returns:
    order (obj): order properties for Klaviyo Placed Order payload
    """
    categories = []
    item_names = []
    for product in products:
        categories = categories + product.get("Categories")
        item_names.append(product.get("ProductName"))
    order = {
    "$event_id": shopify_order.get("id", ""),
    "$value": float('0'+shopify_order.get("total_price", "")),
    "Categories": categories,"ItemNames": item_names,
    "Discount Codes": shopify_order.get("discount_codes", ""),
    "Discount Value": shopify_order.get("total_discounts", ""),
    "Items": products
    }
    return order

def construct_product(shopify_product):
    """
    Assemble the product information from a given Shopify order line item
    Args:
    shopify_product (obj): line item object from an order in a Shopify
    order request
    Returns:
    product (obj): product properties for Klaviyo Ordered Product/Placed
    Order payload
    """
    # Get additional product details from Shopify"s API
    product_response = requests.request("GET",
    f"https://{SHOPIFY_API_AUTH}@{SHOPIFY_URL}{SHOPIFY_PRODUCTS_ENDPOINT}/{shopify_product.get('product_id','')}.json").json().get("product",{})
    categories = []
    for item in product_response.get("tags","").split(", "):
        categories.append(item)
    product = {
    "ProductID": shopify_product.get("product_id",""),
    "SKU": shopify_product.get("sku",""),
    "ProductName": shopify_product.get("name",""),
    "Quantity": shopify_product.get("quantity",""),
    "ItemPrice": float('0'+shopify_product.get("price","")),
    "RowTotal": float('0'+shopify_product.get("price","")) *
    shopify_product.get("quantity",""),
    "ProductURL":
    f"{SHOPIFY_URL}products/{product_response.get('handle','')}",
    "ImageURL": product_response.get("images",{})[0].get("src",""),
    "Categories": categories
    }
    return product

def klaviyo_track_request(event,customer_properties,properties,timestamp):
    """
    Send Klaviyo server-side Track request
    Args:
    payload (obj): JSON payload of an event to track
    Returns:
    response (obj): response object for logging/reporting purposes
    """
    # Construct final payload
    payload = {"token":KLAVIYO_PUBLIC_API_KEY,"event":event,"customer_properties":customer_properties,"properties":properties,"time":timestamp}
    # Convert the JSON payload to a string
    payload_string = json.dumps(payload)# Base64 encode the data for the request
    KLAVIYO_API_QUERY_STRING["data"]=base64.encodebytes(payload_string.encode())
    response = requests.request("GET", KLAVIYO_API_URL,
    params=KLAVIYO_API_QUERY_STRING)
    print(response.url)
    print(KLAVIYO_API_QUERY_STRING)
    print(response.text)
    # Return response for logging purposes
    return response

# Get all 2016 Shopify orders
response = requests.request("GET", f"https://{SHOPIFY_API_AUTH}@{SHOPIFY_URL}{SHOPIFY_ORDERS_ENDPOINT}.json", params=SHOPIFY_API_QUERY_STRING)

# Iterate through each order in 2016, process, and send it
for shopify_order in response.json().get("orders", []):
# Get the customer information to construct the customer_properties for the requests
    customer_properties = construct_customer_properties(shopify_order)

# Get each item in this order and append it to an "items" object
products=[]
# Get unix time from order
dt = datetime.strptime(shopify_order.get("created_at"),
'%Y-%m-%dT%H:%M:%S%z')
timestamp = int(time.mktime(dt.timetuple()))
shopify_order.get("id","")
for shopify_product in shopify_order.get("line_items",""):
    product = construct_product(shopify_product)
products.append(product)
# Add special Klaviyo properties for Ordered Product request
product.update({"$event_id": f"{shopify_order.get('id','')}_{product.get('ProductID')}"})
product.update({"$value": product.get("ItemPrice")})
klaviyo_track_request("Ordered Product",customer_properties,product,timestamp)
# Remove special Klaviyo properties from Ordered Product for Placed Order request
del(product["$event_id"])
del(product["$value"])
# Assemble and track order data
order = construct_order(shopify_order,products)
klaviyo_track_request("Placed Order",customer_properties,order,timestamp)