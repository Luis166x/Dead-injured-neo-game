"""
server.py
Backend server for Dead Injured Neo multiplayer
Uses Flask + Flask-SocketIO for real-time communication
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import os
from utils import calculate_result, valid_code

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///din.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-change-this'

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ================= Models =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Integer, default=1000)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    online = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'rating': self.rating,
            'wins': self.wins,
            'losses': self.losses,
            'matches_played': self.matches_played,
            'online': self.online,
            'created_at': self.created_at.isoformat()
        }


class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'friend_id': self.friend_id,
            'status': self.status
        }


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player1_secret = db.Column(db.String(4), nullable=True)
    player2_secret = db.Column(db.String(4), nullable=True)
    player1_guesses = db.Column(db.Integer, default=0)
    player2_guesses = db.Column(db.Integer, default=0)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='waiting_secrets')  # waiting_secrets, playing, finished
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'player1_id': self.player1_id,
            'player2_id': self.player2_id,
            'player1_guesses': self.player1_guesses,
            'player2_guesses': self.player2_guesses,
            'winner_id': self.winner_id,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'message': self.message,
            'created_at': self.created_at.isoformat()
        }


# ================= JWT Auth =================

def create_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30),
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')


def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except:
        return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = verify_jwt_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated


# ================= REST API =================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing fields'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    
    token = create_jwt_token(user.id)
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing credentials'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user.online = True
    db.session.commit()
    
    token = create_jwt_token(user.id)
    return jsonify({'token': token, 'user': user.to_dict()}), 200


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    limit = request.args.get('limit', 50, type=int)
    users = User.query.order_by(User.rating.desc()).limit(limit).all()
    
    leaderboard = []
    for rank, user in enumerate(users, 1):
        user_data = user.to_dict()
        user_data['rank'] = rank
        leaderboard.append(user_data)
    
    return jsonify(leaderboard), 200


@app.route('/api/friends', methods=['GET'])
@token_required
def get_friends():
    friendships = Friendship.query.filter(
        ((Friendship.user_id == request.user_id) | (Friendship.friend_id == request.user_id)),
        Friendship.status == 'accepted'
    ).all()
    
    friends = []
    for fs in friendships:
        fid = fs.friend_id if fs.user_id == request.user_id else fs.user_id
        friend = User.query.get(fid)
        if friend:
            friends.append(friend.to_dict())
    
    return jsonify(friends), 200


@app.route('/api/friends/add/<int:friend_id>', methods=['POST'])
@token_required
def add_friend(friend_id):
    if friend_id == request.user_id:
        return jsonify({'error': 'Cannot add yourself'}), 400
    
    existing = Friendship.query.filter_by(user_id=request.user_id, friend_id=friend_id).first()
    if existing:
        return jsonify({'error': 'Already sent request'}), 400
    
    fs = Friendship(user_id=request.user_id, friend_id=friend_id, status='pending')
    db.session.add(fs)
    db.session.commit()
    return jsonify({'message': 'Friend request sent'}), 201


@app.route('/api/friends/accept/<int:friend_id>', methods=['POST'])
@token_required
def accept_friend(friend_id):
    fs = Friendship.query.filter_by(user_id=friend_id, friend_id=request.user_id).first()
    if fs:
        fs.status = 'accepted'
        db.session.commit()
        return jsonify({'message': 'Friend accepted'}), 200
    return jsonify({'error': 'No request found'}), 404


@app.route('/api/matches', methods=['GET'])
@token_required
def get_matches():
    matches = Match.query.filter(
        (Match.player1_id == request.user_id) | (Match.player2_id == request.user_id)
    ).order_by(Match.created_at.desc()).limit(20).all()
    
    return jsonify([m.to_dict() for m in matches]), 200


# ================= WebSocket Events =================

active_users = {}  # user_id -> socket_id
matchmaking_queue = []
active_matches = {}  # match_id -> {player1_data, player2_data}


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit('connect_response', {'message': 'Connected to server'})


@socketio.on('authenticate')
def handle_authenticate(data):
    token = data.get('token')
    user_id = verify_jwt_token(token)
    
    if not user_id:
        emit('error', {'message': 'Invalid token'})
        return
    
    user = User.query.get(user_id)
    if not user:
        emit('error', {'message': 'User not found'})
        return
    
    active_users[user_id] = request.sid
    socketio.emit('user_online', {'user_id': user_id, 'username': user.username}, broadcast=True)
    print(f"User {user.username} authenticated")


@socketio.on('disconnect')
def handle_disconnect():
    for uid, sid in list(active_users.items()):
        if sid == request.sid:
            user = User.query.get(uid)
            if user:
                user.online = False
                db.session.commit()
                socketio.emit('user_offline', {'user_id': uid, 'username': user.username}, broadcast=True)
            del active_users[uid]
            print(f"User {uid} disconnected")
            break


@socketio.on('join_matchmaking')
def handle_join_matchmaking(data):
    user_id = data.get('user_id')
    
    if user_id not in active_users:
        emit('error', {'message': 'Not authenticated'})
        return
    
    if user_id in matchmaking_queue:
        emit('error', {'message': 'Already in queue'})
        return
    
    matchmaking_queue.append(user_id)
    print(f"User {user_id} joined matchmaking queue. Queue size: {len(matchmaking_queue)}")
    
    # Check if we can make a match
    if len(matchmaking_queue) >= 2:
        p1_id = matchmaking_queue.pop(0)
        p2_id = matchmaking_queue.pop(0)
        
        match = Match(player1_id=p1_id, player2_id=p2_id, status='waiting_secrets')
        db.session.add(match)
        db.session.commit()
        
        print(f"Match created: {match.id} between {p1_id} and {p2_id}")
        
        # Notify both players
        p1_user = User.query.get(p1_id)
        p2_user = User.query.get(p2_id)
        
        if p1_id in active_users:
            socketio.emit('match_found', {
                'match_id': match.id,
                'opponent_id': p2_id,
                'opponent_username': p2_user.username,
                'you_are': 'player1'
            }, room=active_users[p1_id])
        
        if p2_id in active_users:
            socketio.emit('match_found', {
                'match_id': match.id,
                'opponent_id': p1_id,
                'opponent_username': p1_user.username,
                'you_are': 'player2'
            }, room=active_users[p2_id])


@socketio.on('set_secret')
def handle_set_secret(data):
    match_id = data.get('match_id')
    player_id = data.get('player_id')
    secret = data.get('secret')
    
    if not valid_code(secret):
        emit('error', {'message': 'Invalid secret code'})
        return
    
    match = Match.query.get(match_id)
    if not match:
        emit('error', {'message': 'Match not found'})
        return
    
    # Store secret
    if player_id == match.player1_id:
        match.player1_secret = secret
    elif player_id == match.player2_id:
        match.player2_secret = secret
    else:
        emit('error', {'message': 'Not in this match'})
        return
    
    # Check if both players have set their secrets
    if match.player1_secret and match.player2_secret:
        match.status = 'playing'
        socketio.emit('game_start', {
            'match_id': match.id,
            'message': 'Both players ready! Game starting...'
        }, broadcast=True, skip_sid=request.sid)
    
    db.session.commit()
    print(f"Player {player_id} set secret for match {match_id}")


@socketio.on('guess')
def handle_guess(data):
    match_id = data.get('match_id')
    player_id = data.get('player_id')
    guess = data.get('guess')
    
    if not valid_code(guess):
        emit('error', {'message': 'Invalid guess format'})
        return
    
    match = Match.query.get(match_id)
    if not match:
        emit('error', {'message': 'Match not found'})
        return
    
    if match.status != 'playing':
        emit('error', {'message': 'Match is not in playing state'})
        return
    
    # Determine which player is guessing and which secret to check
    if player_id == match.player1_id:
        secret = match.player2_secret
        match.player1_guesses += 1
        opponent_id = match.player2_id
    elif player_id == match.player2_id:
        secret = match.player1_secret
        match.player2_guesses += 1
        opponent_id = match.player1_id
    else:
        emit('error', {'message': 'Not in this match'})
        return
    
    # Calculate result
    dead, injured, neo = calculate_result(secret, guess)
    
    # Check if player won
    if dead == 4:
        match.winner_id = player_id
        match.status = 'finished'
        
        # Update user stats
        winner = User.query.get(player_id)
        loser = User.query.get(opponent_id)
        
        winner.wins += 1
        winner.rating += 10
        loser.losses += 1
        loser.rating = max(900, loser.rating - 5)
        
        db.session.commit()
        
        # Notify both players
        socketio.emit('match_end', {
            'match_id': match.id,
            'winner_id': player_id,
            'winning_guess': guess,
            'guesses_taken': match.player1_guesses if player_id == match.player1_id else match.player2_guesses
        }, broadcast=True)
    else:
        db.session.commit()
        
        # Notify opponent
        if opponent_id in active_users:
            socketio.emit('opponent_guess', {
                'match_id': match.id,
                'guess': guess,
                'dead': dead,
                'injured': injured,
                'neo': neo
            }, room=active_users[opponent_id])
    
    print(f"Player {player_id} guessed '{guess}' in match {match_id}: D={dead}, I={injured}")


@socketio.on('send_message')
def handle_send_message(data):
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    match_id = data.get('match_id')
    
    msg = ChatMessage(sender_id=sender_id, receiver_id=receiver_id, match_id=match_id, message=message)
    db.session.add(msg)
    db.session.commit()
    
    sender = User.query.get(sender_id)
    
    if receiver_id in active_users:
        socketio.emit('new_message', {
            'message': msg.to_dict(),
            'sender_username': sender.username
        }, room=active_users[receiver_id])


@app.before_request
def create_tables():
    db.create_all()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
