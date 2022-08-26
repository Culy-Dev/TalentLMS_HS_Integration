import logging
import pandas as pd
from pandas.tseries.offsets import BDay
from hubapi import get_all_records
from dateutil.parser import parse
from calendar import timegm
from datetime import datetime, date, timezone

logger = logging.getLogger(F'LinkedInAssignDueDateUpdate.{__name__}')

class DueDate:
    def __init__(self, objectType='2-7353817', curr_date=date.today()):
        self.records = self.get_all_records_with_property(objectType)
        self.curr_date = datetime.combine(curr_date, datetime.min.time())
        self.payload = {'inputs': []}
    
    def calc_assign_due_date(self):
        for row in self.records.itertuples(index=True, name="Pandas"):
            try:
                live_session_date = datetime.strptime(row[-1][:-10], "%Y-%m-%d")
                if self.curr_date < live_session_date: 
                    assignment_due_date = live_session_date - BDay(2)
                    assignment_due_date_unix = timegm(assignment_due_date.timetuple()) * 1000
                    self.payload['inputs'].append({'id': row.id, 'properties': {"assignment_due_date": assignment_due_date_unix}})
            except Exception as e:
                self.logger.error(e, exc_info=True)
                continue
    
    def get_all_records_with_property(self, objectType, property_name={'live_session_datetime', 'assignment_due_date'}):
        all_records = get_all_records(objectType, add_params={'properties': property_name})
        records_in_hs = pd.json_normalize(all_records)
        records_in_hs = records_in_hs[(records_in_hs['properties.live_session_datetime'].notnull()) & ((records_in_hs['properties.assignment_due_date'].isnull()) | (records_in_hs['properties.assignment_due_date']==''))]
        return records_in_hs