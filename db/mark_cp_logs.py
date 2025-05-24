from db.platforms.leetcode import get_leetcode_recent_submissions
from db.platforms.codeforces import get_codeforces_recent_submissions
from db.db import save_cp_log, delete_cp_log
from utils.parse_message import extract_user_info, extract_user_lc_cf_id, extract_day_number
import json
import os

# Load questions configuration
QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "questions.json")
with open(QUESTIONS_FILE, "r") as file:
    questions = json.load(file)

def check_lc(question_id, leetcode_submissions):
    """Check if a LeetCode question is solved"""
    for sub in leetcode_submissions:
        if str(sub.get("id")) == str(question_id):
            return True
    return False

def check_cf(question_id, codeforces_submissions):
    """Check if a CodeForces question is solved"""
    for sub in codeforces_submissions:
        if str(sub.get("id")) == str(question_id) and sub.get('verdict')=='OK':
            return True
    return False

def process_submissions(msg: str):
    """
    Process user submissions from a message.
    
    Args:
        msg (str): The message containing user information and submissions
        
    Returns:
        dict: Status of submission processing with details
    """
    # Extract information
    user_id, name = extract_user_info(msg)
    platform_ids = extract_user_lc_cf_id(msg)
    day = extract_day_number(msg)
    
    # Validate extracted data
    if not user_id:
        return {"error": "Could not extract user ID"}
    if not name:
        return {"error": "Could not extract user name"}
    if not platform_ids['lc'] or not platform_ids['cf']:
        return {"error": "Could not extract platform IDs"}
    if not day:
        return {"error": "Could not extract day number"}
    
    # Get questions for the day
    day_questions = questions.get(str(day))
    if not day_questions:
        return {"error": f"No questions found for day {day}"}
    
    # Get submissions
    lc_submissions = get_leetcode_recent_submissions(platform_ids['lc'])
    cf_submissions = get_codeforces_recent_submissions(platform_ids['cf'])
    
    # Validate submissions
    if isinstance(lc_submissions, dict) and 'error' in lc_submissions:
        return {"error": f"LeetCode error: {lc_submissions['message']}"}
    if isinstance(cf_submissions, dict) and 'error' in cf_submissions:
        return {"error": f"CodeForces error: {cf_submissions['message']}"}
    
    # Check submissions against questions
    solved = []
    for idx, q in enumerate(day_questions):
        if q.startswith("LC"):
            question_id = q[3:]
            if check_lc(question_id, lc_submissions):
                solved.append(idx)
        elif q.startswith("CF"):
            question_id = q[3:]
            if check_cf(question_id, cf_submissions):
                solved.append(idx)
    
    # Update database
    try:
        save_cp_log(user_id, day_questions, name, lc_submissions, cf_submissions, day)
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}
    
    return {
        "status": "success",
        "solved_questions": solved,
        "total_questions": len(day_questions),
        "day": day,
        "user_id": user_id,
        "name": name
    }

def cpLogs(studentId, usernameCF, usernameLC, realName, day):
    """
    Legacy function for backward compatibility.
    Use process_submissions() for new code.
    """
    leetcodeSubmission = get_leetcode_recent_submissions(usernameLC)
    codeforcesSubmission = get_codeforces_recent_submissions(usernameCF)
    questionOfDay = questions[str(day)]
    save_cp_log(studentId, questionOfDay, realName, leetcodeSubmission, codeforcesSubmission, day)
