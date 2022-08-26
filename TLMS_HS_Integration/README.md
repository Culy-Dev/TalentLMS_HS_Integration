# TLMS_HS_Integration Overview

The folder TLMS_HS_Integration contains a list of modules that work together to bring in data from Talent LMS into a SQLite database and then in turn released into Hubspot.

A crontab is set up to run the program every hour everyday. Student and Class data is grabbed from TalentLMS. Then, depending on certain criteria, the information is transformed to 
the appropriate structure in order to be migrated over to Hubspot.

## Crontab Explanation

To check which cronjobs are set up, enter the following command <br />
<pre>
sudo crontab -l 
</pre>

The following information should show up:
<pre>
*/60 * * * * /home/ubuntu/TalentLMS_HS_Integration/venv/bin/python /home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/task.py > /home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/temp/hour.log 2>&1
</pre>
The above means:  
  *  ```*/60 * * * * ```: Runs every 60 minutes.
  *  ```/home/ubuntu/TalentLMS_HS_Integration/venv/bin/python```: From the virtual environment, use python
  *  ```/home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/task.py```: to run the ```task.py``` module
  *  ```> /home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/temp/hour.log 2>&1```: Write the console output onto the ```hour.log``` file in the ```/temp/``` folder.

## Stopping the Cronjob
Do the following in order to stop the cronjob.
1. Enter ```sudo crontab -e``` in the command line. This will enter you the crontab jobs file in which is currently set up to be edited by the vim.
2. Type to ```i``` to insert.
3. Get to the line with the cronjob and add ```#``` in order to comment out the crontab.
<pre>
# */60 * * * * /home/ubuntu/TalentLMS_HS_Integration/venv/bin/python /home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/task.py > /home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/temp/hour.log 2>&1
</pre>
4. Save your edits to the vim file by typing hitting the ```ESC``` button and then typing ```:wq```
** If you need to exit the vim without saving, hit the ```ESC``` button and then typing ```:q!```

## Logs 
All log will be stored in papertrail. Each log starts the same: the timestamp is followed by the log level. A standard process log or a warning will then continue 
on with the specific information about the line code which triggered the log, followed by the log message. 

The following is an example of a success code:
<pre>
2022-08-16 18:07:46 | INFO
    [HourlyUpdate.hubapi:310] Working on batch request 29/135...
2022-08-16 18:07:46 | DEBUG
    [HourlyUpdate.hubapi: 38] "METHOD": "POST", "STATUS_CODE": "201","URL": "https://api.hubapi.com/crm/v3/associations/courses/2-7353817/batch/create"
NoneType: None
</pre>
The error message will look like this: 
<pre>
2022-08-10 12:58:18 | ERROR
{
"loggername" : "HourlyUpdate.hubapi",
"filename": "hubapi.py",
"funcName": "api_log",
"lineno": "43",
"module": "hubapi",
"pathname": "/home/frank-quoc/TalentLMS_HS_Integration/TLMS_HS_Integration/hubapi.py,"
"message": {"METHOD": "POST", "STATUS_CODE": "400","URL": "https://api.hubapi.com/crm/v3/objects/contacts","FAIL RESPONSE": "{"status":"error","message":"Property values were not valid: [{\"isValid\":false,\"message\":\"Email address example.lcom is invalid\",\"error\":\"INVALID_EMAIL\",\"name\":\"email\"}]","correlationId":"c8617a85-58a6-4a95-b619-e7d3594c170c","category":"VALIDATION_ERROR"}","PAYLOAD": {'properties': {'talentlms_user_id': 935, 'firstname': 'Example', 'lastname': 'Example', 'login': 'example.lcom ', 'email': 'example.lcom ', 'most_recent_linkedin_badge': None}}}
}
</pre>

## .env
The ```.gitignore``` file has been set to ignore ```.env``` files. So please add your API keys and password in a ```.env``` file should you need to redownload the file 
somewhere else.

## Manual Run
If for some reason you need to manually run the file, cancel the cronjob as given by the steps above and then enter the following in the command line:
<pre>
python3 /home/ubuntu/TalentLMS_HS_Integration/TLMS_HS_Integration/task.py
</pre>

Make sure you turn the cronjob back on once you made the appropriate edits to the program by following the same steps of stopping the cronjob, but delete the ```#```
instead.
