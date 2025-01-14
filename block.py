from time import time

from utility.printable import Printable


class Block(Printable):
    """A single block of our blockchain.

    Attributes:
        :index: The index of this block.
        :previous_hash: The hash of the previous block in the blockchain.
        :timestamp: The timestamp of the block
        (automatically generated by default).
        :votes: A list of vote which are included in the block.
        :proof: The proof of work number that yielded this block.
    """

    def __init__(self, index, previous_hash, votes, proof, time=time()):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = time
        self.votes = votes
        self.proof = proof
