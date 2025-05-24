import os
import psycopg2
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()
DB_URL = os.getenv("NEON_DB_URL")
def connect_db():
    print(DB_URL)
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ Connected to Neon DB successfully.")
        return conn
    except Exception as e:
        print("❌ Failed to connect:", e)
        return None
    


def check_lc(question_id, leetcode_submissions):
    for sub in leetcode_submissions:
        if str(sub.get("id")) == str(question_id):
            return True
    return False


def check_cf(question_id, codeforces_submissions):
    for sub in codeforces_submissions:
        if str(sub.get("id")) == str(question_id) and sub.get('verdict')=='OK':
            return True
    return False


def mark_db(studentId, questions, name, leetcode_submissions, codeforces_submissions, day):
    conn = connect_db()
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
        cur.execute('SELECT * FROM "student_list_2024" WHERE "stu_id" = %s;', (studentId,))
        if cur.fetchone() is None:
            cur.execute(
                'INSERT INTO "student_list_2024" ("stu_id", "name", "q1", "q2", "q3", "Total Solved") VALUES (%s, %s, %s, %s, %s, %s);',
                (studentId, name, [], [], [], 0)
            )
            conn.commit()

        # Update solved questions
        for idx in solved:
            field = f"Question {idx + 1}"
            cur.execute(f'''
                UPDATE "student_list_2024"
                SET "{field}" = array_append("{field}", %s),
                    "Total Solved" = "Total Solved" + 1
                WHERE "stu_id" = %s AND NOT (%s = ANY("{field}"));
            ''', (day, studentId, day))

        conn.commit()
        print("✅ Updated CP log successfully.")

def delete_db(studentId, day):
    conn = connect_db()
    if conn is None:
        return

    with conn.cursor() as cur:
        fields = ["q1", "q2", "q3"]
        count_removed = 0

        for field in fields:
            # Check if 'day' exists in the array for this field
            cur.execute(f"""
                SELECT "{field}" FROM "student_list_2024" WHERE "stu_id" = %s;
            """, (studentId,))
            result = cur.fetchone()

            if result and day in result[0]:  # check if 'day' is in the array
                # Remove it and decrement total solved
                cur.execute(f"""
                    UPDATE "student_list_2024"
                    SET "{field}" = array_remove("{field}", %s),
                        "Total Solved" = "Total Solved" - 1
                    WHERE "stu_id" = %s;
                """, (day, studentId))
                count_removed += 1

        conn.commit()
        print(f"✅ Deleted '{day}' from {count_removed} field(s) for student '{studentId}'.")

