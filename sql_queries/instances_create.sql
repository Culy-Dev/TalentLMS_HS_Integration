SELECT 
    student_course_instance.instance_name AS instance_name,
    student_course_instance.talentlms_user_id AS talentlms_user_id, 
    student_course_instance.talentlms_course_id AS talentlms_course_id,
    student_course_instance.firstname AS firstname, 
    student_course_instance.lastname AS lastname, 
    student_course_instance.course_name AS course_name, 
    student_course_instance.code AS code, 
    student_course_instance.company_cohort_id AS company_cohort_id,
    student_course_instance.completed_on AS completed_on, 
    student_course_instance.completion_status AS completion_status, 
    student_course_instance.completion_percent AS completion_percent, 
    student_course_instance.email AS email,
    student_course_instance.live_session_datetime AS live_session_datetime,
    student_course_instance.role AS role,
    student_course_instance.session_time AS session_time,
    student_course_instance.status AS status,
    student_course_instance.total_time AS total_time,
    student_course_instance.total_time_seconds AS total_time_seconds,
    student_course_instance.last_accessed_unit_url AS last_accessed_unit_url,
    student_course_instance.linkedin_badge AS linkedin_badge,
    student_course_instance.assignment_complete AS assignment_complete
FROM student_course_instance 
LEFT JOIN instance_history 
ON student_course_instance.talentlms_user_id = instance_history.talentlms_user_id 
    AND student_course_instance.talentlms_course_id = instance_history.talentlms_course_id 
WHERE instance_history.hs_instance_id IS NULL;
