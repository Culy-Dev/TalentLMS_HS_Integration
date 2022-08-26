import os
import requests
import json




def create_custom_prop(payload, APP_TOKEN):
    url = 'https://api.hubapi.com/crm/v3/properties/2-7353817'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {APP_TOKEN}'
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    print(f"\n{response} - {response.text}\n")
    print("-" * 100)
    return response

def get_custom_prop(APP_TOKEN):
    url = 'https://api.hubapi.com/crm/v3/properties/2-7353817'
    url = 'https://api.hubapi.com/crm/v3/properties/2-7353817/live_session_datetime'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {APP_TOKEN}'
    }

    response = requests.get(url, headers=headers)

    print(f"\n{response} - {response.text}\n")
    print("-" * 100)
    return response

if __name__ == '__main__':
    # payload = {
    # "name": "live_session_datetime",
    # "label": "Live Session Datetime",
    # "type": "datetime",
    # "fieldType": "date",
    # "groupName": "Student Class Instance Properties",
    # "hidden": False,
    # "displayOrder": 2,
    # "hasUniqueValue": False
    # }

    # create_custom_prop(payload, HS_APP_TOKEN)
    HS_TOKEN='deleted'
    print(get_custom_prop(HS_TOKEN))