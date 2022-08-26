from pipedream.script_helpers import (steps, export)
import requests
import json

# TOKEN = DO THE TOKEN HERE


headers = {
    'Content-Type': 'application/json',
    f'Authorization': 'Bearer {TOKEN}}'
}

student_email = steps["trigger"]["event"]["body"]["email"]
course_name = steps["trigger"]["event"]["body"]["course_name"]

#FIND THE INSTANCE
# replace with student_course_instace in production
url_search = 'https://api.hubapi.com/crm/v3/objects/2-7353817/search' 

payload_search = {
  "filterGroups": [
    {
      "filters": [
        {
          "value": student_email,
          "propertyName": "email",
          "operator": "EQ"
        },
        {
          "value": course_name,
          "propertyName": "course_name",
          "operator": "EQ"
        }
      ]
    }
  ],
  "sorts": [
    {
      "propertyName": "hs_createdate",
      "direction": "DESCENDING"
    }
  ],
  "properties": [
    "hs_object_id"
  ],
  "limit": 10,
  "after": 0
}


res = requests.post(url_search, data=json.dumps(payload_search), headers=headers)

# MIGRATE SURVEY DATA
instance_id = res.json()['results'][0]['id']
# replace with student_course_instace in production
url_update = f'https://api.hubapi.com/crm/v3/objects/2-7353817/{instance_id}'

payload_update = {
  "properties": {
    "email": student_email,
    "course_name":  course_name,
    "phone": steps["trigger"]["event"]["body"]["phone"],
    "have_a_good_time_": steps["trigger"]["event"]["body"]["have_a_good_time_"]
  }
}


res_survey = requests.patch(url_update, data=json.dumps(payload_update), headers=headers)

export(res_survey, res_survey.text)
