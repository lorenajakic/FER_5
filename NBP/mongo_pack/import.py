from pymongo import MongoClient
from datetime import datetime, timezone


client = MongoClient("mongodb://root:rootnmbp@localhost:27017/admin")

db = client.amazon
collection = db.reviews

BATCH_SIZE = 1000
batch = []

def save_batch(batch):
    if batch: collection.insert_many(batch)

    return []

with open("/Users/lorenajakic/Downloads/Video_Games.txt", "r", encoding="utf-8") as f:
    product, review = {}, {}

    for line in f:
        line = line.strip()

        if not line:
            doc = { "product": product, "review": review }
            batch.append(doc)

            if len(batch) >= BATCH_SIZE: batch = save_batch(batch)

            product, review = {}, {}
            continue

        key, value = line.split(":", 1)
        value = value.strip()

        if key.startswith("product/"):
            field = key.split("/")[1]

            if field == "price":
                try: product[field] = float(value)
                except ValueError:
                    product[field] = None
            else: product[field] = value

        elif key.startswith("review/"):
            field = key.split("/")[1]

            if field == "score": review[field] = float(value)
            elif field == "time": review[field] = datetime.fromtimestamp(int(value), tz=timezone.utc)
            else: review[field] = value

batch = save_batch(batch)
