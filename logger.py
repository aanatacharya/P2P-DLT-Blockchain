from auth import get_db_connection

import mysql.connector
from mysql.connector import Error

def log_action(username, action, details=None, status="success"):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        data_tuple = (username, action, details, status)
        query = """INSERT INTO audit_log 
                (username, action, detail, status) 
                VALUES(%s, %s, %s, %s)
                """
        cursor.execute(query, data_tuple)
        connection.commit()
        print(f"---Log added {username}, status : {status}, action : {action}---")
        return True
    except Error as e:
        print(f"Error in log_action: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("---DB Connection closed log_action---")


def get_user_logs(username):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM audit_log WHERE username=%s ORDER BY created_at DESC",(username,))
        result = cursor.fetchall()
        if not result:
            return []
        
        for row in result:
            row["created_at"] = str(row["created_at"])
        
        return result
    
    except Error as e:
        print(f"---CANNOT CONNECT TO THE DATABASE get_user_logs: {e}---")
        return []
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            print("---DB CONNECTION CLOSE get_user_logs---")
            connection.close()


def get_admin_logs(username):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM audit_log WHERE username=%s OR username IN ( SELECT username FROM admin_users WHERE created_by =%s ) ORDER BY created_at DESC",(username, username,))
        result = cursor.fetchall()
        if not result:
            return []
        
        for row in result:
            row["created_at"] = str(row["created_at"])
        
        return result
    
    except Error as e:
        print(f"---CANNOT CONNECT TO THE DATABASE get_admin_logs: {e}---")
        return []
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            print("---DB CONNECTION CLOSE get_admin_logs---")
            connection.close()

    
        
    
