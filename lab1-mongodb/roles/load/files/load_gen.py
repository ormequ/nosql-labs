# W workers do inserts, finds, updates on <db>.<collection> for --seconds
# usage: see argparse defaults; password comes from --password-file, never argv
import argparse
import pathlib
import random
import threading
import time
from datetime import datetime, timezone

from pymongo import MongoClient

OPS = {"insert": 0, "find": 0, "update": 0}
lock = threading.Lock()


def worker(host, user, password, authdb, db, coll, seconds):
    client = MongoClient(host, username=user, password=password,
                         authSource=authdb, serverSelectionTimeoutMS=5000)
    collection = client[db][coll]
    stop = time.time() + seconds
    ops = {"insert": 0, "find": 0, "update": 0}
    inserted = []
    while time.time() < stop:
        r = random.random()
        if r < 0.4:
            name = f"load-{threading.get_ident()}-{time.time()}"
            collection.insert_one({
                "name": name,
                "value": random.randint(0, 1000),
                "created": datetime.now(timezone.utc),
            })
            inserted.append(name)
            ops["insert"] += 1
        elif r < 0.8:
            # find is lazy in pymongo, materialize the cursor so the query reaches the db
            list(collection.find({"value": {"$gte": random.randint(0, 900)}}).limit(10))
            ops["find"] += 1
        elif inserted:
            # updates must hit documents that exist, not a filter matching nothing
            collection.update_one(
                {"name": random.choice(inserted)},
                {"$set": {"value": random.randint(0, 1000)}},
            )
            ops["update"] += 1
    with lock:
        for k in OPS:
            OPS[k] += ops[k]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True, help="host:port")
    p.add_argument("--user", required=True)
    p.add_argument("--password-file", required=True,
                   help="root-only file with `password: <value>` on one line")
    p.add_argument("--authdb", default="admin")
    p.add_argument("--db", default="shop")
    p.add_argument("--collection", default="load_docs")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--seconds", type=int, default=180)
    args = p.parse_args()
    line = pathlib.Path(args.password_file).read_text().strip()
    password = line.split(":", 1)[1].strip()

    threads = [
        threading.Thread(target=worker,
                         args=(args.host, args.user, password, args.authdb,
                               args.db, args.collection, args.seconds))
        for _ in range(args.workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"{OPS}")


if __name__ == "__main__":
    main()
