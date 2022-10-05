from sqlalchemy import create_engine, MetaData, ForeignKey, Column, Date, Integer, Text, PrimaryKeyConstraint, CheckConstraint 
from sqlalchemy.orm import relationship, backref, sessionmaker, deferred
from sqlalchemy.ext.declarative import declarative_base
import json
import time
import os

 
# If echo is True, the Engine will log all statements as well as a repr() of their parameter lists to the default 
# log handler, which defaults to sys.stdout for output. If set to the string "debug", result rows will be 
# printed to the standard output as well. The echo attribute of Engine can be modified at any time to turn 
#logging on and off; direct control of logging is also available using the standard Python logging module.
# Engine is the homebase for the actual db. Program that performs a core or essential function for

# Get the direct path to database
package_dir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(package_dir, 'company_name.db')
# NEED 4 /'s to specify absolute for sqlalchemy!
# ex: sqlite:////asdfaijegoij/aerga.db
# NEED 3 /'s for relative paths
# path has a / at the beginning so we have 3 here

# Create the database
SQLITE_DB = ''.join(['sqlite:///', db_dir])


engine = create_engine(SQLITE_DB) 

# imports the declarative_base object, which connects the database engine to the SQLAlchemy functionality of 
# metadata = MetaData()
Base = declarative_base()
# Session = sessionmaker(bind=engine)
# session = Session()

class Contacts(Base):
    """Model to represent the students and all data associated with them"""

    __tablename__ = "contacts"

    talentlms_user_id  = Column(Integer, primary_key=True, sqlite_on_conflict_primary_key='REPLACE')
    firstname = Column(Text)
    lastname = Column(Text)
    login = Column(Text) 
    email = Column(Text)
    most_recent_linkedin_badge = Column(Text)
    hs_content_membership_status = Column(Text)

    # Relationships
    student_course_instances = relationship("StudentCourseInstance", backref=backref("contacts"))
    contact_hs_histories = relationship("ContactHSHistory", backref=backref("contact_hs_history"), uselist=False)


class Courses(Base):
    """Model to represent the courses and all data associated with them"""

    __tablename__ = "courses"

    talentlms_course_id = Column(Integer, primary_key=True, sqlite_on_conflict_primary_key='REPLACE')
    course_name = Column(Text)
    code = Column(Text)
    description = Column(Text)
    end_date = Column(Integer) 
    live_session_datetime = Column(Integer) 
    session_time = Column(Text)
    start_date = Column(Integer) 
    assignment_due_date = Column(Integer) 
    cohort_id = Column(Text)
    course_template_code = Column(Text)
    course_template_name = Column(Text)
    trigger_datetime = Column(Integer) 
    

    # Relationships
    student_course_instances = relationship("StudentCourseInstance", backref=backref("courses"))
    course_hs_histories = relationship("CourseHSHistory", backref=backref("course_hs_history"), uselist=False)


class StudentCourseInstance(Base):
    """Model to represent the an instance of a student taking a particular course."""

    __tablename__ = "student_course_instance"

    talentlms_user_id = Column(Integer, ForeignKey('contacts.talentlms_user_id'), primary_key=True, sqlite_on_conflict_primary_key='REPLACE') 
    talentlms_course_id = Column(Integer, ForeignKey('courses.talentlms_course_id'), primary_key=True, sqlite_on_conflict_primary_key='REPLACE')
    instance_name = Column(Text)
    firstname = Column(Text)
    lastname = Column(Text)
    course_name = Column(Text)
    code = Column(Text)
    company_cohort_id = Column(Text)
    completed_on = Column(Integer) 
    completion_status = Column(Text)
    completion_percent = Column(Integer) 
    email = Column(Text)
    live_session_datetime = Column(Integer) 
    role = Column(Text)
    session_time = Column(Text)
    status = Column(Text)
    total_time = Column(Text)
    total_time_seconds = Column(Integer) 
    last_accessed_unit_url = Column(Text)
    linkedin_badge = Column(Text)
    assignment_complete = Column(Text)
    __table_args__ = (PrimaryKeyConstraint(talentlms_user_id, talentlms_course_id, sqlite_on_conflict='REPLACE', name='user_course_compound_id'),)
    # Relationships
    # student_course_instance_histories = relationship("StudentCourseInstanceHistory", backref=backref("student_course_instance"))


class ContactHSHistory(Base):
    """Historical data to never be deleted of unique ids from TalentLMS and Hubspot contact ids"""
    
    __tablename__ = "contact_hs_history"

    talentlms_user_id = Column(Integer, ForeignKey('contacts.talentlms_user_id'), primary_key=True, sqlite_on_conflict_primary_key='REPLACE') 
    hs_contact_id = Column(Integer, unique=True)


class CourseHSHistory(Base):
    """Historical data to never be deleted of unique ids from TalentLMS and Hubspot course ids"""
    
    __tablename__ = "course_hs_history"

    talentlms_course_id = Column(Integer, ForeignKey('courses.talentlms_course_id'), primary_key=True, sqlite_on_conflict_primary_key='REPLACE') 
    hs_course_id = Column(Integer, unique=True)


class InstanceHistory(Base):
    """
    Historical data to never be deleted of unique ids from TalentLMS contact and course ids
    along with Hubspot student/course instance ids
    """
    
    __tablename__ = "instance_history"

    talentlms_user_id = Column(Integer, ForeignKey('instance_history.talentlms_user_id')) 
    talentlms_course_id = Column(Integer, ForeignKey('instance_history.talentlms_course_id')) 
    hs_instance_id = Column(Integer, unique=True)
    __table_args__ = (PrimaryKeyConstraint(talentlms_user_id, talentlms_course_id, sqlite_on_conflict='REPLACE', name='user_course_compound_id'),)


class TimeTracking(Base):
    """Model to store the most recent time the integration has run"""
    
    __tablename__ = 'time_tracking'

    last_modified_time = Column(Integer, primary_key=True)

# Add all the Tables/Models to the database
Base.metadata.create_all(engine)

engine.dispose()