from firebase import read
from datetime import datetime

def generate_order_id():
    orders = read("orders")

    if not orders or not isinstance(orders, dict):
        next_id = 1
    else:
        nums = []
        for o in orders.values():
            if isinstance(o, dict) and "order_id" in o:
                try:
                    nums.append(int(o["order_id"].replace("SRP", "")))
                except:
                    pass

        next_id = max(nums) + 1 if nums else 1

    return f"SRP{next_id:03d}"

def today():
    return datetime.now().strftime("%d-%m-%Y")
