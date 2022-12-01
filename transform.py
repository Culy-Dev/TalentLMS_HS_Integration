"""Module to transform TalentLMS data to what will be uploaded on Hubspot"""

from calendar import timegm
from dateutil.parser import parse
from datetime import datetime,timezone
import pytz
from sqlalchemy import exc, text

import logging
from models import Contacts, ContactHSHistory, CourseHSHistory, InstanceHistory, TimeTracking
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import re

# 2-8311841 is the internal ID of courses object on HS
# 2-8311962 is the internal ID of the student_course_instance object on HS

logger = logging.getLogger(f'CurrUpdate.{__name__}')

def validate_unix(time_str):
    """
    The validate_unix is a helper function for the return_unix_time function takes a time string and checks if the string is in valid unix time (milliseconds)
    :param time_str: a string that is supposed to represent a time string
    :return: True if it's a valid unix time and False if not
    """
    if time_str.isdigit():
        # Check if our time string is between 0 and the current unit time
        if 0 <= int(time_str):
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
    """
    Takes a datestring and changes it into unix epoch time and also grabs the time data as its own separate entitity
    :param dt_str: a string to represent a datetime string, zonename: the time zone
    :return: The unix epoch time and session time
    """
    # Set the timezone
    tz = pytz.timezone(zonename)
    # Grab the datetime from a string
    dt_obj_unaware = parse(dt_str, fuzzy=True)
    # Make the datetime object aware of the timezone
    dt_obj_aware = tz.localize(dt_obj_unaware)
    # Create a timetuple of the datetime in UTC time
    utc_time = dt_obj_aware.astimezone(pytz.utc).timetuple()
    # Convert to unix epoch time in milliseconds
    unix_epoch_time = timegm(utc_time) * 1000
    # Grab the time from the datetime string and add daylights savig and timezone information
    session_time = dt_obj_aware.strftime("%H:%M:%S %Z")
    return unix_epoch_time, session_time

def return_unix_time(time_str):
    """
    The return_unix_time function takes the time string and checks the value of the string and return the appropriate value depending on the input
    :param time_str: the datetime string to validate
    :return: an empty string if there's no value, the same time string if it's already in unix time, or changing the time string to unix time
    """
    # If there's no value
    if time_str is None or time_str == '':
        return None
    # If the value is already in unix time (millisec)
    elif validate_unix(time_str) is True:
        return int(time_str) * 1000
    # If the date time needs to be changed to unix time
    else:
        return to_millisec(time_str)

def create_obj_payload(outer_join_file, engine):
    """
    Uses an outer join to match up Historical Data with new data from their respective tables 
    in order to find any TalentLMS IDs without Hubspot Ids in the historical tables
    for a CREATE API payload

    Args:
        outer_join_file (str): a .sql filename for creates
        engine (class): Engine object to provide a source of database connectivity and behavior

    Returns:
        (dict): dict that will be convert to JSON data for Hubspot CREATE 
    """
    try:
        with engine.connect() as con:
            with open(outer_join_file) as file:
                query = text(file.read())
                
                results = con.execute(query)
                return  {'inputs': [{'properties': dict(result)} for result in results]}
        con.close()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
        pass
    except Exception as e:
        logger.error(e, exc_info=True)
        pass
    

def update_obj_payload(inner_join_file, obj, engine):
    """Uses an inner join to match up Historical Data with new data from their respective tables 
    in order to find Hubspot IDs associated with TalentLMS IDs in the historical tables
    for an UPDATE API payload

    Args:
        inner_join_file (str): .sql filename for updates
        obj (str): object name on Hubspot to update to
        engine (class): Engine object to provide a source of database connectivity and behavior

    Returns:
        (dict): dict that will be convert to JSON data for Hubspot UPDATE
    """
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
                    elif obj == '2-8311841':
                        payload['inputs'].append({'id': record.pop('hs_course_id'), 'properties': record})
                    elif obj == '2-8311962':
                        payload['inputs'].append({'id': record.pop('hs_instance_id'), 'properties': record})
                return payload   
        con.close()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
        pass
    except Exception as e:
        logger.error(e, exc_info=True)
        pass

def update_if_already_exists_payload(hs_id, payld):
    """
    Creates a payload for the CREATE API if there's an error of the TalentLMS ID record already
    existing under a Hubspot ID, and sends an UPDATE API call instead

    Args:
        hs_id: hubspot id of the record
        payld (dict): Grabs the payload meant to be used for CREATE and adds a Hubspot ID 
            for update

    Returns:
        (dict): dict that will be convert to JSON data for Hubspot UPDATE
    """
    payload = {'id': hs_id}
    payload.update(payld)
    return payload

def create_assoc_payload(assoc_join_file, assoc_type, engine):
    """
    Creates an association payload for either the Contact or Courses object to be associated 
    with the Student/Instance object

    Args:
        assoc_join_file (str): filename of a .sql that uses a JOIN on historical data to grab the
            ids of contact or courses and associated with an instance id
        assoc_type (str): shows the connection to be contact_to_instance or courses_to_instance
        engine (class): Engine object to provide a source of database connectivity and behavior

    Returns:
        (dict): dict that will be convert to JSON data for Hubspot CREATE for associations
    """
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
        pass
    except Exception as e:
        logger.error(e, exc_info=True)
        pass
   

def gather_batch_hs_id(objectType, res, session):
    """
    Gathers the Hubspot IDS generated with doing a CREATE API call and storing it with a 
    TalentLMS ID as a single record

    Args:
        objectType (str): Hubspot object to be used to specify which table to put the historical
            data in
        res (class): JSON response to find the ids
        session (class):  scoped_session object, and it represents a registry of  Session
            objects: which manages persistence operations for ORM-mapped objects.
    """
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
        elif objectType == '2-8311841':
            try:
                session.add(CourseHSHistory(hs_course_id=r['id'], talentlms_course_id=r['properties']\
                    ['talentlms_course_id']))
            except SQLAlchemyError as s:
                logger.error(s, exc_info=True)
                continue
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
        elif objectType == '2-8311962':
            try:
                session.add(InstanceHistory(hs_instance_id=r['id'], talentlms_user_id=r['properties']\
                    ['talentlms_user_id'], talentlms_course_id=r['properties']['talentlms_course_id']))
            except SQLAlchemyError as s:
                logger.error(s, exc_info=True)
                session.rollback()
                continue
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
    try: 
        session.commit()
    except IntegrityError as i:
        logger.error(i, exc_info=True)
        session.rollback()
        pass
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
        session.rollback()
        pass
    except Exception as e:
        logger.error(e, exc_info=True)
        pass

def gather_unit_hs_id(objectType, res, session):
    """
    Helper function to gather the created Hubspot Ids and match it up with to the TalentLMS Ids
    This information is kept as historical data to be added to the 
    ContactHSHistory, CourseHSHistory, and Instance History tables.

    Args:
        objectType (str): Hubspot object to be used to specify which table to put the historical
            data in
        res (class): JSON response to find the ids
        session (class): scoped_session object, and it represents a registry of  Session
            objects: which manages persistence operations for ORM-mapped objects.
    """
    r = res.json()
    if objectType == 'contacts':
        try:
            session.add(ContactHSHistory(hs_contact_id=r['id'], talentlms_user_id=r['properties']\
                ['talentlms_user_id']))
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
            session.rollback()
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
    elif objectType == '2-8311841':
        try:
            session.add(CourseHSHistory(hs_course_id=r['id'], talentlms_course_id=r['properties']\
                ['talentlms_course_id']))
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
            session.rollback()
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
            pass
    elif objectType == '2-8311962': 
        try:
            session.add(InstanceHistory(hs_instance_id=r['id'], talentlms_user_id=r['properties']\
                ['talentlms_user_id'], talentlms_course_id=r['properties']['talentlms_course_id']))
        except SQLAlchemyError as s:
            logger.error(s, exc_info=True)
            session.rollback()
            pass
        except Exception as e:
            logger.error(e, exc_info=True)
            pass
    try: 
        session.commit()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
        session.rollback()
        pass
    except Exception as e:
        logger.error(e, exc_info=True)
        pass

def update_time_tracking(time_str, session):
    """Updates the last_modified_time recored to the start time of the program running.

    Args:
        time_str (str): datetime str of the current integration run
        session (class):  scoped_session object, and it represents a registry of Session objects: 
            which manages persistence operations for ORM-mapped objects.
    """
    try:
        session.query(TimeTracking).update({'last_modified_time': return_unix_time(time_str)})
        session.commit()
    except SQLAlchemyError as s:
        logger.error(s, exc_info=True)
        session.rollback()
        pass
    except Exception as e:
        logger.error(e, exc_info=True)
        pass

def remove_string(string):
    """Takes the course template name and remove (Template) and not case sensitive

    Args:
        string (str): the course template name with (Template)

    Returns:
        (str): course_template_name without (Template)
    """
    pattern = re.compile(r" \(TEMPLATE\)", re.I)
    return pattern.sub("", string)
