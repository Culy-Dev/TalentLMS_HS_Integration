"""Main module to run TalentLMS to Hubspot Integration"""
from datetime import datetime

from talentlmsapi import TalentLMS
from hubapi import CreateRecordsHandler, UpdateRecordsHandler, CreateAssociationsHandler
from transform import create_obj_payload, update_obj_payload, create_assoc_payload, update_time_tracking, gather_batch_hs_id, gather_unit_hs_id
from logger import get_logger
from models import Courses, Contacts, StudentCourseInstance, SQLITE_DB 
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session

import os
# "2-8311841" Test for courses
# 2-8311962  Test for student_class_instance

# 2-8311841 is the internal ID of courses object on HS
# 2-8311962 is the internal ID of the student_course_instance object on HS

project_root = os.path.dirname(os.path.dirname(__file__))
output_path = os.path.join(project_root, 'TLMS_HS_Integration/sql_queries')   

class HourlyUpdate:

    def __init__(self, isodatetime=datetime.utcnow().isoformat()):
        # Create an engine and session to SQLAlchemy to start the program
        self.engine, self.session = self.get_session()
        try:
            # Delete any information in the Contacts, Courses, and StudentCourseInstance from the last run
            # This is done to only bring in newly created or updated information from TalentLMS
            self.session.query(Contacts).delete()
            self.session.query(Courses).delete()
            self.session.query(StudentCourseInstance).delete()
            self.session.commit()
        except SQLAlchemyError as s:
            self.logger.error(s)
            self.session.rollback()
            pass
        except Exception as e:
            self.logger.error(e, exc_info=True)
            pass
        self.isodatetime = isodatetime # set the current time
        self.logger = get_logger('HourlyUpdate') # Instantiate the logger

    def run(self):
        """Main function to run the program"""
        self.logger.info(f'--- BEGIN HOURLY UPDATE ({self.isodatetime}) ---\n')

        self._migrate_from_talentlms()
        self._contacts_to_hs()
        self._courses_to_hs()
        self._instances_to_hs()
        self._create_assoc()
        # After the program is done running, update the TimeTrack table to the start time that this program has run
        update_time_tracking(self.isodatetime, self.session)
        # CLose the session and engine
        self.session.close()
        self.engine.dispose()

        self.logger.info(f'--- END HOURLY UPDATE ({self.isodatetime}) ---')

    def get_session(self):
        """Creates a new database self.session for instant use"""

        engine = create_engine(SQLITE_DB)
        Session = sessionmaker(bind = engine)
        session = scoped_session(Session)
        return (engine, session)
        
        # GET ALL SESSIONS AND CLOSE DATABASE

    def _migrate_from_talentlms(self):
        """Migrates all data from TalentLMS to a SQLite database"""

        self.logger.info('-- START TALENTLMS ROUTINE --\n')

        self.logger.info('Retrieving data from TalentLMS...')
        # Instantiate the information needed to do API calls to TalentLMS
        get_from_talentlms = TalentLMS(self.isodatetime, self.engine, self.session)
        # Lets you know the amount of information gathered from TalentLMS
        self.logger.info(f'... Obtained {len(get_from_talentlms.all_courses.json()) if get_from_talentlms.all_courses is not None else "no"} courses from TalentLMS')
        self.logger.info(f'... Obtained {len(get_from_talentlms.all_students.json()) if get_from_talentlms is not None else "no"} contacts from TalentLMS\n')

        self.logger.info('Moving Courses to SQLite database...')
        # Move course information to SQLITE database
        get_from_talentlms.move_courses_to_sqlite()
        try:
            # Give the amount of records moved to the Courses table
            num_course_rows = self.session.query(Courses).count()
            self.logger.info(f'...Migrated {num_course_rows} courses to the SQLite database\n')
        except SQLAlchemyError as s:
            self.logger.error(s, exc_info=True)
            pass
        except Exception as e:
            self.logger.error(e, exc_info=True)
            pass

        self.logger.info('Moving Users to SQLite database...')
        # Move contact information to SQLite database
        get_from_talentlms.move_users_to_sqlite()
        try:
            # Give the amount of records move to the Contacts table
            num_contacts_rows = self.session.query(Contacts).count()
            self.logger.info(f'...Migrated {num_contacts_rows} contacts to the SQLite database\n')
        except SQLAlchemyError as s:
            self.logger.error(s, exc_info=True)
            pass
        except Exception as e:
            self.logger.error(e, exc_info=True)
            pass
        # Move information to the Student Class Instance
        self.logger.info('Moving Student Class Instances to SQLite database...')
        get_from_talentlms.move_instances_to_sqlite()
        try:
            # Give the amount of records moved to the Instance table
            num_instances_rows = self.session.query(StudentCourseInstance).count()
            self.logger.info(f'...Migrated {num_instances_rows} instances to the SQLite database\n')
        except SQLAlchemyError as s:
            self.logger.error(s, exc_info=True)
            pass
        except Exception as e:
            self.logger.error(e, exc_info=True)
            pass
        self.logger.info('-- END TALENTLMS ROUTINE --\n')

    def _contacts_to_hs(self):
        """Moves infromation from the Constants Table to Hubspot"""

        self.logger.info('-- START HUBSPOT CONTACTS ROUTINE --\n')

        self.logger.info('Creating contacts on Hubspot...')
        # Instantiates a Contacts Recrd to be created
        create_contact = CreateRecordsHandler('contacts', self.session)
        # Creates the contact creation payload
        create_contact_payload = create_obj_payload(os.path.join(output_path, 'contacts_create.sql'), self.engine)
        # Create on Hubspot
        create_contact.dispatch(create_contact_payload)
        self.logger.info('...Finished creating contacts.\n')

        self.logger.info('Updating contacts on Hubspot...')
        # Instantiates a Contacts Recrd to be uploaded
        update_contact = UpdateRecordsHandler('contacts')
        # Creates the contact upload payload
        update_contact_payload = update_obj_payload(os.path.join(output_path, 'contacts_update.sql'), 'contacts', \
            self.engine)
        # Upload to Hubspot
        update_contact.dispatch(update_contact_payload)
        self.logger.info('...Finished updating contacts.\n')

        self.logger.info('-- END HUBSPOT CONTACTS ROUTINE --\n')

    def _courses_to_hs(self):
        """Moves information from the Courses Table to Hubspot"""

        self.logger.info('-- START HUBSPOT COURSES ROUTINE --\n')

        self.logger.info('Creating courses on Hubspot...')
        # Instantiates a Coourses Recrd to be created
        create_course = CreateRecordsHandler('2-8311841', self.session)
        create_course_payload = create_obj_payload(os.path.join(output_path, 'courses_create.sql'), self.engine)
        create_course.dispatch(create_course_payload)
        self.logger.info('...Finished creating courses.\n')

        self.logger.info('Updating course on Hubspot...')
        update_course = UpdateRecordsHandler('2-8311841')
        update_course_payload = update_obj_payload(os.path.join(output_path, 'courses_update.sql'),  '2-8311841', \
            self.engine)
        update_course.dispatch(update_course_payload)
        self.logger.info('...Finished updating courses.\n')

        self.logger.info('-- END HUBSPOT COURSES ROUTINE --\n')

    def _instances_to_hs(self):
        """Moves infromation from the Instance Table to Hubspot"""

        self.logger.info('-- START HUBSPOT INSTANCES ROUTINE --')

        self.logger.info('Creating instances on Hubspot...')
        create_instance = CreateRecordsHandler('2-8311962', self.session)
        create_instance_payload = create_obj_payload(os.path.join(output_path, 'instances_create.sql'), self.engine)
        create_instance.dispatch(create_instance_payload)
        self.logger.info('...Finished creating instances.\n')

        self.logger.info('Updating instances on Hubspot...')
        update_instance = UpdateRecordsHandler('2-8311962')
        update_instance_payload = update_obj_payload(os.path.join(output_path, 'instances_update.sql'),  '2-8311962', \
            self.engine)
        update_instance.dispatch(update_instance_payload)
        self.logger.info('...Finished updating instances.\n')

        self.logger.info('-- END HUBSPOT INSTANCES  ROUTINE --\n')

    def _create_assoc(self):
        """
        Creates Hubspot Associations between the contacts and student_course_instance records
        Creates Hubspot Associations between the courses and student_course_instance records
        """

        self.logger.info('-- START HUBSPOT ASSOCIATIONS ROUTINE --')

        self.logger.info('Associating Contacts to Instances on Hubspot...')
        # Instantiates an Associations Object for contacts and student_class_instance
        contact_instance_assoc = CreateAssociationsHandler('contact','2-8311962')
        # Create the association payload for contacts and student_class_instance
        contact_instance_payload = create_assoc_payload(os.path.join(output_path, 'assoc_contact_instance.sql'),  \
            'student_class_instance_to_contact', self.engine)
        # Create the association on Hubspot
        contact_instance_assoc.dispatch(contact_instance_payload)
        self.logger.info('...Finished associating Contacts to Instances.\n')

        self.logger.info('Associating Courses to Instances on Hubspot...')
        # Instantiates an Associations Object for courses and student_class_instance
        course_instance_assoc = CreateAssociationsHandler('2-8311841', '2-8311962')
        # Create the association payload for courses and student_class_instance
        course_instance_payload = create_assoc_payload(os.path.join(output_path, 'assoc_courses_instance.sql'),  \
            'course_to_student_class_instance', self.engine)
        # Create the association on Hubspot
        course_instance_assoc.dispatch(course_instance_payload)
        self.logger.info('...Finished associating Courses to Instances.\n')

        self.logger.info(f'-- END HUBSPOT ASSOCIATIONS  ROUTINE --{datetime.utcnow().isoformat()} \n')


if __name__ == '__main__':
    integration = HourlyUpdate()
    integration.run()
