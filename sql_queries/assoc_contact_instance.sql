SELECT 
    c.hs_contact_id AS hs_contact_id,
    i.hs_instance_id AS hs_instance_id
FROM 
    contact_hs_history c
JOIN
    instance_history i
ON
    i.talentlms_user_id = c.talentlms_user_id;

-- 1560, 128

-- UPDATE instance_history
-- SET talentlms_user_id = 1560,
-- talentlms_course_id = 128
-- WHERE 
--     hs_instance_id = 1870511175;