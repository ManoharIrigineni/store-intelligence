import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8000/stores/STORE_BLR_002/metrics')
    print("Metrics Dashboard Response:", response.read().decode())
except Exception as e:
    print("Error hitting Metrics:", e)