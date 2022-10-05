SELECT 
    contacts.talentlms_user_id AS talentlms_user_id, 
    contacts.firstname AS firstname, 
    contacts.lastname AS lastname, 
    contacts.login AS login, 
    contacts.email AS email, 
    contacts.hs_content_membership_status AS hs_content_membership_status, 
    contacts.most_recent_linkedin_badge AS most_recent_linkedin_badge, 
    contact_hs_history.hs_contact_id AS hs_contact_id
FROM contacts JOIN contact_hs_history ON contacts.talentlms_user_id = contact_hs_history.talentlms_user_id;