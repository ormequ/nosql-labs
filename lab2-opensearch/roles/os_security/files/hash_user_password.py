"""Bcrypt hash with the salt derived from the username, so re-runs give the same hash. Password on stdin"""
import base64
import hashlib
import sys

import bcrypt

# bcrypt uses its own order of the base64 alphabet
STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
BCRYPT = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

user = sys.argv[1]
password = sys.stdin.buffer.read().rstrip(b"\n")
seed = hashlib.sha256(f"lab2-salt:{user}".encode()).digest()[:16]
salt = base64.b64encode(seed).decode().rstrip("=").translate(str.maketrans(STD, BCRYPT))
print(bcrypt.hashpw(password, f"$2b$12${salt}".encode()).decode())
