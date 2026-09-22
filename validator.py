from crypEngine import Hash
from classesBlock import Block, BlockChain

def validateChain(chain, difficulty):
    for i in range(1, len(chain)):
        currentBlock = chain[i]
        previousBlock = chain[i - 1]
        
        recomputedHash = Hash(
            str(str(currentBlock.index) + str(currentBlock.transactions) + str(currentBlock.previousHash)),
            currentBlock.nonce
        )
        if currentBlock.hash != recomputedHash:
            print(f"STORED: {currentBlock.hash}")
            print(f"COMPUTED: {recomputedHash}")
            return False
        
        if currentBlock.previousHash != previousBlock.hash:
            return False
        
        if not currentBlock.hash.startswith("0" * difficulty):
            return False
    
    return True   #Even if the argument chain is of length 1, the chain's still valid, thus True is returned



