import os
import requests
import json

from dotenv import load_dotenv, find_dotenv


load_dotenv()
HS_APP_TOKEN = os.getenv('HS_APP_TOKEN')

def create_custom_obj(payload, APP_TOKEN):
    url = 'https://api.hubapi.com/crm/v3/schemas'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {APP_TOKEN}'
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    print(f"\n{response} - {response.text}\n")
    print("-" * 100)
    return response


if __name__ == '__main__':
    payload_student_course = {
    "labels": {
        "singular": "Student Course Instance",
        "plural": "Student Course Instances"
    },
    "requiredProperties": [
        "talentlms_user_id",
        "talentlms_course_id",
        "firstname",
        "lastname",
        "course_name"
    ],
    "searchableProperties": [
        "talentlms_user_id",
        "talentlms_course_id",
        "firstname",
        "lastname",
        "course_name"
    ],
    "secondaryDisplayProperties": [
    ],
    "properties": [
        {
        "name": "instance_name",
        "label": "Instance Name",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 1,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "firstname",
        "label": "First Name",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 2,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "lastname",
        "label": "Last Name",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 3,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "course_name",
        "label": "Course Name",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 4,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "talentlms_user_id",
        "label": "TalentLMS User ID",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 5,
        "type": "number",
        "fieldType": "number"
        },
        {
        "name": "talentlms_course_id",
        "label": "TalentLMS Course ID",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 6,
        "type": "number",
        "fieldType": "number"
        },
        {
        "name": "completed_on",
        "label": "Completed On",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 7,
        "type": "datetime",
        "fieldType": "date"
        },
        {
        "name": "completion_status",
        "label": "Completion Status",
        "groupName": "Student Course Instance Properties",
        "options": [
            {
            "label": "Not Attempted",
            "value": "not_attempted",
            "displayOrder": 1,
            },
            {
            "label": "Incomplete",
            "value": "incomplete",
            "displayOrder": 2,
            },
            {
            "label": "Completed",
            "value": "completed",
            "displayOrder": 3
            }
        ],
        "displayOrder": 8,
        "type": "enumeration",
        "fieldType": "select"
        },
        {
        "name": "completion_percent",
        "label": "Completion Percent",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 9,
        "type": "number",
        "fieldType": "number"
        },
        {
        "name": "total_time",
        "label": "Total Time",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 10,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "total_time_seconds",
        "label": "Total Time (seconds)",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 11,
        "type": "number",
        "fieldType": "number"
        },
        {
        "name": "last_accessed_unit_url",
        "label": "Last Accessed Unit Url",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 12,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "linkedin_badge",
        "label": "LinkedIn Badge",
        "groupName": "Student Course Instance Properties",
        "description": "URL link to LinkedIn Badge",
        "displayOrder": 13,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "email",
        "label": "Email",
        "groupName": "Student Course Instance Properties",
        "description": "Student email",
        "displayOrder": 14,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "live_session_datetime",
        "label": "Live Session Datetime",
        "groupName": "Student Course Instance Properties",
        "displayOrder": 15,
        "type": "datetime",
        "fieldType": "date"
        }
    ],
    "associatedObjects": [
        "CONTACT"
    ],
    "name": "student_course_instance",
    "primaryDisplayProperty": "instance_name",
    "metaType": "PORTAL_SPECIFIC"
    }

    # 2-73538172-7353817

    payload_course = {
    "labels": {
        "singular": "Course",
        "plural": "Courses"
    },
    "requiredProperties": [
        "talentlms_course_id",
        "course_name"
    ],
    "searchableProperties": [
        "talentlms_course_id",
        "course_name",
        "code"
    ],
    "secondaryDisplayProperties": [
        "talentlms_course_id",
        "code"
    ],
    "properties": [
        {
        "name": "talentlms_course_id",
        "label": "TalentLMS Course ID",
        "isPrimaryDisplayLabel": True,
        "groupName": "Course Properties",
        "displayOrder": 2,
        "hasUniqueValue": True,
        "type": "number",
        "fieldType": "number"
        },
        {
        "name": "course_name",
        "label": "Course Name",
        "groupName": "Course Properties",
        "displayOrder": 1,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "code",
        "label": "Code",
        "groupName": "Course Properties",
        "displayOrder": 3,
        "type": "string",
        "fieldType": "text"
        },
        {
        "name": "start_date",
        "label": "Start Date",
        "groupName": "Course Properties",
        "displayOrder": 4,
        "type": "date",
        "fieldType": "date"
        },
        {
        "name": "end_date",
        "label": "End Date",
        "groupName": "Course Properties",
        "displayOrder": 5,
        "type": "date",
        "fieldType": "date"
        },
        {
        "name": "live_session_datetime",
        "label": "Live Session Datetime",
        "groupName": "Course Properties",
        "displayOrder": 6,
        "type": "datetime",
        "fieldType": "date"
        },
        {
        "name": "assignment_due_date",
        "label": "Assignment Due Date",
        "groupName": "Course Properties",
        "displayOrder": 7,
        "type": "date",
        "fieldType": "date"
        },
        {
        "name": "cohort_id",
        "label": "Cohort ID",
        "groupName": "Course Properties",
        "displayOrder": 8,
        "type": "string",
        "fieldType": "text"
        }
    ],
    "associatedObjects": [
        "2-7353817"
    ],
    "name": "courses",
    "primaryDisplayProperty": "lastname" ,
    "metaType": "PORTAL_SPECIFIC"
    }

    # create_custom_obj(payload_student_course, HS_APP_TOKEN)
    create_custom_obj(payload_course, HS_APP_TOKEN)