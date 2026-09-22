import time
from crypEngine import Hash, initiateMining

class Block:
    def __init__(self, index, transactions, previousHash, mined_by = None, nonce = 0):
        self.index = index #INTEGER
        self.transactions = transactions #LIST//DICTIONARY
        self.previousHash = previousHash #STRING//HEXADECIMAL
        self.mined_by = mined_by
        
        self.nonce = nonce  #INTEGER
        self.blockData = str(str(index) + str(transactions) + str(previousHash))
        self.hash = self.calculateHash()
    
    def calculateHash(self):
        return Hash(self.blockData, self.nonce)
    
    def mineBlock(self, difficulty):
        self.nonce, self.hash = initiateMining(self.blockData, difficulty)
        return self.nonce, self.hash


class BlockChain:
    def __init__(self, difficulty = 4):
        self.chain = [] 
        self.pendingTransactions = [] 
        self.difficulty = difficulty #INTEGER
        
        self.createGenesisBlock()
    
    def createGenesisBlock(self):
        #CREATING THE FIRST BLOCK
        
        genesisBlock = Block(0, "Genesis Block - System Init", "0")
        genesisBlock.mineBlock(self.difficulty)
        self.chain.append(genesisBlock)
        print("---GENESIS BLOCK FORMED---")
        
    def addTransactions(self, sender, reciever, asset_id, details, submitted_by):
        #APPENDS A NEW BLOCK(TRANSACTION/DATA) INTO THE PENDING POOL
        transaction = {
            "sender": sender,
            "reciever": reciever,
            "assetId": asset_id,
            "details": details, #details: DICTIONARY//STRING
            "submitted_by": submitted_by,
            "timestamp": time.ctime(time.time())
        }
        print(f"A new transaction is created at {transaction["timestamp"]}, submitted by {submitted_by}")
        
        self.pendingTransactions.append(transaction)
        print(f"There are {len(self.pendingTransactions)} pending transaction currently.")
        return len(self.pendingTransactions)

    def minePendingTransactions(self, mined_by):
        
        if not self.pendingTransactions: #No pending transactions currently
            print("There are no pending transactions to mine.")
            return False
        
        latestBlock = self.chain[-1]
        newBlock = Block(len(self.chain), self.pendingTransactions, latestBlock.calculateHash(), mined_by)
        newBlock.mineBlock(self.difficulty)
        self.chain.append(newBlock)
        self.pendingTransactions = [] #Empty any pending transactions given it gets chained
        print(f"Transaction mined and chained successfully. Mined by: {mined_by}")
        return newBlock


        
        
        
        
        
        