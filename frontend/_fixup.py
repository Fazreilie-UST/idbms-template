import re, pathlib
p = pathlib.Path("/home/fbinalex/NPI-IDBMS/frontend/src/features/stocks/services/stock_service.js.tmp")
t = p.read_text()
t = re.sub(r'authHeaders\(\{\}, "(GET|POST)"\)', "authHeaders()", t)
p.write_text(t)
print("done")
