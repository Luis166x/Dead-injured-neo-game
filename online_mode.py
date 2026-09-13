"""
online_mode.py
Online multiplayer GUI components with full registration/login and game flow
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from network_client import NetworkClient
    from utils import valid_code
except ImportError as e:
    print(f"Import error in online_mode: {e}")

# Theme colors
BG          = "#0f1117"
PANEL       = "#1a1d29"
PANEL_ALT   = "#232736"
ACCENT      = "#4f8cff"
ACCENT_HOVER= "#3a78f0"
SUCCESS     = "#2ecc71"
WARNING     = "#f1c40f"
DANGER      = "#e74c3c"
TEXT        = "#e8eaf0"
TEXT_DIM    = "#9aa0b5"

FONT_HEADER = ("Segoe UI Semibold", 12)
FONT_BODY   = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 11)


class OnlineMode:
    """Online multiplayer interface with complete game flow."""
    
    def __init__(self, parent_frame, network_client):
        self.frame = parent_frame
        self.network = network_client
        self.current_match_id = None
        self.opponent_id = None
        self.opponent_username = None
        self.is_logged_in = False
        self.my_role = None
        self.my_secret = None
        self.game_started = False
        
        try:
            self._build_ui()
            self._setup_network_callbacks()
        except Exception as e:
            print(f"Error in OnlineMode: {e}")
            import traceback
            traceback.print_exc()
            self._build_error_ui(str(e))
    
    def _build_error_ui(self, error_msg):
        """Show error message if online mode fails to load."""
        error_frame = ttk.Frame(self.frame)
        error_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        error_label = ttk.Label(error_frame, text="❌ Error Loading Online Mode")
        error_label.pack(pady=10)
        
        error_detail = ttk.Label(error_frame, text=f"Error: {error_msg}")
        error_detail.pack(pady=5)
        
        info_label = ttk.Label(
            error_frame,
            text="Make sure:\n1. server.py is running\n2. All files are in the same folder\n3. Internet connection is working"
        )
        info_label.pack(pady=10)
    
    def _build_ui(self):
        """Build online mode UI."""
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Auth section
        self._build_auth_panel()
        
        # Main content (shown after login)
        self.content_frame = ttk.Frame(self.frame)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_remove()
        
        notebook = ttk.Notebook(self.content_frame)
        notebook.grid(row=0, column=0, sticky="nsew")
        
        # Play tab
        self._build_play_tab(notebook)
        
        # Leaderboard tab
        self._build_leaderboard_tab(notebook)
        
        # Friends tab
        self._build_friends_tab(notebook)
    
    def _build_auth_panel(self):
        """Build login/register panel."""
        self.auth_frame = ttk.Frame(self.frame)
        self.auth_frame.grid(row=0, column=0, sticky="ew", pady=12, padx=12)
        
        title_label = ttk.Label(self.auth_frame, text="👤 ONLINE ACCOUNT", font=FONT_HEADER)
        title_label.pack(anchor="w", padx=12, pady=(12, 8))
        
        form_frame = ttk.Frame(self.auth_frame)
        form_frame.pack(fill=tk.X, padx=12, pady=8)
        
        ttk.Label(form_frame, text="Username:").pack(side=tk.LEFT, padx=5)
        self.username_entry = ttk.Entry(form_frame, width=15)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(form_frame, text="Password:").pack(side=tk.LEFT, padx=5)
        self.password_entry = ttk.Entry(form_frame, width=15, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(form_frame, text="Email:").pack(side=tk.LEFT, padx=5)
        self.email_entry = ttk.Entry(form_frame, width=15)
        self.email_entry.pack(side=tk.LEFT, padx=5)
        
        button_frame = ttk.Frame(self.auth_frame)
        button_frame.pack(fill=tk.X, padx=12, pady=8)
        
        login_btn = ttk.Button(button_frame, text="Login", command=self._login)
        login_btn.pack(side=tk.LEFT, padx=4)
        
        register_btn = ttk.Button(button_frame, text="Register", command=self._register)
        register_btn.pack(side=tk.LEFT, padx=4)
        
        self.logout_btn = ttk.Button(button_frame, text="Logout", command=self._logout, state="disabled")
        self.logout_btn.pack(side=tk.LEFT, padx=4)
        
        self.status_label = ttk.Label(self.auth_frame, text="❌ Not logged in", font=FONT_SMALL)
        self.status_label.pack(anchor="w", padx=12, pady=(0, 12))
    
    def _build_play_tab(self, notebook):
        """Build main play/matchmaking tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🎮 Play Online")
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Matchmaking section
        match_frame = ttk.Frame(frame)
        match_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        match_frame.grid_columnconfigure(2, weight=1)
        
        match_label = ttk.Label(match_frame, text="🎯 Matchmaking", font=FONT_HEADER)
        match_label.grid(row=0, column=0, sticky="w", padx=12, pady=12)
        
        self.find_match_btn = ttk.Button(match_frame, text="Find Match", command=self._start_matchmaking)
        self.find_match_btn.grid(row=0, column=1, sticky="w", padx=12, pady=12)
        
        self.matchmaking_status = ttk.Label(match_frame, text="Ready", font=FONT_SMALL)
        self.matchmaking_status.grid(row=0, column=2, sticky="e", padx=12, pady=12)
        
        # Secret setup section
        secret_frame = ttk.Frame(frame)
        secret_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=12)
        secret_frame.grid_remove()
        self.secret_frame = secret_frame
        
        secret_label = ttk.Label(secret_frame, text="📌 Set Your Secret", font=FONT_HEADER)
        secret_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        
        secret_inst = ttk.Label(secret_frame, text="Enter your 4-digit secret code:", font=FONT_BODY)
        secret_inst.grid(row=1, column=0, sticky="w", padx=12, pady=6)
        
        input_frame = ttk.Frame(secret_frame)
        input_frame.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 12))
        
        self.secret_entry = ttk.Entry(input_frame, width=12, font=FONT_MONO)
        self.secret_entry.pack(side=tk.LEFT, padx=5)
        
        self.set_secret_btn = ttk.Button(input_frame, text="Set Secret", command=self._set_secret)
        self.set_secret_btn.pack(side=tk.LEFT, padx=5)
        
        self.secret_status = ttk.Label(secret_frame, text="Waiting for match...", font=FONT_SMALL)
        self.secret_status.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 12))
        
        # Game info section
        info_frame = ttk.Frame(frame)
        info_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=12)
        info_frame.grid_remove()
        self.info_frame = info_frame
        
        info_label = ttk.Label(info_frame, text="📊 Match Info", font=FONT_HEADER)
        info_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))
        
        opp_label = ttk.Label(info_frame, text="Opponent:", font=FONT_BODY)
        opp_label.grid(row=1, column=0, sticky="w", padx=12, pady=6)
        self.opponent_label = ttk.Label(info_frame, text="", font=FONT_SMALL)
        self.opponent_label.grid(row=1, column=1, sticky="w", padx=12, pady=6)
        
        match_status_lbl = ttk.Label(info_frame, text="Match Status:", font=FONT_BODY)
        match_status_lbl.grid(row=2, column=0, sticky="w", padx=12, pady=6)
        self.match_status_label = ttk.Label(info_frame, text="", font=FONT_SMALL)
        self.match_status_label.grid(row=2, column=1, sticky="w", padx=12, pady=6)
        
        # Game section - use plain tk.Frame instead of styled panel
        game_frame = ttk.Frame(frame)
        game_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=12)
        game_frame.grid_rowconfigure(1, weight=1)
        game_frame.grid_columnconfigure(0, weight=1)
        game_frame.grid_remove()
        self.game_frame = game_frame
        
        game_label = ttk.Label(game_frame, text="🎮 Make Your Guess", font=FONT_HEADER)
        game_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        
        # Game log - plain tk.Text widget
        self.game_log = tk.Text(game_frame, height=15, width=80)
        self.game_log.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        
        # Guess input
        guess_input_frame = ttk.Frame(game_frame)
        guess_input_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        
        guess_lbl = ttk.Label(guess_input_frame, text="Your guess:", font=FONT_BODY)
        guess_lbl.pack(side=tk.LEFT, padx=5)
        
        self.guess_entry = ttk.Entry(guess_input_frame, width=12, font=FONT_MONO)
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        
        self.submit_guess_btn = ttk.Button(guess_input_frame, text="Submit", command=self._submit_guess)
        self.submit_guess_btn.pack(side=tk.LEFT, padx=5)
    
    def _build_leaderboard_tab(self, notebook):
        """Build leaderboard tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🏆 Leaderboard")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        lb_label = ttk.Label(frame, text="🏆 Top Players", font=FONT_HEADER)
        lb_label.grid(row=0, column=0, sticky="w", padx=12, pady=12)
        
        self.leaderboard_tree = ttk.Treeview(
            frame,
            columns=("rank", "id", "username", "rating", "wins", "losses"),
            show="headings",
            height=25
        )
        self.leaderboard_tree.heading("rank", text="Rank")
        self.leaderboard_tree.heading("id", text="ID")
        self.leaderboard_tree.heading("username", text="Player")
        self.leaderboard_tree.heading("rating", text="Rating")
        self.leaderboard_tree.heading("wins", text="Wins")
        self.leaderboard_tree.heading("losses", text="Losses")
        
        self.leaderboard_tree.column("rank", width=50)
        self.leaderboard_tree.column("id", width=50)
        self.leaderboard_tree.column("username", width=120)
        self.leaderboard_tree.column("rating", width=80)
        self.leaderboard_tree.column("wins", width=70)
        self.leaderboard_tree.column("losses", width=70)
        
        self.leaderboard_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        
        refresh_btn = ttk.Button(frame, text="Refresh", command=self._refresh_leaderboard)
        refresh_btn.grid(row=2, column=0, sticky="w", padx=12, pady=12)
    
    def _build_friends_tab(self, notebook):
        """Build friends tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="👥 Friends")
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # User info section
        info_frame = ttk.Frame(frame)
        info_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        
        info_label = ttk.Label(info_frame, text="👤 Your Info", font=FONT_HEADER)
        info_label.pack(side=tk.LEFT, padx=12)
        
        self.my_info_label = ttk.Label(info_frame, text="", font=FONT_SMALL)
        self.my_info_label.pack(side=tk.LEFT, padx=12)
        
        copy_btn = ttk.Button(info_frame, text="Copy Your ID", command=self._copy_my_id)
        copy_btn.pack(side=tk.LEFT, padx=4)
        
        # Add friend section
        add_frame = ttk.Frame(frame)
        add_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=12)
        
        add_label = ttk.Label(add_frame, text="Add Friend (by ID):", font=FONT_HEADER)
        add_label.pack(side=tk.LEFT, padx=12)
        self.friend_id_entry = ttk.Entry(add_frame, width=10)
        self.friend_id_entry.pack(side=tk.LEFT, padx=5)
        
        add_btn = ttk.Button(add_frame, text="Send Request", command=self._add_friend)
        add_btn.pack(side=tk.LEFT, padx=4)
        
        # Friends list
        friends_label = ttk.Label(frame, text="👥 Your Friends", font=FONT_HEADER)
        friends_label.grid(row=2, column=0, sticky="w", padx=12, pady=(12, 6))
        
        self.friends_tree = ttk.Treeview(
            frame,
            columns=("id", "username", "rating"),
            show="headings",
            height=15
        )
        self.friends_tree.heading("id", text="ID")
        self.friends_tree.heading("username", text="Friend")
        self.friends_tree.heading("rating", text="Rating")
        
        self.friends_tree.column("id", width=50)
        self.friends_tree.column("username", width=150)
        self.friends_tree.column("rating", width=100)
        
        self.friends_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
    
    def _setup_network_callbacks(self):
        """Setup network event callbacks."""
        if self.network:
            self.network.on_connected = self._on_connected
            self.network.on_match_found = self._on_match_found
            self.network.on_game_start = self._on_game_start
            self.network.on_opponent_guess = self._on_opponent_guess
            self.network.on_match_end = self._on_match_end
            self.network.on_error = self._on_error
    
    def _login(self):
        """Login to server."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Enter username and password")
            return
        
        try:
            result = self.network.login(username, password)
            
            if result['success']:
                messagebox.showinfo("Success", f"Welcome {username}!")
                self._show_online_content()
                self.is_logged_in = True
            else:
                messagebox.showerror("Login Failed", result.get('error', 'Unknown error'))
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}\n\nMake sure server.py is running!")
    
    def _register(self):
        """Register new account."""
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not all([username, email, password]):
            messagebox.showerror("Error", "Fill all fields")
            return
        
        if len(username) < 3:
            messagebox.showerror("Error", "Username must be 3+ characters")
            return
        
        if len(password) < 4:
            messagebox.showerror("Error", "Password must be 4+ characters")
            return
        
        try:
            result = self.network.register(username, email, password)
            
            if result['success']:
                user_id = result['user']['id']
                messagebox.showinfo("Success", f"Account '{username}' created!\n\nYour ID: {user_id}\n\nYou can now login.")
                self._show_online_content()
                self.is_logged_in = True
            else:
                messagebox.showerror("Registration Failed", result.get('error', 'Unknown error'))
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}\n\nMake sure server.py is running!")
    
    def _logout(self):
        """Logout from server."""
        try:
            self.network.disconnect()
        except:
            pass
        
        self.network.token = None
        self.network.user_id = None
        self.is_logged_in = False
        self._show_auth()
        messagebox.showinfo("Logged Out", "You've been logged out")
    
    def _show_online_content(self):
        """Show online content after login."""
        self.auth_frame.grid_remove()
        self.content_frame.grid()
        self.logout_btn.configure(state="normal")
        self.status_label.configure(text=f"✅ Logged in as: {self.network.username} (ID: {self.network.user_id})")
        self.my_info_label.configure(text=f"Username: {self.network.username} | ID: {self.network.user_id}")
        self._refresh_leaderboard()
    
    def _show_auth(self):
        """Show auth panel."""
        self.auth_frame.grid()
        self.content_frame.grid_remove()
        self.logout_btn.configure(state="disabled")
        self.status_label.configure(text="❌ Not logged in")
    
    def _copy_my_id(self):
        """Copy user ID to clipboard."""
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(str(self.network.user_id))
            messagebox.showinfo("Copied", f"Your ID ({self.network.user_id}) has been copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {e}")
    
    def _start_matchmaking(self):
        """Join matchmaking queue."""
        if not self.is_logged_in:
            messagebox.showinfo("Not Logged In", "Login first to play")
            return
        
        self.matchmaking_status.configure(text="🔄 Searching for opponent...")
        self.find_match_btn.configure(state="disabled")
        
        def search():
            try:
                self.network.join_matchmaking()
                # Wait for match to be found
                for i in range(60):  # Wait up to 60 seconds
                    if self.current_match_id:
                        return
                    self.frame.after(1000)
                
                # If no match found after 60 seconds
                self.matchmaking_status.configure(text="❌ No opponent found (timeout)")
                self.find_match_btn.configure(state="normal")
            except Exception as e:
                messagebox.showerror("Error", f"Matchmaking failed: {str(e)}")
                self.find_match_btn.configure(state="normal")
                self.matchmaking_status.configure(text="Ready")
        
        threading.Thread(target=search, daemon=True).start()
    
    def _on_match_found(self, data):
        """Handle match found."""
        self.current_match_id = data.get('match_id')
        self.opponent_id = data.get('opponent_id')
        self.opponent_username = data.get('opponent_username')
        self.my_role = data.get('you_are')
        
        print(f"✓ Match found! You are {self.my_role}")
        
        self.matchmaking_status.configure(text=f"✓ Found opponent: {self.opponent_username}")
        self.opponent_label.configure(text=self.opponent_username)
        self.match_status_label.configure(text="Waiting for secrets...")
        
        self.secret_frame.grid()
        self.info_frame.grid()
        self.secret_entry.focus_set()
    
    def _set_secret(self):
        """Set your secret code."""
        secret = self.secret_entry.get().strip()
        
        if not valid_code(secret):
            messagebox.showerror("Invalid", "Secret must be 4 unique digits (0-9)")
            return
        
        self.my_secret = secret
        self.secret_entry.configure(state="disabled")
        self.set_secret_btn.configure(state="disabled")
        self.secret_status.configure(text="✓ Secret set! Waiting for opponent...")
        
        self.network.set_secret(self.current_match_id, secret)
    
    def _on_game_start(self, data):
        """Handle game start."""
        self.game_started = True
        self.match_status_label.configure(text="✓ Game started!")
        
        self.secret_frame.grid_remove()
        self.game_frame.grid()
        
        self.game_log.delete(1.0, tk.END)
        self.game_log.insert(tk.END, "🎮 GAME STARTED!\n")
        self.game_log.insert(tk.END, f"Opponent: {self.opponent_username}\n")
        self.game_log.insert(tk.END, "-" * 60 + "\n\n")
        self.game_log.insert(tk.END, "Make your first guess!\n")
        
        self.guess_entry.focus_set()
    
    def _submit_guess(self):
        """Submit guess in match."""
        if not self.game_started:
            messagebox.showinfo("No Match", "Wait for game to start")
            return
        
        guess = self.guess_entry.get().strip()
        
        if not valid_code(guess):
            messagebox.showerror("Invalid", "Must be 4 unique digits (0-9)")
            return
        
        try:
            self.network.submit_guess(self.current_match_id, guess)
            self.game_log.insert(tk.END, f"\n📤 You guessed: {guess}\n")
            self.game_log.see(tk.END)
            self.guess_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _on_opponent_guess(self, data):
        """Handle opponent guess."""
        guess = data.get('guess')
        dead = data.get('dead', 0)
        injured = data.get('injured', 0)
        
        self.game_log.insert(tk.END, f"📥 Opponent guessed: {guess}\n")
        self.game_log.insert(tk.END, f"   → Dead: {dead}, Injured: {injured}\n")
        self.game_log.see(tk.END)
    
    def _on_match_end(self, data):
        """Handle match end."""
        winner_id = data.get('winner_id')
        guesses_taken = data.get('guesses_taken')
        
        if winner_id == self.network.user_id:
            msg = f"🎉 YOU WON!\n\nYou found the code in {guesses_taken} guess(es)!"
        else:
            msg = f"😢 YOU LOST!\n\nOpponent found your code!"
        
        self.game_log.insert(tk.END, f"\n{'='*60}\n")
        self.game_log.insert(tk.END, msg + "\n")
        self.game_log.see(tk.END)
        
        self.submit_guess_btn.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        
        messagebox.showinfo("Match Over", msg)
        
        self._reset_game()
    
    def _reset_game(self):
        """Reset game state for new match."""
        self.game_started = False
        self.current_match_id = None
        self.opponent_id = None
        self.my_secret = None
        
        self.game_frame.grid_remove()
        self.secret_frame.grid_remove()
        self.info_frame.grid_remove()
        
        self.secret_entry.configure(state="normal")
        self.set_secret_btn.configure(state="normal")
        self.submit_guess_btn.configure(state="normal")
        self.guess_entry.configure(state="normal")
        self.find_match_btn.configure(state="normal")
        
        self.matchmaking_status.configure(text="Ready")
        self.secret_entry.delete(0, tk.END)
        self.guess_entry.delete(0, tk.END)
    
    def _on_error(self, data):
        """Handle server error."""
        error_msg = data.get('message', 'Unknown error')
        print(f"Server error: {error_msg}")
        messagebox.showerror("Server Error", error_msg)
    
    def _on_connected(self, data):
        """Handle connected event."""
        print(f"Connected to server: {data}")
    
    def _refresh_leaderboard(self):
        """Refresh leaderboard."""
        def fetch():
            try:
                result = self.network.get_leaderboard()
                if result['success']:
                    for item in self.leaderboard_tree.get_children():
                        self.leaderboard_tree.delete(item)
                    
                    for player in result['leaderboard']:
                        self.leaderboard_tree.insert('', 'end', values=(
                            player.get('rank', ''),
                            player.get('id', ''),
                            player.get('username', ''),
                            player.get('rating', 0),
                            player.get('wins', 0),
                            player.get('losses', 0)
                        ))
            except Exception as e:
                print(f"Error refreshing leaderboard: {e}")
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def _add_friend(self):
        """Add friend."""
        friend_id_str = self.friend_id_entry.get().strip()
        
        if not friend_id_str:
            messagebox.showerror("Error", "Enter friend ID")
            return
        
        try:
            friend_id = int(friend_id_str)
            result = self.network.add_friend(friend_id)
            
            if result['success']:
                messagebox.showinfo("Success", "Friend request sent!")
                self.friend_id_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to add friend")
        except ValueError:
            messagebox.showerror("Error", "Invalid ID")
        except Exception as e:
            messagebox.showerror("Error", str(e))
