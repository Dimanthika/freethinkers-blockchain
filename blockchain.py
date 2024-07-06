from functools import reduce
import json
import requests

# Import two functions from our hash_util.py file. Omit the ".py" in the import
from utility.hash_util import hash_block
from utility.verification import Verification
from block import Block
from vote import Vote
from ballot import Ballot

# The reward we give to miners (for creating a new block)
MINING_REWARD = 1


class Blockchain:
    """The Blockchain class manages the chain of blocks as well as open votes
    and the node on which it's running.


    Attributes:
        :chain: The list of blocks
        :unverified_votes (private): The list of open votes
        :public_key: The connected node (which runs the blockchain).
    """

    def __init__(
            self, public_key, node_id, election_id=None, description=None):
        """The constructor of the Blockchain class."""
        # Our starting block for the blockchain
        genesis_block = Block(0, description, [], election_id, 0)
        # Initializing our (empty) blockchain list
        self.chain = [genesis_block]
        # Unhandled votes
        self.__unverified_votes = []
        self.public_key = public_key
        self.__peer_nodes = set()
        self.node_id = node_id
        self.election_id = election_id
        self.resolve_conflicts = False
        self.load_data()

    # This turns the chain attribute into a property with a getter
    # (the method below) and a setter (@chain.setter)
    @property
    def chain(self):
        return self.__chain[:]

    # The setter for the chain property
    @chain.setter
    def chain(self, val):
        self.__chain = val

    def get_unverified_votes(self):
        """Returns a copy of the open votes list."""
        return self.__unverified_votes[:]

    def load_data(self):
        """Initialize blockchain + open transactions data from a file."""
        try:
            with open('blockchain-{}-{}.txt'.format(
                    self.node_id, self.election_id), mode='r') as f:
                file_content = f.readlines()
                blockchain = json.loads(file_content[0][:-1])
                # We need to convert  the loaded data because
                # Transactions should use OrderedDict
                updated_blockchain = []
                for block in blockchain:
                    converted_tx = [Vote(
                        vt['voter'],
                        vt['candidate'],
                        vt['signature'],
                        vt['amount'])
                        for vt in block['votes']
                        ]
                    updated_block = Block(
                        block['index'],
                        block['previous_hash'],
                        converted_tx,
                        block['proof'],
                        block['timestamp']
                        )
                    updated_blockchain.append(updated_block)
                self.chain = updated_blockchain
                unverified_votes = json.loads(file_content[1][:-1])
                # We need to convert  the loaded data because
                # Transactions should use OrderedDict
                updated_transactions = []
                for vt in unverified_votes:
                    updated_transaction = Vote(
                        vt['voter'],
                        vt['candidate'],
                        vt['signature'],
                        vt['amount']
                        )
                    updated_transactions.append(updated_transaction)
                self.__unverified_votes = updated_transactions
                peer_nodes = json.loads(file_content[2])
                self.__peer_nodes = set(peer_nodes)
        except (IOError, IndexError):
            pass
        finally:
            print('Cleanup!')

    def save_data(self):
        """Save blockchain + open votes snapshot to a file."""
        try:
            with open('blockchain-{}-{}.txt'.format(
                    self.node_id, self.election_id), mode='w') as f:
                saveable_chain = [
                    block.__dict__ for block in
                    [
                        Block(
                            block_el.index,
                            block_el.previous_hash,
                            [vt.__dict__ for vt in block_el.votes],
                            block_el.proof,
                            block_el.timestamp) for block_el in self.__chain
                    ]
                ]
                f.write(json.dumps(saveable_chain))
                f.write('\n')
                saveable_tx = [vt.__dict__ for vt in self.__unverified_votes]
                f.write(json.dumps(saveable_tx))
                f.write('\n')
                f.write(json.dumps(list(self.__peer_nodes)))
                # save_data = {
                #     'chain': blockchain,
                #     'ot': unverified_votes
                # }
                # f.write(pickle.dumps(save_data))
        except IOError:
            print('Saving failed!')

    def proof_of_work(self):
        """Generate a proof of work for the open votes,
        the hash of the previous block and a random number
        (which is guessed until it fits)."""
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        # Try different PoW numbers and return the first valid one
        while not Verification.valid_proof(
                self.__unverified_votes,
                last_hash,
                proof):
            proof += 1
        return proof

    def get_balance(self, voter=None):
        """Calculate and return the balance for a participant.
        """
        if voter is None:
            if self.public_key is None:
                return None
            participant = self.public_key
        else:
            participant = voter
        # Fetch a list of all sent vote amounts for the given person
        # (empty lists are returned if the person was NOT the voter)
        # This fetches sent amounts of votes that were already included
        # in blocks of the blockchain
        tx_sender = [[vt.amount for vt in block.votes
                      if vt.voter == participant] for block in self.__chain]
        # Fetch a list of all sent vote amounts for the given person
        # (empty lists are returned if the person was NOT the voter)
        # This fetches sent amounts of open votes (to avoid double spending)
        open_tx_sender = [vt.amount
                          for vt in self.__unverified_votes
                          if vt.voter is participant]
        tx_sender.append(open_tx_sender)

        print(tx_sender)
        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                             if len(tx_amt) > 0 else tx_sum + 0, tx_sender, 0)

        # This fetches received vote amounts of votes that were already
        # included in blocks of the blockchain
        # We ignore open votes here because you shouldn't be able to
        # spend votes before the vote was confirmed + included in a block
        tx_recipient = [
                    [vt.amount for vt in block.votes
                        if vt.candidate == participant]
                    for block in self.__chain
        ]
        amount_received = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                                 if len(tx_amt) > 0
                                 else tx_sum + 0, tx_recipient, 0)

        # Return the total balance
        return amount_received - amount_sent

    def get_totalmines(self, voter=None):
        """Calculate and return the total amount of mines for a participant.
        """
        if voter is None:
            if self.public_key is None:
                return None
            participant = self.public_key
        else:
            participant = voter
        tx_rec = [
            [vt.amount for vt in block.votes
                if vt.candidate == participant and vt.voter == 'MINING']
            for block in self.__chain
        ]
        amount_mined = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                              if len(tx_amt) > 0 else tx_sum + 0, tx_rec, 0)

        # Return the total amount of mines
        return amount_mined

    def get_results_voters(self, candidate):
        if candidate is None:
            return None

        tx_rec = [
            [vt.voter for vt in block.votes
                if vt.candidate == candidate and vt.voter != 'MINING']
            for block in self.__chain
        ]

        return tx_rec

    def get_results(self, candidate):
        if candidate is None:
            return None

        tx_rec = [
            [vt.amount for vt in block.votes
                if vt.candidate == candidate and vt.voter != 'MINING']
            for block in self.__chain
        ]
        results = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                         if len(tx_amt) > 0 else tx_sum + 0, tx_rec, 0)

        # Return the total amount of mines
        return results

    def get_is_vote(self, voter=None):
        """Check weather particpant was voted or not.
        """
        if voter is None:
            if self.public_key is None:
                return None
            participant = self.public_key
        else:
            participant = voter
        # Fetch a list of all sent vote amounts for the given person
        # (empty lists are returned if the person was NOT the voter)
        # This fetches sent amounts of votes that were already included in
        # blocks of the blockchain
        tx_sender = [[vt.amount for vt in block.votes
                      if vt.voter == participant] for block in self.__chain]
        # Fetch a list of all sent vote amounts for the given person
        # (empty lists are returned if the person was NOT the voter)
        # This fetches sent amounts of open votes (to avoid double spending)
        open_tx_sender = [vt.amount
                          for vt in self.__unverified_votes
                          if vt.voter == participant]
        tx_sender.append(open_tx_sender)

        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                             if len(tx_amt) > 0 else tx_sum + 0, tx_sender, 0)

        if (amount_sent >= 1):
            return True

        if (amount_sent == 0):
            return False

        return None

    def get_last_blockchain_value(self):
        """ Returns the last value of the current blockchain. """
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]
    
    def add_vote(self,
                 candidate,
                 voter,
                 signature,
                 election,
                 amount=1,
                 is_receiving=False):

        if self.get_is_vote(voter):
            return False
        vote = Vote(voter, candidate, signature, amount)
        if Verification.verify_vote(vote, self.get_balance, False):
            self.__unverified_votes.append(vote)
            self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = '{}/broadcast-vote'.format(node)
                    try:
                        response = requests.post(url,
                                                 json={
                                                     'voter': voter,
                                                     'candidate': candidate,
                                                     'amount': amount,
                                                     'signature': signature,
                                                     'election': election})
                        if (response.status_code == 400 or
                                response.status_code == 500):
                            print('Vote declined, needs resolving')
                            return False
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        return False

    def mine_block(self):
        """Create a new block and add open votes to it."""
        # Fetch the currently last block of the blockchain
        if self.public_key is None:
            return None
        last_block = self.__chain[-1]
        # Hash the last block (=> to be able to compare it
        # to the stored hash value)
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()
        reward_vote = Vote(
            'MINING', self.public_key, '', MINING_REWARD)
        # Copy vote instead of manipulating the original unverified_votes list
        # This ensures that if for some reason the mining should fail,
        # we don't have the reward vote stored in the open votes
        copied_votes = self.__unverified_votes[:]
        for vt in copied_votes:
            if not Ballot.verify_vote(vt):
                return None
        copied_votes.append(reward_vote)
        block = Block(len(self.__chain), hashed_block,
                      copied_votes, proof)
        self.__chain.append(block)
        self.__unverified_votes = []
        self.save_data()
        for node in self.__peer_nodes:
            url = '{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['votes'] = [
                vt.__dict__ for vt in converted_block['votes']]
            try:
                response = requests.post(url, json={
                    'block': converted_block,
                    'election': self.election_id
                    })
                if response.status_code == 400 or response.status_code == 500:
                    print('Block declined, needs resolving')
                if response.status_code == 409:
                    self.resolve_conflicts = True
            except requests.exceptions.ConnectionError:
                continue
        return block

    def add_block(self, block):
        votes = [Vote(vt['voter'],
                 vt['candidate'],
                 vt['signature'],
                 vt['amount']) for vt in block['votes']]
        proof_is_valid = Verification.valid_proof(
            votes[:-1], block['previous_hash'], block['proof'])
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False
        converted_block = Block(
            block['index'],
            block['previous_hash'],
            votes, block['proof'],
            block['timestamp'])
        self.__chain.append(converted_block)
        stored_transactions = self.__unverified_votes[:]
        for ivt in block['votes']:
            for unverified_votes in stored_transactions:
                if (unverified_votes.voter == ivt['voter'] and
                        unverified_votes.candidate == ivt['candidate'] and
                        unverified_votes.amount == ivt['amount'] and
                        unverified_votes.signature == ivt['signature']):
                    try:
                        self.__unverified_votes.remove(unverified_votes)
                    except ValueError:
                        print('Item was already removed')
        self.save_data()
        return True

    def resolve(self, election):
        winner_chain = self.chain
        replace = False
        for node in self.__peer_nodes:
            url = '{}/chain?election={}'.format(node, election)
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(
                    block['index'],
                    block['previous_hash'],
                    [
                        Vote(
                            vt['voter'],
                            vt['candidate'],
                            vt['signature'],
                            vt['amount']) for vt in block['votes']
                    ],
                    block['proof'],
                    block['timestamp']) for block in node_chain
                ]
                node_chain_length = len(node_chain)
                local_chain_length = len(winner_chain)
                if (node_chain_length > local_chain_length and
                        Verification.verify_chain(node_chain)):
                    winner_chain = node_chain
                    replace = True
            except requests.exceptions.ConnectionError:
                continue
        self.resolve_conflicts = False
        self.chain = winner_chain
        if replace:
            self.__unverified_votes = []
        self.save_data()
        return replace

    def add_peer_node(self, node):
        """Adds a new node to the peer node set.

        Arguments:
            :node: The node URL which should be added.
        """
        self.__peer_nodes.add(node)
        self.save_data()

    def remove_peer_node(self, node):
        """Removes a node from the peer node set.

        Arguments:
            :node: The node URL which should be removed.
        """
        self.__peer_nodes.discard(node)
        self.save_data()

    def get_peer_nodes(self):
        """Return a list of all connected peer nodes."""
        return list(self.__peer_nodes)
