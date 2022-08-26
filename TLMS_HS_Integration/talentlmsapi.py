"""
Contains functions that call TalentLMS API.
"""
from doctest import testfile
import os
import json 
import logging
import html

from datetime import datetime, timezone
from time import sleep
import requests

from requests_toolbelt import sessions
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from dotenv import load_dotenv

from models import Contacts, Courses, StudentCourseInstance, TimeTracking, SQLITE_DB 
from transform import return_unix_time, convert_dt_to_utc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from pprint import pprint # delete

load_dotenv()
TALENTLMS_API = os.getenv('TALENTLMS_API')


logger = logging.getLogger(f'HourlyUpdate.{__name__}')

# ADD YOUR DOMAIN BELOW
BASE_URL = 'https://your_domain.talentlms.com'
# Lets you fake a browser visit using a python requests or command wget
headers = {
    'Authorization': f'{TALENTLMS_API}'
    }

talentlms_http = sessions.BaseUrlSession(BASE_URL)
talentlms_http.mount(BASE_URL, HTTPAdapter(max_retries=Retry(backoff_factor=1)))
talentlms_http.headers.update(headers)

# Logging Function
def talentlms_log(res):
    res_log = F'"METHOD": {res.request.method}, "STATUS_CODE": {res.status_code}, "URL": {res.url}'
    try:
        if 'does not exit' in res.text:
            logger.debug(F'"LOG": "No results from TalentLMS request.", {res_log}', exc_info=True)
            return None
        elif 'error' in res.text:
            logger.error(F'"LOG": "Unable to process TalentLMS request.", {res_log}', exc_info=True)
            return None
        else:
            logger.debug(F'"LOG": "Successful TalentLMS request.", {res_log}', exc_info=True)
            return res
    except ValueError:
        logger.error(F'"LOG": "Failed TalentLMS request, unknown error.", {res_log}', exc_info=True)
        return None

# Request Class
class TalentLMS: # Make this into a Parent Class and create some child classes
    # possibly put a batch limit here

    def __init__(self, engine=None, session=None):
        self.engine = engine
        self.session = session
        self.all_students = self.get_all_students() 
        self.all_courses = self.get_all_courses() 
        self.student_ids = set() # tell use what they do
        self.course_ids_session = {}

        try:
            self.time_track = self.session.query(TimeTracking.last_modified_time).first()[0]
        except SQLAlchemyError as s:
           logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
        
    # Request Helper Functions
    def get_all_courses(self):
        endpoint = 'api/v1/courses/'
        res = talentlms_http.get(endpoint)
        return talentlms_log(res)

    def get_course(self, course_id):
        endpoint = f'api/v1/courses/id:{course_id}'
        res = talentlms_http.get(endpoint)
        return talentlms_log(res)

    def get_all_students(self):
        endpoint = 'api/v1/users/'
        res = talentlms_http.get(endpoint)
        return talentlms_log(res)

    def get_student(self, user_id):
        endpoint = f'api/v1/users/id:{user_id}'
        res = talentlms_http.get(endpoint)
        return talentlms_log(res)
    
    def get_timeline_of_unit(self, unit_id, eventType="unitprogress_assignment_answered"):
        endpoint = f'api/v1/gettimeline/event_type:{eventType},unit_id:{unit_id}' #
        res = talentlms_http.get(endpoint)
        return talentlms_log(res)

    def move_courses_to_sqlite(self):
        order_entries = []
        for course in self.all_courses.json():
            course_datetime = return_unix_time(course['last_update_on'])
            # For Initial Migration
            # if course_datetime > self.time_track or course['custom_field_3'] is None or course['custom_field_4'] is None or (return_unix_time(course['custom_field_3']) - 2629743 <= self.time_track <= return_unix_time(course['custom_field_4']) + 2629743):
            if course['custom_field_3'] is not None or course['custom_field_4'] is not None or course['custom_field_5'] is not None or course['custom_field_6'] is not None or course['custom_field_7'] is not None or course_datetime > self.time_track:
                try:
                    code=course['code']
                    live_session_dt_str = course['custom_field_5']
                    if live_session_dt_str is not None:
                        session_date_unix, session_time = convert_dt_to_utc(live_session_dt_str)
                    else:
                        session_date_unix = None
                        session_time = None
                    added_courses = Courses(    
                                            talentlms_course_id=course['id'],
                                            course_name=course['name'],
                                            code=code,
                                            description=course['description'], 
                                            start_date=return_unix_time(course['custom_field_3']), 
                                            end_date=return_unix_time(course['custom_field_4']),
                                            live_session_datetime=session_date_unix,
                                            session_time=session_time,
                                            assignment_due_date=return_unix_time(course['custom_field_6']),
                                            cohort_id=course['custom_field_7']
                                            )
                    order_entries.append(added_courses)
                    # # 2629743 = a month in unix
                    self.course_ids_session[course['id']] = {'code': code, 'session_date_unix': session_date_unix, 'session_time': session_time, 'assign_complete_ids': []}
                    logger.info('Grabbing individual course records:')
                    course_json = self.get_course(course['id']).json()
                    sleep(.36)
                    for unit in course_json['units']:
                        if unit['type'] == 'Assignment':
                            completed_users = get_timeline_of_unit(unit['id']).json()
                            sleep(.36)
                            for user in completed_users:
                                self.course_ids_session[course['id']]['assign_complete_ids'].append(user['user_id'])
                    # logger.info(course_json)
                    # course_json.json()
                    for user in course_json['users']:
                        self.student_ids.add(user['id'])  
                except SQLAlchemyError as s:
                    logger.error(s, exc_info=True)
                    continue
                except Exception as e:
                    logger.error(e, exc_info=True)
                    continue 
        try: 
            self.session.add_all(order_entries)
            self.session.commit()
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)

    def move_users_to_sqlite(self):
        order_entries = []
        for student in self.all_students.json():
            student_datetime = student['last_updated_timestamp']
            if int(student_datetime) * 1000 > self.time_track:
                try:
                    added_contact = Contacts( 
                                            talentlms_user_id=student['id'],
                                            firstname=student['first_name'],
                                            lastname=student['last_name'],
                                            login=student['login'],
                                            email=student['email'],
                                            hs_content_membership_status=student['status']
                                            )
                    order_entries.append(added_contact)
                    self.student_ids.add(student['id'])
                except SQLAlchemyError as s:
                    logger.error(s, exc_info=True)
                    continue
                except Exception as e:
                    logger.error(e, exc_info=True)
                    continue
        # self.session.begin_nested()
        try: 
            self.session.add_all(order_entries)
            self.session.commit()
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)

    def move_instances_to_sqlite(self):
        # own function if a student instance is updated and studen't doesn't. Potentially pull 
        order_entries = []
        logger.info('Grabbing individual student records:')
        for student_id in self.student_ids:
            instance_json = self.get_student(student_id).json()
            sleep(.36)
            for course in instance_json["courses"]:
                course_id = course['id']
                if course_id in self.course_ids_session.keys():
                    if student_id in self.course_ids_session[course_id]['assign_complete_ids']:
                        assignment_status = "Yes"
                    else: 
                        assignment_status = "No"
                    try:
                        added_instance = StudentCourseInstance( 
                                        talentlms_user_id=student_id,
                                        talentlms_course_id=course['id'],
                                        instance_name=f"{instance_json['last_name']} {instance_json['first_name']}: {html.unescape(course['name'])}",
                                        firstname=instance_json['first_name'], 
                                        lastname=instance_json['last_name'],
                                        course_name=course['name'],
                                        code=self.course_ids_session[course['id']]['code'],
                                        company_cohort_id=instance_json['custom_field_4'],
                                        completed_on=int(course['completed_on_timestamp']) * 1000 \
                                            if course['completed_on_timestamp'] is not None \
                                            else course['completed_on_timestamp'],
                                        completion_status=course['completion_status'],
                                        completion_percent=course['completion_percentage'],
                                        email=instance_json['email'],
                                        live_session_datetime=self.course_ids_session[course['id']]['session_date_unix'],
                                        role=course['role'],
                                        session_time=self.course_ids_session[course['id']]['session_time'],
                                        status = instance_json['status'],
                                        total_time=course['total_time'],
                                        total_time_seconds=course['total_time_seconds'],
                                        last_accessed_unit_url=course['last_accessed_unit_url'],
                                        assignment_complete=assignment_status
                                        )
                        order_entries.append(added_instance)
                    except SQLAlchemyError as s:
                        logger.error(s, exc_info=True)
                        continue
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        continue
        try: 
            self.session.add_all(order_entries)
            self.session.commit()
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
