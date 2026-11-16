#!/bin/sh
# a unique 1 KB query per request, otherwise Lucene compresses the docs and the 1 MB rollover never fires
seq "${1:-2000}" | xargs -P 8 -I{} sh -c 'curl -s -o /dev/null "http://127.0.0.1/?r=$(openssl rand -hex 512)"'
