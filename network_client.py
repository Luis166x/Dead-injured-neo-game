"""
network_client.py
Client-side networking for multiplayer
"""

import socketio
import requests
import threading
from typing import Callable, Optional

class NetworkClient:
    """Handles all network communication with server."""
    
    def __init__(self, server_url='http://localhost:5000'):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.token = None
        self.user_id = None
        self.username = None
        self.current_match_id = None
        
        # Callbacks
        self.on_connected = None
        self.on_match_found = None
        self.on_opponent_guess = None
        self.on_new_message = None
        self.on_user_online = None
        self.on_user_offline = None
        self.on_error = None
        self.on_game_start = None
        self.on_match_end = None
        
        self._setup_listeners()
    
    def _setup_listeners(self):
        """Setup WebSocket event listeners."""
        
        @self.sio.on('connect_response')
        def on_connect(data):
            print("✓ Connected to server")
        
        @self.sio.on('authenticated')
        def on_auth(data):
            self.user_id = data.get('user_id')
            if self.on_connected:
                self.on_connected(data)
        
        @self.sio.on('match_found')
        def on_match(data):
            self.current_match_id = data.get('match_id')
            print(f"✓ Match found! Match ID: {self.current_match_id}")
            if self.on_match_found:
                self.on_match_found(data)
        
        @self.sio.on('game_start')
        def on_game_start(data):
            print("✓ Game started!")
            if self.on_game_start:
                self.on_game_start(data)
        
        @self.sio.on('opponent_guess')
        def on_opp_guess(data):
            print(f"Opponent guessed: {data.get('guess')}")
            if self.on_opponent_guess:
                self.on_opponent_guess(data)
        
        @self.sio.on('match_end')
        def on_match_end(data):
            print(f"Match ended! Winner: {data.get('winner_id')}")
            if self.on_match_end:
                self.on_match_end(data)
        
        @self.sio.on('new_message')
        def on_msg(data):
            if self.on_new_message:
                self.on_new_message(data)
        
        @self.sio.on('user_online')
        def on_online(data):
            if self.on_user_online:
                self.on_user_online(data)
        
        @self.sio.on('user_offline')
        def on_offline(data):
            if self.on_user_offline:
                self.on_user_offline(data)
        
        @self.sio.on('error')
        def on_err(data):
            print(f"❌ Server error: {data}")
            if self.on_error:
                self.on_error(data)
    
    # ========== Authentication ==========
    
    def register(self, username: str, email: str, password: str) -> dict:
        """Register new account."""
        try:
            response = requests.post(
                f'{self.server_url}/api/auth/register',
                json={'username': username, 'email': email, 'password': password},
                timeout=5
            )
            data = response.json()
            
            if response.status_code == 201:
                self.token = data['token']
                self.username = username
                self.user_id = data['user']['id']
                return {'success': True, 'user': data['user']}
            else:
                return {'success': False, 'error': data.get('error', 'Registration failed')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def login(self, username: str, password: str) -> dict:
        """Login to account."""
        try:
            response = requests.post(
                f'{self.server_url}/api/auth/login',
                json={'username': username, 'password': password},
                timeout=5
            )
            data = response.json()
            
            if response.status_code == 200:
                self.token = data['token']
                self.username = username
                self.user_id = data['user']['id']
                self.connect()  # Connect to WebSocket after login
                return {'success': True, 'user': data['user']}
            else:
                return {'success': False, 'error': data.get('error', 'Login failed')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== Connection ==========
    
    def connect(self):
        """Connect to WebSocket server."""
        try:
            self.sio.connect(self.server_url, auth={'token': self.token})
            self.sio.emit('authenticate', {'token': self.token})
            print(f"✓ Authenticated as: {self.username}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from server."""
        if self.sio.connected:
            self.sio.disconnect()
            print("Disconnected from server")
    
    # ========== Leaderboard ==========
    
    def get_leaderboard(self, limit: int = 50) -> dict:
        """Get top players."""
        try:
            response = requests.get(
                f'{self.server_url}/api/leaderboard',
                params={'limit': limit},
                timeout=5
            )
            return {'success': True, 'leaderboard': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== Friends ==========
    
    def get_friends(self) -> dict:
        """Get friend list."""
        try:
            response = requests.get(
                f'{self.server_url}/api/friends',
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=5
            )
            return {'success': True, 'friends': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_friend(self, friend_id: int) -> dict:
        """Send friend request."""
        try:
            response = requests.post(
                f'{self.server_url}/api/friends/add/{friend_id}',
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=5
            )
            return {'success': response.status_code == 201}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def accept_friend(self, friend_id: int) -> dict:
        """Accept friend request."""
        try:
            response = requests.post(
                f'{self.server_url}/api/friends/accept/{friend_id}',
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=5
            )
            return {'success': response.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== Matchmaking ==========
    
    def join_matchmaking(self):
        """Join matchmaking queue."""
        print(f"Joining matchmaking queue...")
        self.sio.emit('join_matchmaking', {'user_id': self.user_id})
    
    def get_matches(self) -> dict:
        """Get match history."""
        try:
            response = requests.get(
                f'{self.server_url}/api/matches',
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=5
            )
            return {'success': True, 'matches': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== Gameplay ==========
    
    def set_secret(self, match_id: int, secret: str):
        """Set your secret code for a match."""
        print(f"Setting secret for match {match_id}")
        self.sio.emit('set_secret', {
            'match_id': match_id,
            'player_id': self.user_id,
            'secret': secret
        })
    
    def submit_guess(self, match_id: int, guess: str):
        """Submit a guess in match."""
        print(f"Submitting guess: {guess}")
        self.sio.emit('guess', {
            'match_id': match_id,
            'player_id': self.user_id,
            'guess': guess
        })
    
    def send_message(self, receiver_id: int, message: str, match_id: Optional[int] = None):
        """Send chat message."""
        self.sio.emit('send_message', {
            'sender_id': self.user_id,
            'receiver_id': receiver_id,
            'message': message,
            'match_id': match_id
        })
