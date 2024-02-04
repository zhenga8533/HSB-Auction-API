import requests as rq
import json
import os
import pickle
from datetime import datetime
from util.functions import decode_nbt, average_objects, update_kuudra_piece

AUCTION_URL = 'https://api.hypixel.net/v2/skyblock/auctions'


def get_active_auction(items: dict, page: int) -> None:
    """
    Fetch auction data and process items lbin data.

    :param: items - Item data object
    :param: page - Page number of the auction data
    :return: None
    """

    response = rq.get(AUCTION_URL, params={'page': page})

    if response.status_code != 200:
        print(f"Failed to get data. Status code: {response.status_code}")
        return

    data = response.json()
    # print(f"Auction Looping ({page + 1}/{data['totalPages']})")
    for auction in data["auctions"]:
        if not auction['bin']:
            continue

        # Get Item ID
        nbt_object = decode_nbt(auction)
        extra_attributes = nbt_object['']['i'][0]['tag']['ExtraAttributes']

        # Item ID Handling
        item_id = str(extra_attributes.get('id'))
        if item_id == "PET":
            pet_info = json.loads(nbt_object['']['i'][0]['tag']['ExtraAttributes']['petInfo'])
            item_id = f'{pet_info["tier"]}_{pet_info["type"]}'
        elif item_id == "RUNE":
            runes = nbt_object['']['i'][0]['tag']['ExtraAttributes']['runes']
            runeKey, runeValue = next(iter(runes.items()))
            item_id = f"{runeKey}_{int(runeValue)}"
        current = items.get(item_id)

        # Item Cost Handling
        item_bin = auction['starting_bid']
        item = {'lbin': item_bin if current is None else min(item_bin, current.get('lbin'))}

        # Attributes Handling
        attributes = extra_attributes.get('attributes')
        item['attributes'] = {} if current is None else current.get('attributes') or {}

        if attributes is not None:
            attribute_keys = sorted(attributes.keys())
            check_combo = True
            is_kuudra_piece = False

            # Get lbin single attribute
            for attribute in attribute_keys:
                tier = attributes[attribute]
                if tier > 5:
                    check_combo = False
                attribute_cost = item_bin / (2 ** (tier - 1))
                if attribute_cost <= item['attributes'].get(attribute, attribute_cost):
                    item['attributes'][attribute] = attribute_cost

                # Set Kuudra Armor Attributes
                is_kuudra_piece = update_kuudra_piece(items, item_id, attribute, attribute_cost)

            # Get lbin attribute combination if value > X (to check for Kuudra god roll)
            if is_kuudra_piece:
                item_combos = current.get('attribute_combos', {}) if current and 'attribute_combos' in current else {}
                if check_combo and len(attribute_keys) > 1:
                    attribute_combo = ' '.join(attribute_keys)
                    item_combos[attribute_combo] = min(item_bin, item_combos.get(attribute_combo, item_bin))
                if item_combos:
                    item['attribute_combos'] = item_combos

        # Delete attribute variable for no attribute items
        if item['attributes'] == {}:
            del item['attributes']

        # Set Item
        items[item_id] = item

    if page + 1 < data['totalPages']:
        get_active_auction(items, page + 1)
    else:
        manage_items(items)
        # print('Auction Process Complete!')


def manage_items(items: dict) -> None:
    """
    Manages the provided 'items' dictionary, saving it to a file for persistence.

    :param: items - A dictionary containing information about items, where keys are item IDs.
    :return: None
    """

    # Check for data directory and files
    if not os.path.exists('data/active'):
        os.makedirs('data/active')
    if not os.path.isfile('data/active/day'):
        with open('data/active/day', 'wb') as file:
            pickle.dump(-1, file)

    save_items(items)


def save_items(items: dict) -> None:
    """
    Saves the provided 'items' dictionary to files, managing daily and weekly averages for persistence.

    :param: items - A dictionary containing information about items, where keys are item IDs.
    :return: None
    """

    today = datetime.now().weekday()

    # Load and save current day
    with open(f'data/active/day', 'rb') as file:
        day = pickle.load(file)
    with open('data/active/day', 'wb') as file:
        pickle.dump(today, file)

    # Average out data with higher bias on day/hour
    if today == day:
        with open(f'data/active/auction_{today}', 'rb') as file:
            data = pickle.load(file)
        average_objects(items, data, 2)

    # Save new data to current day file
    with open(f'data/active/auction_{today}', 'wb') as file:
        pickle.dump(items, file)

    # Average weekly values
    count = 1
    for file_name in os.listdir('data/active'):
        if file_name != f'auction_{today}' and file_name != 'day':
            count += 1
            with open(f'data/active/{file_name}', 'rb') as file:
                average_objects(items, pickle.load(file), count)

    # Save average to auction file
    with open(f'data/active/auction', 'wb') as file:
        pickle.dump(items, file)
