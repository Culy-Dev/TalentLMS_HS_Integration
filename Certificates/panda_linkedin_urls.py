import requests
import os
import logging
import json
import time

from urllib.parse import quote, urlencode
from dotenv import load_dotenv

from sqlalchemy import insert, desc, create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

from models import CertIdHistory, SQLITE_DB 

load_dotenv()

logger = logging.getLogger(F'LinkedInAssignDueDateUpdate.{__name__}')

PANDA_API = os.environ['PANDA_API']
TEMPLATE_ID = os.environ['TEMPLATE_ID']
FOLDER_ID = os.environ['FOLDER_ID']

headers = {'Authorization': f'API-Key {PANDA_API}', 'Content-Type': 'application/json'}

def api_log(res, success_code):
    if res.status_code == success_code:
        logger.debug(F'"METHOD": "{res.request.method}", '
                    F'"STATUS_CODE": "{res.status_code}",'
                    F'"URL": "{res.url}"', exc_info=True)
        return res
    else:
        logger.warning(F'"METHOD": "{res.request.method}", '
                       F'"STATUS_CODE": "{res.status_code}",'
                       F'"URL": "{res.url}",'
                       F'"FAIL RESPONSE": "{res.text}"', exc_info=True)
        return None


class PandaLinkedIn:
    def __init__(self, hs_record, date, engine=None, session=None):
        self.urls = {}
        self.engine = engine
        self.session = session
        self.firstname = hs_record['properties']['firstname']
        self.lastname = hs_record['properties']['lastname']
        self.course_name = hs_record['properties']['course_name']
        self.linkedin_company_id = hs_record['properties']['linkedin_company_id']
        self.cert_id = self.create_cert_id(hs_record['properties']['hs_object_id'])
        self.date = date

    def create_cert_id(self, hs_obj_id):
        stmt = CertIdHistory(hs_instance_id=hs_obj_id)
        self.session.add(stmt)
        self.session.commit()
        cert_id_query = str(self.session.query(CertIdHistory.cert_id).filter_by(hs_instance_id=hs_obj_id).first()[0]).zfill(10)
        cert_id = f'{cert_id_query[:3]}-{cert_id_query[3:8]}-{cert_id_query[8:]}'
        self.urls['unique_certificate_id'] = cert_id 
        return cert_id 


    def gather_urls(self):
        doc_id = self.create_pd_cert().json()['id']
        time.sleep(5) # Takes 3-5 seconds to change from document.uploaded to document.draft
        self.update_doc_status(doc_id) # Must change to document.completed to get
        cert_id = self.create_cert_url(doc_id).json()['id']
        cert_url = f'https://app.pandadoc.com/s/{cert_id}'
        self.urls['certificate_file_url'] = cert_url
        self.urls['linkedin_badge'] = self.create_linkedin_url(cert_url)


    def create_pd_cert(self):
        # template ID logic; if "generate" field known and is true, push corresponding PD template ID and timestamp to dict
        url = "https://api.pandadoc.com/public/v1/documents"
        payload = {
            "name": f"{self.course_name} - {self.firstname} {self.lastname} Certificate",
            "template_uuid": TEMPLATE_ID,
            "folder_uuid": FOLDER_ID ,
            "recipients": [{"email": "example@email.com"}],
            "tokens": [
                {"name": "Student FName Student LName", "value": f"{self.firstname} {self.lastname}"},
                {"name": "Course Name", "value": self.course_name},
                {"name": "Date Issued", "value": str(self.date)}
            ]
        }

        res = requests.post(url, headers=headers, data=json.dumps(payload))

        return api_log(res, 201)

    def update_doc_status(self, doc_id):
        url = f"https://api.pandadoc.com/public/v1/documents/{doc_id}/status/"

        payload = {
            "status": 2
        }

        res = requests.patch(url, headers=headers, data=json.dumps(payload))

        return api_log(res, 204)

    def create_cert_url(self, doc_id):
        url = f"https://api.pandadoc.com/public/v1/documents/{doc_id}/session"

        payload = {
            'silent': 'true',
            "recipient": "example@email.com"
        }

        res= requests.post(url, data=json.dumps(payload), headers=headers)

        return api_log(res, 201)

    def create_linkedin_url(self, merged_doc_url):
        base_url = "https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME&name="
        name_param = f'{quote("Certificate of Completion: " + self.course_name, safe="")}&'
        params_1= {
            'organizationId': self.linkedin_company_id,
            'issueYear': str(self.date.year),
            'issueMonth': str(self.date.month)
        }
        certUrl_param = f'{quote(merged_doc_url, safe="")}&'
        params_2 = {'certId': self.cert_id}
    
        final_url = base_url + name_param +  urlencode(params_1) + "&certUrl=" + certUrl_param + urlencode(params_2)

        return final_url
