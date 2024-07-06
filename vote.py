from collections import OrderedDict

from utility.printable import Printable


class Vote(Printable):
    """A vote which can be added to a block in the blockchain.

    Attributes:
        :voter: The voter of the votes.
        :candidate: The candidate of the votes.
        :signature: The signature of the vote.
        :amount: The amount of votes sent.
    """

    def __init__(self, voter, candidate, signature, amount):
        self.voter = voter
        self.candidate = candidate
        self.amount = amount
        self.signature = signature

    def to_ordered_dict(self):
        """Converts this vote into a (hashable) OrderedDict."""
        return OrderedDict([
                ('voter', self.voter),
                ('candidate', self.candidate),
                ('amount', self.amount)
            ]
        )
