from firebase import read

def generate_order_id():
    orders = read("orders") or {}

    if not isinstance(orders, dict) or len(orders) == 0:
        return "SRP001"

    existing = []
    for o in orders.values():
        oid = o.get("order_id", "")
        if oid.startswith("SRP"):
            try:
                num = int(oid.replace("SRP", ""))
                existing.append(num)
            except:
                pass

    if not existing:
        return "SRP001"

    next_id = max(existing) + 1
    return f"SRP{next_id:03d}"
