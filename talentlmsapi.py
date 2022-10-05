"""
Contains functions that calls TalentLMS API.
"""
import os
import json 
import logging
import html
import re
import requests

from time import sleep
from webbrowser import get


from requests_toolbelt import sessions
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from dotenv import load_dotenv

from models import Contacts, Courses, StudentCourseInstance, TimeTracking, SQLITE_DB 
from transform import return_unix_time, convert_dt_to_utc, remove_string
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from hubapi import read_property, add_value_to_property

load_dotenv()
TALENTLMS_API = os.getenv('TALENTLMS_API')


logger = logging.getLogger(f'HourlyUpdate.{__name__}')

BASE_URL = 'https://company_name.talentlms.com'
# Lets you fake a browser visit using a python requests or command wget
headers = {
    'Authorization': f'{TALENTLMS_API}'
    }

talentlms_http = sessions.BaseUrlSession(BASE_URL)
talentlms_http.mount(BASE_URL, HTTPAdapter(max_retries=Retry(backoff_factor=1)))
talentlms_http.headers.update(headers)

# Logging Function
def talentlms_log(res):
    """Takes an api response and sets logging messaged based on certain criteria

    Args:
        res (class): contains the server's response to the HTTP request

    Returns:
        res (class): same as above or None depending on certain criteria
    """
    res_log = F'"METHOD": {res.request.method}, "STATUS_CODE": {res.status_code}, "URL": {res.url}'
    try:
        if 'does not exist' in res.text:
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

    def __init__(self, isodatetime, engine=None, session=None):
        self.isodatetime = isodatetime
        self.engine = engine 
        self.session = session
        self.all_students = self.get_all_students() # Gathers all users from TalentLMS
        self.all_courses = self.get_all_courses() # Gathers all courses from TalentLMS
        # A unique set of student ids obtained from courses that pass a certain criteria. 
        # This is used to later compare with information to lessen the amount of API calls needed
        self.student_ids = set() 
        # A dictionary where the keys are certain courses to be checked. code, session_date_unix, 
        # session_time, and assign_complete_ids from course TalentsLMS API call to be used in 
        # instances
        self.course_ids_session = {} 

        # 2-8311841 is the custom object internal name in hubspot for courses
        # Get all the values from the property: course_template_name
        course_template_name_payload = read_property('2-8311841', 'course_template_name').json()
        # Gathers a dictionary of {course code: course name}
        self.course_templates = {option['value']: option['label'] for option in course_template_name_payload['options']}

        try:
            # Get the last datetime the integration ran
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
        endpoint = f'api/v1/gettimeline/event_type:{eventType},unit_id:{unit_id}' 
        res = talentlms_http.get(endpoint)
        return talentlms_log(res)

    def move_courses_to_sqlite(self):
        """
        Move the courses obtained from TalentLMS that pass certain criteria to the Courses table
        in SQLite
        """
        order_entries = []
        # Loop through all the courses
        for course in self.all_courses.json():
            # The datetime that the course was last update in unix epoch  (milliseconds)
            course_datetime = return_unix_time(course['last_update_on'])
            # If any of the custom fields are empty or if the last time the course was updated is
            # newer than the last time the integration run add it to the database
            if course['custom_field_3'] is not None or course['custom_field_4'] is not None or course['custom_field_5'] is not None or course['custom_field_6'] is not None or course['custom_field_7'] is not None or course_datetime > self.time_track:
                try:
                    course_template_name = None
                    course_template_code = None
                    code=course['code']
                    # strip the course code front of any numbers and split from the last dash
                    transformed_code = code.lstrip('0123456789').rpartition("-")
                    template_code = transformed_code[0] 
                    # If you split from the last dash and it's a T
                    if transformed_code[-1] == "T":
                        # Remove (Template) from the course name
                        course_label = remove_string(course['name']) 
                        # if the course code does not exist in the Hubspot prop course_template_name as an internal name
                        if template_code not in self.course_templates.keys():
                            # and if the course name does not exist in the Hubspot prop course_template_name as a UI name
                            if course_label not in self.course_templates.values():
                                # Create it and add it
                                add_value = {
                                    "label": course_label,
                                    "value": template_code
                                    }
                                upd_prop_course_req = add_value_to_property('2-8311841', 'course_template_name', add_value)
                                upd_prop_instance_req = add_value_to_property('2-8311962', 'course_template_name', add_value)
                                self.course_templates[template_code] = course_label
                                course_template_code = course_template_name = template_code
                            else:
                                # If the course code does not already exist in Hubspot
                                for value, label in self.course_templates.items():
                                    # But the course name does exist in Hubspot
                                    if label == course_label:
                                        # the wrong course code is on TalentLMS, so set it to
                                        # whatever is in Hubspot
                                        course_template_code = course_template_name = value
                        else:
                            # if the course code does exist, just set both of these to it
                            course_template_code = course_template_name = template_code
                    else: # if the split is not a T
                        # And it's in the list of values in the property
                        if template_code in self.course_templates.keys():
                            course_template_code = course_template_name = template_code
                        # If not in the list of values of the property
                        else:
                            course_template_name = None
                            course_template_code = template_code
                    live_session_dt_str = course['custom_field_5']
                    if live_session_dt_str is not None:
                        # Changes the TalentLMS session date to unix time and a string of just the time in EST/EDT
                        session_date_unix, session_time = convert_dt_to_utc(live_session_dt_str)
                    else:
                        session_date_unix = None
                        session_time = None
                    # Add all data to the Courses Table
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
                                            cohort_id=course['custom_field_7'],
                                            course_template_name=course_template_name,
                                            course_template_code=course_template_code,
                                            trigger_datetime=return_unix_time(self.isodatetime)
                                            )
                    order_entries.append(added_courses)
                    # Keep a record of ids to be TalentLMS API called along with code, session_date_unix, session_time, assign_complete_id to be added to the HS student_course_instance object
                    self.course_ids_session[course['id']] = {'code': code, 'session_date_unix': session_date_unix, 'session_time': session_time, 'assign_complete_ids': []}
                    logger.info('Grabbing individual course records:')
                    course_json = self.get_course(course['id']).json()
                    # sleep to avoid rate limits
                    sleep(.36)
                    # Check the units
                    for unit in course_json['units']:
                        # Find the unit with type of Assignment assigned to the course
                        if unit['type'] == 'Assignment':
                            # If exists, do an TalentLMS API call to find all the student ids that have completed the assignment
                            completed_users = self.get_timeline_of_unit(unit['id']).json()
                            sleep(.36)
                            for user in completed_users:
                                # Put all the student ids that have completed the assignment in the course_ids_session dictionary
                                self.course_ids_session[course['id']]['assign_complete_ids'].append(user['user_id'])
                    for user in course_json['users']:
                        # Grab all the student id in the course (This includes active and inactive students)
                        self.student_ids.add(user['id'])  
                except SQLAlchemyError as s:
                    logger.error(s, exc_info=True)
                    self.session.rollback()
                    continue
                except Exception as e:
                    logger.error(e, exc_info=True)
                    continue 
        try: 
            self.session.add_all(order_entries)
            self.session.commit()
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
            self.session.rollback()
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
            pass

    def move_users_to_sqlite(self):
        """
        Moves all students to the Contacts table based on certain criteria
        """
        order_entries = []
        for student in self.all_students.json():
            # Check to see if the last updated student information is newer than the last time the program ran
            student_datetime = student['last_updated_timestamp']
            if int(student_datetime) * 1000 > self.time_track:
                try:
                    # Add to the Contacts Table
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
        try: 
            self.session.add_all(order_entries)
            self.session.commit()
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
            self.session.rollback()
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
            pass

    def move_instances_to_sqlite(self):
        """
        Brings over information from the student and courses TalentLMS API call to create a record for a student taking a course
        The amount of API calls or decreased thanks to self.student_ids and self.course_ids_session keys (course_ids), which passed 
        the criteria of having a last_updated time that is newer than the last time the program has run.
        Information stored earlier in self.course_ids_session is also gather for the student_course_instance records
        """
        order_entries = []
        logger.info('Grabbing individual student records:')
        # Loop only through students that are currently in courses
        for student_id in self.student_ids:
            instance_json = self.get_student(student_id).json()
            sleep(.36)
            # Loop through all the courses the student is taking
            for course in instance_json["courses"]:
                course_id = course['id']
                # If the course in the student data is also in the courses the pass the criteria of being newer than the last time the program ran
                # Or, the custom objects are filled, then add the data to the StudentCourseInstance Table
                # This is done to decrease the number of API calls needed
                if course_id in self.course_ids_session.keys():
                    # Check if the student has already completed the assignment
                    if student_id in self.course_ids_session[course_id]['assign_complete_ids']:
                        assignment_status = "Yes"
                    else: 
                        assignment_status = "No"
                    try:
                        # Add all needed data to the StudentCourseIntance table
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
                        self.session.rollback()
                        continue
                    except Exception as e:
                        logger.error(e, exc_info=True)
                        continue
        try: 
            self.session.add_all(order_entries)
            self.session.commit()
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
            self.session.rollback()
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
            pass
