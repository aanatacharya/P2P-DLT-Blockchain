
import mysql.connector
from mysql.connector import Error
import json
import time
from classesBlock import Block

def save_block_to_db(block):  # block : Block
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='supply_chain_db'
        )
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Successfully connected to mySQL Server version: {db_info}")
            
            cursor = connection.cursor()
            transactionList = json.dumps(block.transactions, sort_keys=True)
            thisQuery = """
                INSERT INTO verified_blocks 
                (block_index, timestamp, transactions_json, previous_hash, nonce, block_hash, mined_by) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
            dataTuple = (
                block.index, 
                time.time(), 
                transactionList, 
                block.previousHash, 
                block.nonce, 
                block.hash,
                block.mined_by 
            )
            
            cursor.execute(thisQuery, dataTuple)
            connection.commit()
            print(f"---Block {block.index} successfully committed to database---")
            return True
            
    except Error as e:
        print(f"---ERROR WHILE CONNECTING TO THE DATABASE: {e}---")
        return False
    
    finally:
        # Closing the connection
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("---MySQL connection CLOSED---")


def load_chain_from_db():
    connection = None
    cursor = None
    chainList = []
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='supply_chain_db'
        )
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Successfully connected to mySQL Server version: {db_info}")
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM verified_blocks ORDER BY block_index ASC")
            rows = cursor.fetchall()
            
            for row in rows:
                rawJsonString = row["transactions_json"]
                transactionsList = json.loads(rawJsonString)
                
                newBlock = Block(
                    index=row['block_index'],
                    transactions=transactionsList,
                    previousHash=row['previous_hash'],
                    nonce=row['nonce']
                )
                newBlock.hash = row['block_hash']
                newBlock.mined_by = row['mined_by']
                chainList.append(newBlock)
                
            print(f"---BLOCKS LOADED SUCCESSFULLY, {len(chainList)} BLOCKS LOGGED---")
            
    except Error as e:
        print(f"---ERROR WHILE CONNECTING TO THE DATABASE {e}---")
    finally:
        # close the connection
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("---MySQL CONNECTION CLOSED---")

        return chainList


#CONSENSUS/RESOLUTION OF CONFLICT ALGORITHM
def clear_and_sync_db(newChain):
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='supply_chain_db'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            cursor.execute("TRUNCATE TABLE verified_blocks;")
            
            thisQuery = """
                INSERT INTO verified_blocks 
                (block_index, timestamp, transactions_json, previous_hash, nonce, block_hash, mined_by) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
        
            for block in newChain:
                transactionList = json.dumps(block.transactions, sort_keys=True)
                dataTuple = (
                    block.index, 
                    time.time(), 
                    transactionList, 
                    block.previousHash, 
                    block.nonce, 
                    block.hash,
                    block.mined_by
                )
                cursor.execute(thisQuery, dataTuple)
            
            
            connection.commit()
            print("---DATABASE RESYNCED WITH NETWORK CONSENSUS---")
            return True
            
    except Error as e:
        print(f"---DATABASE CANNOT BE SYNCED, ERROR: {e}---")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
