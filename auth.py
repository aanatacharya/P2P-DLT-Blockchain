from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from mysql.connector import Error

import time
import mysql.connector

Secret_Key = "7asd--asdasdasdsadawddasda123132"
Algorithm = "HS256"
Access_Token_Expire_Hours = 2

pwd_context = CryptContext( schemes=["bcrypt"], deprecated = "auto")

oauth2_Scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db_connection():
    return mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='supply_chain_db'
        )

def hash_password(password:str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data:dict):
    copyData = data.copy()
    copyData["exp"] = datetime.utcnow() + timedelta(hours=Access_Token_Expire_Hours)
    return jwt.encode(copyData, Secret_Key, algorithm=Algorithm)

def verify_token(token):
    try:
        payload = jwt.decode(token, Secret_Key, algorithms=[Algorithm])
        sub_username = payload.get("sub") #get a username/ sub key has a username
        role = payload.get("role")
        if not sub_username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {
            "username": sub_username,
            "role": role
        }
        
    except JWTError as e:
        print(f"JWTError, {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    
def get_current_user(token = Depends(oauth2_Scheme)):
    return verify_token(token)

def is_setup_complete():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM admin_users;")
        count = cursor.fetchone()
        if count[0] > 0:
            return True
        else:
            return False
    except Error as e:
        print(f"is_setup_complete error: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("---DB CONNECTION CLOSED is_setup_complete---")


def create_user(username, password, created_by=None , role="user"):
    connection = None
    cursor = None
    try:
        
        hashedPwd = hash_password(password)
        connection = get_db_connection()
        cursor = connection.cursor()
        query = """INSERT INTO admin_users
                (username, hashed_password, created_by, role) 
                VALUES(%s, %s, %s, %s)"""
        dataTuple = (username, hashedPwd, created_by, role)
        cursor.execute(query, dataTuple)
        connection.commit()
        print("---Username and password inserted---")
        return True
    except Error as e:
        print(f"---create_admin error: {e}---")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("---DB connection closed for create_admin---")

def authenticate_user(username, password):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin_users WHERE username=%s", (username,))
        result = cursor.fetchone()
        if not result:
            return None
        
        if not verify_password(password, result["hashed_password"]):
            return None
        
        return result
    except Error as e:
        print(f"---Error in authenticate_user: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("---DB connection closed for authenticate_user---")

    

def get_user_created_time(current_user):
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT created_at FROM admin_users WHERE username=%s", (current_user,))
        result = cursor.fetchone()
        if not result:
            return None
        return str(result[0])
    except Error as e:
        print(f"---ERROR in get_user_created_time:{e}---")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("---DB connection closed for get_user_created_time---")

    