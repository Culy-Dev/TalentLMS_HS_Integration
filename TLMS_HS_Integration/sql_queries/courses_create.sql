SELECT 
    courses.talentlms_course_id AS talentlms_course_id, 
    courses.course_name AS course_name, 
    courses.code AS code, 
    courses.start_date AS start_date, 
    courses.description AS description, 
    courses.end_date AS end_date, 
    courses.live_session_datetime AS live_session_datetime, 
    courses.session_time AS session_time, 
    courses.assignment_due_date AS assignment_due_date,
    courses.cohort_id AS cohort_id
FROM courses LEFT JOIN course_hs_history ON courses.talentlms_course_id = course_hs_history.talentlms_course_id 
WHERE course_hs_history.hs_course_id IS NULL;
