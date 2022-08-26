SELECT 
    c.hs_course_id AS hs_course_id,
    i.hs_instance_id AS hs_instance_id
FROM 
    course_hs_history c
JOIN
    instance_history i
ON
    i.talentlms_course_id = c.talentlms_course_id;
