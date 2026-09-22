import time
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from classesBlock import BlockChain, Block
from db_manager import save_block_to_db, load_chain_from_db, clear_and_sync_db
from validator import validateChain
from auth import get_current_user, create_access_token, authenticate_user, is_setup_complete, create_user, get_user_created_time
from logger import log_action, get_admin_logs, get_user_logs


blockChain = BlockChain() 
app = FastAPI()
peerNodes = set()  #holds unique network peers, no duplicate values

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


print("---SYNCHRONIZING ENGINE WITH MYSQL---")
dbHistory = load_chain_from_db()


if dbHistory:
    blockChain.chain = dbHistory
    print("---DATABASE LOADED---")
else:
    print("---NO ENTRIES CURRENTLY IN THE DATABASE---")


#To validate transaction payload
class TransactionPayLoad(BaseModel):
    sender: str
    reciever: str
    assetId: str
    details: dict

    
#validate node payload
class NodeRegPayload(BaseModel):
    nodes: list[str] #Holds IPv4 of connected peers

#validate user credentials
class credentialPayload(BaseModel):
    username : str
    password : str


#View the ledger : ROUTE A
@app.get("/chain")
def view_ledger(current_user: dict = Depends(get_current_user)):
    serializedChain = [] #OF Block
    for block in blockChain.chain:
        serializedChain.append({
            "index":block.index,
            "transactions":block.transactions,
            "previousHash":block.previousHash,
            "nonce":block.nonce,
            "hash":block.hash,
            "mined_by": block.mined_by
        })

    return {
        "length": len(serializedChain),
        "chain": serializedChain,
        "current_user": current_user["username"],
        "role": current_user["role"]
    }

#Add a transaction to the pending list : ROUTE B
@app.post("/transaction/new")
def add_Transaction(payload: TransactionPayLoad, current_user : dict = Depends(get_current_user)):
    blockChain.addTransactions(payload.sender, payload.reciever, payload.assetId, payload.details, current_user["username"])
    log_action(current_user["username"], "transaction_staged", f"Staged transaction for {payload.assetId}", "success")
    return {
        "timestamp":f"---{time.ctime(time.time())}---",
        "message":"---TRANSACTION STAGED SUCCESSFULLY, CURRENTLY PENDING---",
        "current_user": current_user["username"],
        "role": current_user["role"]
    }

#Mine a pending block : ROUTE C
@app.get("/mine")
def mine_block(current_user : dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        log_action(current_user["username"], "mined_block", "Unauthorized action attempted.", "failed")
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    if not blockChain.pendingTransactions:
        log_action(current_user["username"], "mined_block", "No pending transactions to mine.", "success")
        raise HTTPException(status_code=400, detail="No pending transactions available to mine.")
    
    pendingTransCopy = blockChain.pendingTransactions.copy()  #copy temporarily in case database operation fails
    newBlock = blockChain.minePendingTransactions(current_user["username"])
    saved = save_block_to_db(newBlock)
    if not saved:
        blockChain.chain.pop()  #remove from the actual ledger, since the new block is added on .mine method of BlockChain
        blockChain.pendingTransactions = pendingTransCopy
        log_action(current_user["username"], "mined_block", "Database write failed.","failed")
        raise HTTPException(status_code=500, detail="DATABASE WRITE FAILED!")
    
    log_action(current_user["username"], "mined_block", f"Mined block #{newBlock.index}", "success")
    return {
        "timestamp":f"---{time.ctime(time.time())}---",
        "message":"---BLOCK SUCCESSFULLY MINED AND STORED ON THE DATABASE---",
        "blockDetails":{
            "index": newBlock.index,
            "transactions": newBlock.transactions,
            "previousHash": newBlock.previousHash,
            "nonce": newBlock.nonce,
            "hash": newBlock.hash,
            "mined_by": current_user["username"]
        }
    }

# Register a node to the P2P network : ROUTE D  
@app.post("/nodes/register")
def register_nodes(payload: NodeRegPayload, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        log_action(current_user["username"], "node_registration", "Unauthorized access attempted.", "failed")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not payload.nodes:
        log_action(current_user["username"], "node_registration", "Peer list is not supplied.", "failed")
        raise HTTPException(status_code=400, detail="Invalid request, Supply a list of peers.") 

    for node in payload.nodes:
        cleaned_node = node.replace("http://", "").replace("https://", "").strip("/")
        peerNodes.add(cleaned_node) 
    
    log_action(current_user["username"], "node_registration", f"Registered node {payload.nodes}", "success")
    return {
        "message": "---NEW PEER NODE(S) REGISTERED---",
        "total_nodes": list(peerNodes),
        "current_user": current_user["username"]
    }


#CONSENSUS AND CONFLICT RESOLUTION : ROUTE E
@app.get("/nodes/resolve")
def resolve_conflicts(current_user : dict = Depends(get_current_user)):  # connects with ROUTE A
    global blockChain
    
    if current_user["role"] != "admin":
        log_action(current_user["username"], "conflict_resolution", "Unauthorized access attempted.", "failed")
        raise HTTPException(status_code=403, detail="Admin access required")
    
    longestChain = None
    maxLength = len(blockChain.chain)
    
    for node in peerNodes:
        try:
            response = requests.get(f"http://{node}/chain", timeout=3)  # connected with ROUTE A
            if response.status_code == 200:
                data = response.json()
                length = data.get("length")
                chain = data.get("chain")
                
                if length > maxLength:
                    maxLength = length
                    longestChain = chain
        
        except requests.exceptions.RequestException:
            continue
    
    if longestChain:
        newValidChain = []
        
        for block in longestChain:
            newValidBlock = Block(
                index=block["index"],
                transactions=block["transactions"],
                previousHash=block["previousHash"],
                nonce=block["nonce"]
            )
            newValidBlock.hash = block["hash"]
            newValidBlock.mined_by = block.get("mined_by")
            newValidChain.append(newValidBlock)
        if not validateChain(newValidChain, blockChain.difficulty):
            log_action(current_user["username"], "conflict_resolution", "Consensus rejected, peer chain failed integrity validation, local chain retained", "failed")
            return {
                "message": "---CONSENSUS REJECTED: Peer chain failed integrity validation, retaining local chain---",
                "newLength": len(blockChain.chain),
                "current_user": current_user["username"],
                "role": current_user["role"]
            }
        
        blockChain.chain = newValidChain
        
        # resync with database
        dbSyncSuccess = clear_and_sync_db(newValidChain)
        if not dbSyncSuccess:
            log_action(current_user["username"], "conflict_resolution", "Database synchronisation failed.", "failed")
            raise HTTPException(
                status_code=500, 
                detail="Consensus updated in local memory, but local database synchronisation failed."
            )

        log_action(current_user["username"], "conflict_resolution", "Conflict resolved, local chain replaced by network consensus.", "success")
        return {
            "message": "---CONFLICT RESOLVED: Local chain replaced by network consensus---",
            "newLength": len(blockChain.chain),
            "current_user": current_user["username"],
            "role": current_user["role"]
        }
    
    log_action(current_user["username"], "conflict_resolution", "Consensus secured, local node holds the definitive longest chain.", "success")
    return {
        "message": "---CONSENSUS SECURE: Local node holds the definitive longest chain---",
        "newLength": len(blockChain.chain),
        "current_user": current_user["username"],
        "role": current_user["role"]
    }
        



#AUTH/LOGIN ADMIN(USER)

#SETUP ADMIN
@app.post("/auth/setup")
def setup_admin(userPass : credentialPayload):
    if is_setup_complete():
        log_action(userPass.username, "admin_setup", "Attempted to setup an admin account.", "failed")
        raise HTTPException(status_code=403, detail="Setup already completed")
    
    if len(userPass.password) < 8:
        raise HTTPException(status_code=400, detail="Password must have at least 8 characters.")
    
    created = create_user(userPass.username, userPass.password, created_by = userPass.username, role="admin")
    if not created:
        log_action(userPass.username, "admin_setup", "Failed to create admin credentials.", "failed")
        raise HTTPException(status_code=500, detail="Failed to create credentials.")
    
    log_action(userPass.username, "admin_setup", "Admin setup", "success")
    return {
        "message":f"Admin {userPass.username} created."
    }

#LOGIN ADMIN
@app.post("/auth/login")
def login_user(form_data : OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        log_action(form_data.username, "user_login", "User failed to provide failed credentials.", "failed")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user_token = create_access_token({"sub": user["username"], "role": user["role"]})
    log_action(form_data.username, "user_login", f"{form_data.username} logged in.", "success")
    return {
        "access_token": user_token,
        "token_type": "bearer",
        "role": user["role"]
    }
    

#VERIFY ADMIN
@app.get("/auth/verify")
def verify_user(current_user : dict = Depends(get_current_user)):
    return {
        "message":"Valid token",
        "current_user": current_user["username"],
        "role": current_user["role"]
    }


#SETUP USER
@app.post("/auth/user/create")
def setup_user(userPass : credentialPayload, current_user : dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        log_action(current_user["username"], "setup_localuser", "unauthorized access attempted.", "failed")
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    if len(userPass.password) < 8:
        raise HTTPException(status_code=400, detail="Password must have at least 8 characters.")
    
    created = create_user(userPass.username, userPass.password, created_by=current_user["username"], role="user")
    if not created:
        log_action(current_user["username"], "setup_localuser", f"Failed to create credentials for {userPass.username}", "failed")
        raise HTTPException(status_code=500, detail="Failed to create credentials.")
    
    log_action(current_user["username"], "setup_localuser", f"{current_user['username']} created a local user {userPass.username}.", "success")
    return {
        "message": f"User {userPass.username} created.",
        "created_by" : f"{current_user["username"]}",
        "created_at" : get_user_created_time(userPass.username)
    }
    

#DISPLAY LOG
@app.get("/view/logs")
def view_logs(current_user : dict = Depends(get_current_user)):
    if current_user["role"] == "admin":
        result = get_admin_logs(current_user["username"])
    
    if current_user["role"] == "user":
        result = get_user_logs(current_user["username"])
    
    if result == []:
        raise HTTPException(status_code=500, detail="Could not fetch log details.")
    
    return {
        "logs": result,
        "count": len(result),
        "viewed_by": current_user["username"],
        "role": current_user["role"]
    }