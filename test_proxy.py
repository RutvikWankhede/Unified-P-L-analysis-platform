import urllib.request

url = "http://127.0.0.1:3003/api/v1/pl/summary"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJBZG1pbiIsImV4cCI6MTc4NDAwNTMzOH0.Ao0taUxzfggn1eJXZF6qMRSkjTbCRJrKvzhgrKx1hd0"

req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Body:", response.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Headers:", e.headers)
    print("Body:", e.read().decode())
except Exception as e:
    print("Error:", e)
