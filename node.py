from flask import Flask, jsonify, request
from flask_cors import CORS
from ballot import Ballot
from blockchain import Blockchain


app = Flask(__name__)
CORS(app)


elections = {}


@app.route('/create-election', methods=['POST'])
def create_election():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
            }
        return jsonify(response), 400
    required = ['id', 'description']
    if not all(key in values for key in required):
        response = {
            'message': 'Some data is missing.'
            }
        return jsonify(response), 400
    if ballot.load_keys():
        blockchain = Blockchain(
                ballot.public_key, port, values['id'], values['description'])
        global elections
        elections[values['id']] = blockchain
        elections[values['id']].save_data()
        response = {
            'message': 'Election synced successfully.'
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Loading the keys failed.'
        }
        return jsonify(response), 500


@app.route('/generateKeys', methods=['POST'])
def generate_keys():
    private_key, public_key = ballot.generate_keys()
    if private_key:
        response = {
            'public_key': public_key,
            'private_key': private_key
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Generating keys failed.'
        }
        return jsonify(response), 500


@app.route('/ballot', methods=['POST'])
def create_keys():
    ballot.create_keys()
    if ballot.save_keys():
        response = {
            'public_key': ballot.public_key,
            'private_key': ballot.private_key
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Saving the keys failed.'
        }
        return jsonify(response), 500


@app.route('/ballot', methods=['GET'])
def load_keys():
    if ballot.load_keys():
        response = {
            'public_key': ballot.public_key,
            'private_key': ballot.private_key
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Loading the keys failed.'
        }
        return jsonify(response), 500


@app.route('/balance', methods=['POST'])
def get_balance():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required = ['election', 'voter']
    if not all(key in values for key in required):
        response = {
            'message': 'Required data are missing.'
        }
        return jsonify(response), 400
    global elections
    election = int(values['election'])
    balance = elections[election].get_balance(values['voter'])
    if balance is not None:
        response = {
            'message': 'Fetched balance successfully.',
            'funds': balance
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'Loading balance failed.',
            'wallet_set_up': ballot.public_key is not None
        }
        return jsonify(response), 500


@app.route('/broadcast-vote', methods=['POST'])
def broadcast_vote():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
            }
        return jsonify(response), 400
    required = ['election', 'voter', 'candidate', 'amount', 'signature']
    if not all(key in values for key in required):
        response = {
            'message': 'Required data are missing.'
            }
        return jsonify(response), 400
    global elections
    success = elections[int(values['election'])].add_vote(
        values['candidate'],
        values['voter'],
        values['signature'],
        int(values['election']),
        values['amount'],
        is_receiving=True)
    if success:
        response = {
            'message': 'Successfully added Vote!',
            'vote': {
                'voter': values['voter'],
                'candidate': values['candidate'],
                'amount': values['amount'],
                'signature': values['signature']
            }
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Creating a vote failed.'
        }
        return jsonify(response), 500


@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required = ['election', 'block']
    if not all(key in values for key in required):
        response = {
            'message': 'Required data are missing.'
        }
        return jsonify(response), 400
    block = values['block']
    global elections
    election = int(values['election'])
    if block['index'] == elections[election].chain[-1].index + 1:
        if elections[int(values['election'])].add_block(block):
            response = {
                'message': 'Block added'
            }
            return jsonify(response), 201
        else:
            response = {
                'message': 'Block seems invalid.'
            }
            return jsonify(response), 409
    elif block['index'] > elections[int(values['election'])].chain[-1].index:
        response = {
            'message': 'Blockchain seems to differ from local blockchain.'
        }
        elections[int(values['election'])].resolve_conflicts = True
        return jsonify(response), 200
    else:
        response = {
            'message': 'Blockchain seems to be shorter, block not added'
        }
        return jsonify(response), 409


@app.route('/vote', methods=['POST'])
def add_vote():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required_fields = [
        'candidate',
        'voter_public_key',
        'election',
        'voter_private_key'
        ]
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Required data is missing.'
        }
        return jsonify(response), 400
    candidate = values['candidate']
    voter = values['voter_public_key']
    voter_private_key = values['voter_private_key']
    global elections
    if elections[int(values['election'])].get_is_vote(voter):
        response = {
            'message': 'Voter already Voted.'
        }
        return jsonify(response), 400
    signature = ballot.sign_vote(voter, voter_private_key, candidate)
    success = elections[int(values['election'])].add_vote(
        candidate,
        voter,
        signature,
        int(values['election']))
    if success:
        response = {
            'message': 'Successfully added vote.',
            'vote': {
                'voter': voter,
                'candidate': candidate,
                'signature': signature,
                'election': int(values['election'])
            },
            'funds': elections[int(values['election'])].get_balance(voter)
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Creating a vote failed.'
        }
        return jsonify(response), 500


@app.route('/mine', methods=['POST'])
def mine():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required_fields = ['election']
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Election ID Needed!'
        }
        return jsonify(response), 400
    global elections
    if elections[int(values['election'])].resolve_conflicts:
        response = {'message': 'Election ID Needed!'}
        return jsonify(response), 409
    block = elections[int(values['election'])].mine_block()
    if block is not None:
        dict_block = block.__dict__.copy()
        dict_block['votes'] = [
            vt.__dict__ for vt in dict_block['votes']]
        response = {
            'message': 'Block added successfully.',
            'block': dict_block
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Adding a block failed.'
        }
        return jsonify(response), 500


@app.route('/resolve-conflicts', methods=['POST'])
def resolve_conflicts():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required = ['election']
    if not all(key in values for key in required):
        response = {
            'message': 'Election ID is needed!'
        }
        return jsonify(response), 400
    global elections
    election = int(values['election'])
    replaced = elections[election].resolve(int(values['election']))
    if replaced:
        response = {'message': 'Chain was replaced!'}
    else:
        response = {'message': 'Local chain kept!'}
    return jsonify(response), 200


@app.route('/votes', methods=['POST'])
def get_unverified_vote():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required = ['election']
    if not all(key in values for key in required):
        response = {
            'message': 'Election ID is needed!'
        }
        return jsonify(response), 400
    votes = elections[int(values['election'])].get_unverified_votes()
    dict_votes = [vt.__dict__ for vt in votes]
    return jsonify(dict_votes), 200


@app.route('/chain', methods=['GET'])
def get_chain():
    election = request.args.get('election', default=0, type=int)
    if not (election):
        response = {
            'message': 'Election id is missing.'
        }
        return jsonify(response), 400
    global elections
    chain_snapshot = elections[election].chain
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    for dict_block in dict_chain:
        dict_block['votes'] = [
            vt.__dict__ for vt in dict_block['votes']]
    return jsonify(dict_chain), 200


@app.route('/totalmines', methods=['GET'])
def get_totalmines():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
            }
        return jsonify(response), 400
    required = ['election']
    if not all(key in values for key in required):
        response = {
            'message': 'Election id is missing.'
            }
        return jsonify(response), 400
    global elections
    amount_mined = elections[int(values['election'])].get_totalmines()
    if amount_mined is not None:
        response = {
            'message': 'Fetched total mines successfully.',
            'amount_mined': amount_mined
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'Loading total mines failed.',
            'wallet_set_up': ballot.public_key is not None
        }
        return jsonify(response), 500


@app.route('/vote-eligibility', methods=['POST'])
def get_is_vote():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required = ['election', 'voter']
    if not all(key in values for key in required):
        response = {
            'message': 'Required data are missing.'
        }
        return jsonify(response), 400
    global elections
    isVote = elections[int(values['election'])].get_is_vote(values['voter'])
    if isVote is not None:
        response = {
            'message': 'Fetched request successfully.',
            'isVote': isVote
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'Fetching isVote failed.',
            'wallet_set_up': ballot.public_key is not None
        }
        return jsonify(response), 500


@app.route('/results', methods=['POST'])
def add_results():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required_fields = ['candidate', 'election']
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Required data is missing.'
        }
        return jsonify(response), 400
    global elections
    election = int(values['election'])
    results = elections[election].get_results(values['candidate'])
    response = {
        'message': 'Fetched request successfully.',
        'Votes': results
    }
    return jsonify(response), 200


@app.route('/results-voters', methods=['POST'])
def get_results_voters():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
        }
        return jsonify(response), 400
    required_fields = ['candidate', 'election']
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Required data is missing.'
        }
        return jsonify(response), 400
    global elections
    election = int(values['election'])
    results = elections[election].get_results_voters(values['candidate'])
    response = {
        'message': 'Fetched request successfully.',
        'Voters': results
    }
    return jsonify(response), 200


@app.route('/node', methods=['POST'])
def add_node():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data attached.'
        }
        return jsonify(response), 400
    required = ['election', 'node']
    if not all(key in values for key in required):
        response = {
            'message': 'Required data are missing.'
        }
        return jsonify(response), 400
    node = values['node']
    elections[int(values['election'])].add_peer_node(node)
    response = {
        'message': 'Node added successfully.',
        'all_nodes': elections[int(values['election'])].get_peer_nodes()
    }
    return jsonify(response), 201


@app.route('/node', methods=['DELETE'])
def remove_node():
    election = request.args.get('election', default=0, type=int)
    node_url = request.args.get('node_url', type=str)
    if not (election and node_url):
        response = {
            'message': 'Required data are missing.'
        }
        return jsonify(response), 400
    global elections
    if node_url == '' or node_url is None:
        response = {
            'message': 'No node found.'
        }
        return jsonify(response), 400
    elections[election].remove_peer_node(node_url)
    response = {
        'message': 'Node removed',
        'all_nodes': elections[election].get_peer_nodes()
    }
    return jsonify(response), 200


@app.route('/nodes', methods=['GET'])
def get_nodes():
    election = request.args.get('election', default=0, type=int)
    if not (election):
        response = {
            'message': 'Election id is missing.'
        }
        return jsonify(response), 400
    global elections
    nodes = elections[election].get_peer_nodes()
    response = {
        'all_nodes': nodes
    }
    return jsonify(response), 201


@app.route('/election', methods=['GET'])
def get_elections():
    election = request.args.get('election', default=0, type=int)
    global elections
    if elections.get(election) is not None:
        response = {
            'election': 1
        }
        return jsonify(response), 201
    else:
        response = {
            'election': 0
        }
        return jsonify(response), 201


@app.route('/')
def serverStatus():
    return 'Server Running Correctly!'


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8900)
    args = parser.parse_args()
    port = args.port
    ballot = Ballot(port)
    blockchain = Blockchain(ballot.public_key, port)
    app.run(host='0.0.0.0', port=port)