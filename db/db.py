import psycopg2
from config import DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST
from utils.parse_message import extract_user_info
import pytz
import datetime
from prometheus_client import Counter
import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()
DB_URL = os.getenv("NEON_DB_URL")

total_db_operations = Counter('total_db_operations', 'Count of total database ops occured')

def connect_to_database():
    """Central database connection function that tries both connection methods"""
    try:
        # Try Neon DB first
        if DB_URL:
            conn = psycopg2.connect(DB_URL)
            print("✅ Connected to Neon DB successfully.")
            return conn
    except Exception as e:
        print(f"Failed to connect to Neon DB: {e}")
    
    try:
        # Fallback to traditional connection
        conn = psycopg2.connect(
            dbname=DATABASE_NAME,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=5432
        )
        print("Connection to the database was successful")
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None

# Participation logs related functions
def save_log(message, discord_user_id, discord_message_id, sent_at, in_text_valid=-1):
    try:
        conn = connect_to_database()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO participation_logs (
                message, discord_user_id, discord_message_id, sent_at, in_text_valid
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (message, discord_user_id, discord_message_id, sent_at, in_text_valid)
        )
        conn.commit()
        total_db_operations.inc()
    except psycopg2.Error as e:
        print(f"Error occurred while saving log: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def update_log(discord_message_id, message, in_text_valid, updated_at):
    try:
        conn = connect_to_database()
        cur = conn.cursor()
        cur.execute("""
            UPDATE participation_logs
            SET message = %s, in_text_valid = %s, updated_at = %s
            WHERE discord_message_id = %s
        """, (message, in_text_valid, updated_at, discord_message_id))
        conn.commit()
        total_db_operations.inc()
        if cur.rowcount == 0:
            conn.rollback()
            print(f"No log found for message ID: {discord_message_id}")
            return False
        else:
            return True
    except Exception as e:
        print(f"Error updating log: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def delete_log(discord_message_id):
    try:
        conn = connect_to_database()
        cur = conn.cursor()
        ist_time = get_ist_time()
        cur.execute(
            """
            UPDATE participation_logs
            SET deleted_at = %s
            WHERE discord_message_id = %s
            """,
            (ist_time, discord_message_id),
        )
        conn.commit()
        print(f"Log marked as deleted for message ID: {discord_message_id}")
        total_db_operations.inc()
    except Exception as e:
        print(f"Error updating log: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# CP logs related functions
def save_cp_log(student_id, name, questions, leetcode_submissions, codeforces_submissions, day):
    """Save CP log to database"""
    conn = connect_to_database()
    if not conn:
        return

    solved = []
    for idx, q in enumerate(questions):
        if q.startswith("LC"):
            question_id = q[3:]
            if check_lc(question_id, leetcode_submissions):
                solved.append(idx)
        elif q.startswith("CF"):
            question_id = q[3:]
            if check_cf(question_id, codeforces_submissions):
                solved.append(idx)

    with conn.cursor() as cur:
        # Make sure user exists
        cur.execute('SELECT * FROM "cpLogs" WHERE "studentId" = %s;', (student_id,))
        if cur.fetchone() is None:
            cur.execute(
                'INSERT INTO "cpLogs" ("studentId", "Name", "Question 1", "Question 2", "Question 3", "Total Solved") VALUES (%s, %s, %s, %s, %s, %s);',
                (student_id, name, [], [], [], 0)
            )
            conn.commit()

        # Update solved questions
        for idx in solved:
            field = f"Question {idx + 1}"
            cur.execute(f'''
                UPDATE "cpLogs"
                SET "{field}" = array_append("{field}", %s),
                    "Total Solved" = "Total Solved" + 1
                WHERE "studentId" = %s AND NOT (%s = ANY("{field}"));
            ''', (day, student_id, day))

        conn.commit()
        print("✅ Updated CP log successfully.")

def delete_cp_log(student_id, day):
    """Delete CP log from database"""
    conn = connect_to_database()
    if conn is None:
        return

    with conn.cursor() as cur:
        fields = ["Question 1", "Question 2", "Question 3"]
        count_removed = 0

        for field in fields:
            cur.execute(f"""
                SELECT "{field}" FROM "cpLogs" WHERE "studentId" = %s;
            """, (student_id,))
            result = cur.fetchone()

            if result and day in result[0]:
                cur.execute(f"""
                    UPDATE "cpLogs"
                    SET "{field}" = array_remove("{field}", %s),
                        "Total Solved" = "Total Solved" - 1
                    WHERE "studentId" = %s;
                """, (day, student_id))
                count_removed += 1

        conn.commit()
        print(f"✅ Deleted '{day}' from {count_removed} field(s) for student '{student_id}'.")

# Utility functions
def get_ist_time():
    utc_now = datetime.datetime.now()
    ist = pytz.timezone('Asia/Kolkata')
    ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(ist)
    return ist_now

def check_intext_validity(message):
    conn = connect_to_database()
    cur = conn.cursor()
    try: 
        college_id = extract_user_info(message)
        if college_id:
            cur.execute("SELECT name FROM student_list_2023 WHERE student_id = %s", (college_id.upper(),))
            full_name = cur.fetchone()
            total_db_operations.inc()
            if full_name:
                first_name = full_name[0].split()[0]
                if first_name.lower() in message.lower():
                    return 1
                elif full_name[0].lower() in message.lower():
                    return 1
            else:
                print(f"No name found for student_id: {college_id}")
        return 0  
    except Exception as e:
        print(f"Error while checking intext validity: {e}")
        return -1
    finally:
        cur.close() 
        conn.close()

if __name__ == "__main__":
    print(check_intext_validity(""))
