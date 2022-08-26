import json

from datetime import date, datetime
from calendar import timegm

from hubapi import search_records, UpdateRecordsHandler
from logger import get_logger

from panda_linkedin_urls import PandaLinkedIn
from due_date import DueDate

from models import SQLITE_DB

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

class LinkedInBadgeDueDate:

    def __init__(self, isodate=date.today()):
        self.engine, self.session = self.get_session()
        self.instance_obj = '2-7353817'
        self._payload_search_hs = {
            "filterGroups": [
                {
                "filters": [
                    {
                    "value": 'true',
                    "propertyName": "certificate_checkbox",
                    "operator": "EQ"
                    },
                    {
                    "propertyName": "linkedin_badge",
                    "operator": "NOT_HAS_PROPERTY"
                    }
                ]
                }
            ],
            "properties": [
                "hs_object_id",
                "firstname",
                "lastname",
                "course_name", 
                "linkedin_company_id"
            ],
            "limit": 100,
            "after": 0
        } 
        self.isodate = isodate
        midnight=datetime.combine(self.isodate, datetime.min.time())
        self.hs_date=timegm(midnight.timetuple()) * 1000
        self.logger = get_logger('LinkedInAssignDueDateUpdate')
        self.update_payload_hs = {'inputs': []}
        # Change the object here during projection

    def run(self):
        self._linkedinbadge()
        self._assign_date()

    def get_session(self):
        """Creates a new database self.session for instant use"""

        engine = create_engine(SQLITE_DB )
        Session = sessionmaker(bind = engine)
        session = scoped_session(Session)
        return (engine, session)

    def _linkedinbadge(self):
        self.logger.info(f'--- BEGIN LINKEDIN CERTIFICATIONS CREATION ({self.isodate}) ---\n')

        badge = LinkedInBadgeDueDate()

        self.logger.info('Retrieving data from Hubspot...')
        instances_json = search_records(self.instance_obj, self._payload_search_hs).json()
        self.logger.info(f'... Obtained {len(instances_json["results"])} instances to create certifications for.\n')

        self.logger.info(f'Creating Certifications and LinkedIn URL\n')
        for instance in instances_json["results"]:
            try:
                record = PandaLinkedIn(instance, self.isodate, self.engine, self.session)
                record.gather_urls()
                self.update_payload_hs['inputs'].append({'id': instance['id'], 
                                                        'properties': record.urls | {'certificate_issue_year': int(self.isodate.year), 
                                                                                    'certificate_issue_month': int(self.isodate.month),
                                                                                    'certificate_issue_date': self.hs_date}})
            except SQLAlchemyError as s:
                self.logger.error(s, exc_info=True)
                continue
            except Exception as e:
                self.logger.error(e, exc_info=True)
                continue
        self.logger.info(f'\nUrls for {len(self.update_payload_hs["inputs"])} instance(s) have been created.\n')

        add_linkedin_badge = UpdateRecordsHandler('2-7353817')
        add_linkedin_badge.dispatch(self.update_payload_hs)

        self.session.close()
        self.engine.dispose()

        self.logger.info(f'\n--- END LINKEDIN CERTIFICATIONS CREATION ---\n')

    def _assign_date(self):
        self.logger.info(f'\n--- BEGIN ASSIGNMENTMENT DUE DATE CALCULATION ---\n')

        
        get_appropriate_records = DueDate()
        get_appropriate_records.calc_assign_due_date()
        add_assign_due_date = UpdateRecordsHandler('2-7353817')
        add_assign_due_date.dispatch(get_appropriate_records.payload)
        try:
            self.logger.info(f'\n{len(get_appropriate_records.payload["inputs"])} due date(s) have been added.\n')
        except Exception as e:
            self.logger.error(e, exc_info=True)

        self.logger.info(f'\n--- END ASSIGNMENTMENT DUE DATE CALCULATION ({self.isodate}) ---')

if __name__ == '__main__':
    daily_run = LinkedInBadgeDueDate()
    daily_run.run()