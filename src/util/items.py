import base64
import gzip
import io
from nbtlib import Compound
from util.functions import *


def decode_nbt(item_bytes) -> dict:
    """
    Decode => Decompress => Warp in io.BytesIO to parse the Base64-encoded data

    :param: item_bytes - Base64-encoded item data
    :return: Parsed NBT data as a Compound object
    """

    decoded_data = base64.b64decode(item_bytes)
    decompressed_data = gzip.decompress(decoded_data)
    return Compound.parse(io.BytesIO(decompressed_data))


def update_lbin(auction: dict, item: dict) -> None:
    """
    Update the lowest BIN price of an item.

    :param: auction - Auction data containing all item information
    :param: item - Single item information to update the BIN price
    :return: None
    """

    if not item["bin"]:
        return

    price = item.get("price", item.get("starting_bid"))
    nbt = decode_nbt(item["item_bytes"])

    tag = nbt[""]["i"][0]["tag"]
    extra_attributes = tag["ExtraAttributes"]
    item_id = str(extra_attributes.get("id"))

    if item_id not in auction:
        auction[item_id] = {"lbin": price}
        return

    if price < auction[item_id]["lbin"]:
        auction[item_id]["lbin"] = price