import requests

base_url = "http://postgrest-api-demo:3000/orders_n"


params = {
    "id": "eq.3"
}

response = requests.get(base_url, params=params)

if response.ok:
    todos = response.json()
    for todo in todos:
        print(todo)
else:
    
    print("Error:", response.status_code, response.text)
