import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            buffered=True
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def execute_query(query, params=None, fetch=False, fetchall=False, commit=False):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        result = None
        if fetch:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
            
        if commit:
            conn.commit()
            
        return result
    except mysql.connector.Error as err:
        print(f"Database error executing {query}: {err}")
        if commit:
            conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()
