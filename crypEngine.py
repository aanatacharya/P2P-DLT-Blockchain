
import hashlib
import json
import time

def Hash(thisData, thisNonce):
    # Ensure dictionaries/objects are stringified consistently
    if isinstance(thisData, (dict, list)):
        dataString = json.dumps(thisData, sort_keys=True)
    else:
        dataString = str(thisData)
    
    thisData = dataString + str(thisNonce) 
    encodedData = thisData.encode('utf-8')   #encode the data string into bytes
    hashObject = hashlib.sha256(encodedData) #create a SHA-256 object
    return hashObject.hexdigest()            #return hexadecimal representation of the hash

def initiateMining(theData, Difficulty):
    Nonce= 0
    targetPrefix = "0" * Difficulty
    startTime = time.time()
    
    print(f"Mining Initiated. Target prefix: {targetPrefix}. Initial Nonce = {Nonce}")
    while True:
        blockHash = Hash(theData, Nonce)
        if blockHash.startswith(targetPrefix):
            elapsedTime = time.time() - startTime
            print(f"Mine success!, Block mine is at {Nonce}. Time taken to mine {round(elapsedTime, 4)} seconds")
            return Nonce, blockHash
        Nonce += 1









