from calendar import timegm
from dateutil.parser import parse
from datetime import datetime,timezone
import pytz
from sqlalchemy import exc, text

import logging
from models import Contacts, ContactHSHistory, CourseHSHistory, InstanceHistory, TimeTracking
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(f'HourlyUpdate.{__name__}')

def validate_unix(time_str):
    """
    The validate_unix is a helper function for the return_unix_time function takes a time string and checks if the string is in valid unix time (milliseconds)
    :param time_str: a string that is supposed to represent a time string
    :return: True if it's a valid unix time and False if not
    """
    if time_str.isdigit():
        # Gets the current time in unix time milliseconds
        curr_unix_time = timegm(datetime.utcnow().utctimetuple()) * 1000
        # Check if our time string is between 0 and the current unit time
        if 0 <= int(time_str) <= curr_unix_time:
            return True
    return False

def to_millisec(datetime_str):
    """
    The to_millisec is a helper function for the return_unix_time function takes a datetime string and changes the time to unix time
    :param datetime_str: a string to be changed to unix time
    :return: the correlating datetime in unix time (milliseconds) 
    """
    return timegm(parse(datetime_str, fuzzy=True).timetuple()) * 1000

def convert_dt_to_utc(dt_str, zonename='US/Eastern'):
    # Check if the current time is a datetime
    tz = pytz.timezone(zonename)
    dt_obj_unaware = parse(dt_str, fuzzy=True)
    print(dt_obj_unaware)
    dt_obj_aware = tz.localize(dt_obj_unaware)
    utc_time = dt_obj_aware.astimezone(pytz.utc).timetuple()
    unix_epoch_time = timegm(utc_time * 1000)
    session_time = dt_obj_aware.strftime("%H:%M:%S %Z")
    return unix_epoch_time, session_time

def return_unix_time(time_str):
    """
    The return_unix_time function takes the time string and checks the value of the string and return the appropriate value depending on the input
    :param time_str: the datetime string to validate
    :return: an empty string if there's no value, the same time string if it's already in unix time, or changing the time string to unix time
    """
    # If there's no value
    if time_str is None or '':
        return None
    # If the value is already in unix time (millisec)
    elif validate_unix(time_str) is True:
        return int(time_str) * 1000
    # If the date time needs to be changed to unix time
    else:
        return to_millisec(time_str)

def create_obj_payload(outer_join_file, engine):
    try:
        with engine.connect() as con:
            with open(outer_join_file) as file:
                query = text(file.read())
                
                results = con.execute(query)
                return {'inputs': [{'properties': dict(result)} for result in results]}
        con.close()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
    except Exception as e:
        logger.error(e, exc_info=True)
    

def update_obj_payload(inner_join_file, obj, engine):
    payload = {'inputs': []}
    try:
        with engine.connect() as con:
            with open(inner_join_file) as file:
                query = text(file.read())
                
                results = con.execute(query)
                for result in results:
                    record = dict(result)
                    if obj == 'contacts':
                        payload['inputs'].append({'id': record.pop('hs_contact_id'), 'properties': record})
                    elif obj == 'courses':
                        payload['inputs'].append({'id': record.pop('hs_course_id'), 'properties': record})
                    elif obj == '2-7353817':
                        payload['inputs'].append({'id': record.pop('hs_instance_id'), 'properties': record})
                return payload   
        con.close()
    except SQLAlchemyError as s:
        logger.error(s)
    except Exception as e:
        logger.error(e, exc_info=True)

def create_assoc_payload(assoc_join_file, assoc_type, engine):
    try:
        with engine.connect() as con:
            with open(assoc_join_file) as file:
                query = text(file.read())
                results = con.execute(query)
                return {'inputs': [{
                                    "from": {
                                        "id": str(result[0])
                                    },
                                    "to": {
                                        "id": str(result[1])
                                    },
                                    "type": assoc_type
                                    } for result in results]}
        con.close()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
    except Exception as e:
        logger.error(e, exc_info=True)
   

def gather_batch_hs_id(objectType, res, session):
    for r in res.json()['results']:
        if objectType == 'contacts':
            try:
                session.add(ContactHSHistory(hs_contact_id=r['id'], talentlms_user_id=r['properties']\
                    ['talentlms_user_id']))
            except SQLAlchemyError as s:
                logger.error(s, exc_info=True)
                continue
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
        elif objectType == 'courses':
            try:
                session.add(CourseHSHistory(hs_course_id=r['id'], talentlms_course_id=r['properties']\
                    ['talentlms_course_id']))
            except SQLAlchemyError as s:
                logger.error(s, exc_info=True)
                continue
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
        elif objectType == '2-7353817':
            try:
                session.add(InstanceHistory(hs_instance_id=r['id'], talentlms_user_id=r['properties']\
                    ['talentlms_user_id'], talentlms_course_id=r['properties']['talentlms_course_id']))
            except SQLAlchemyError as s:
                logger.error(s, exc_info=True)
                continue
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
    session.commit()

def gather_unit_hs_id(objectType, res, session):
    r = res.json()
    if objectType == 'contacts':
        try:
            session.add(ContactHSHistory(hs_contact_id=r['id'], talentlms_user_id=r['properties']\
                ['talentlms_user_id']))
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
    elif objectType == 'courses':
        try:
            session.add(CourseHSHistory(hs_course_id=r['id'], talentlms_course_id=r['properties']\
                ['talentlms_course_id']))
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
    elif objectType == '2-7353817': # this potentially needs to be the id given when creating the custom object
        try:
            session.add(InstanceHistory(hs_instance_id=r['id'], talentlms_user_id=r['properties']\
                ['talentlms_user_id'], talentlms_course_id=r['properties']['talentlms_course_id']))
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
        except Exception as e:
            logger.error(e, exc_info=True)
    session.commit()

def update_time_tracking(time_str, session):
    try:
        session.query(TimeTracking).update({'last_modified_time': return_unix_time(time_str)})
        session.commit()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
    except Exception as e:
        logger.error(e, exc_info=True)


