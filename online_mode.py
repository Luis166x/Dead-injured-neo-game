"""
online_mode.py
Online multiplayer GUI components with full registration/login and game flow
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network_client import NetworkClient
from utils import valid_code

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
        self.frame.configure(bg=BG)
        self.network = network_client
        self.current_match_id = None
        self.opponent_id = None
        self.opponent_username = None
        self.is_logged_in = False
        self.my_role = None  # 'player1' or 'player2'
        self.my_secret = None
        self.game_started = False
        
        try:
            self._build_ui()
            self._setup_network_callbacks()
        except Exception as e:
            print(f"Error in OnlineMode.__init__: {e}")
            self._build_error_ui(str(e))
    
    def _build_error_ui(self, error_msg):
        """Show error message if online mode fails to load."""
        error_frame = ttk.Frame(self.frame, style="Panel.TFrame")
        error_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        ttk.Label(
            error_frame,
            text="❌ Error Loading Online Mode",
            style="Header.TLabel"
        ).pack(pady=10)
        
        ttk.Label(
            error_frame,
            text=f"Error: {error_msg}",
            style="Dim.TLabel"
        ).pack(pady=5)
        
        ttk.Label(
            error_frame,
            text="Make sure:\n1. server.py is running\n2. All files are in the same folder\n3. Internet connection is working",
            style="Dim.TLabel",
            justify=tk.LEFT
        ).pack(pady=10)
    
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
        
        # Title
        ttk.Label(self.auth_frame, text="👤 ONLINE ACCOUNT", font=FONT_HEADER).pack(
            anchor="w", padx=12, pady=(12, 8)
        )
        
        # Form frame
        form_frame = ttk.Frame(self.auth_frame)
        form_frame.pack(fill=tk.X, padx=12, pady=8)
        
        # Username
        ttk.Label(form_frame, text="Username:").pack(side=tk.LEFT, padx=5)
        self.username_entry = ttk.Entry(form_frame, width=15)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        # Password
        ttk.Label(form_frame, text="Password:").pack(side=tk.LEFT, padx=5)
        self.password_entry = ttk.Entry(form_frame, width=15, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=5)
        
        # Email (for registration)
        ttk.Label(form_frame, text="Email:").pack(side=tk.LEFT, padx=5)
        self.email_entry = ttk.Entry(form_frame, width=15)
        self.email_entry.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.auth_frame)
        button_frame.pack(fill=tk.X, padx=12, pady=8)
        
        login_btn = ttk.Button(button_frame, text="Login", command=self._login)
        login_btn.pack(side=tk.LEFT, padx=4)
        
        register_btn = ttk.Button(button_frame, text="Register", command=self._register)
        register_btn.pack(side=tk.LEFT, padx=4)
        
        self.logout_btn = ttk.Button(button_frame, text="Logout", command=self._logout, state="disabled")
        self.logout_btn.pack(side=tk.LEFT, padx=4)
        
        # Status
        self.status_label = ttk.Label(
            self.auth_frame,
            text="❌ Not logged in",
            font=FONT_SMALL
        )
        self.status_label.pack(anchor="w", padx=12, pady=(0, 12))
    
    def _build_play_tab(self, notebook):
        """Build main play/matchmaking tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🎮 Play Online")
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Matchmaking section
        match_frame = ttk.Frame(frame, style="Panel.TFrame")
        match_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        match_frame.grid_columnconfigure(2, weight=1)
        
        ttk.Label(match_frame, text="🎯 Matchmaking", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=12
        )
        
        self.find_match_btn = ttk.Button(match_frame, text="Find Match", command=self._start_matchmaking)
        self.find_match_btn.grid(row=0, column=1, sticky="w", padx=12, pady=12)
        
        self.matchmaking_status = ttk.Label(match_frame, text="Ready", style="Dim.TLabel")
        self.matchmaking_status.grid(row=0, column=2, sticky="e", padx=12, pady=12)
        
        # Secret setup section
        secret_frame = ttk.Frame(frame, style="Panel.TFrame")
        secret_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=12)
        secret_frame.grid_remove()
        self.secret_frame = secret_frame
        
        ttk.Label(secret_frame, text="📌 Set Your Secret", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        
        ttk.Label(secret_frame, text="Enter your 4-digit secret code:", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", padx=12, pady=6
        )
        
        input_frame = ttk.Frame(secret_frame, style="Panel.TFrame")
        input_frame.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 12))
        
        self.secret_entry = ttk.Entry(input_frame, width=12, font=FONT_MONO)
        self.secret_entry.pack(side=tk.LEFT, padx=5)
        
        self.set_secret_btn = ttk.Button(input_frame, text="Set Secret", command=self._set_secret)
        self.set_secret_btn.pack(side=tk.LEFT, padx=5)
        
        self.secret_status = ttk.Label(secret_frame, text="Waiting for match...", style="Dim.TLabel")
        self.secret_status.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 12))
        
        # Game info section
        info_frame = ttk.Frame(frame, style="Panel.TFrame")
        info_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=12)
        info_frame.grid_remove()
        self.info_frame = info_frame
        
        ttk.Label(info_frame, text="📊 Match Info", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6)
        )
        
        ttk.Label(info_frame, text="Opponent:", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", padx=12, pady=6
        )
        self.opponent_label = ttk.Label(info_frame, text="", style="Dim.TLabel")
        self.opponent_label.grid(row=1, column=1, sticky="w", padx=12, pady=6)
        
        ttk.Label(info_frame, text="Match Status:", style="Body.TLabel").grid(
            row=2, column=0, sticky="w", padx=12, pady=6
        )
        self.match_status_label = ttk.Label(info_frame, text="", style="Dim.TLabel")
        self.match_status_label.grid(row=2, column=1, sticky="w", padx=12, pady=6)
        
        # Game section
        game_frame = ttk.Frame(frame, style="Panel.TFrame")
        game_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=12)
        game_frame.grid_rowconfigure(1, weight=1)
        game_frame.grid_columnconfigure(0, weight=1)
        game_frame.grid_remove()
        self.game_frame = game_frame
        
        ttk.Label(game_frame, text="🎮 Make Your Guess", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        
        # Game log
        self.game_log = scrolledtext.ScrolledText(
            game_frame, height=15, width=80, bg=PANEL_ALT, fg=TEXT, font=FONT_MONO
        )
        self.game_log.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        
        # Guess input
        guess_input_frame = ttk.Frame(game_frame, style="Panel.TFrame")
        guess_input_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        
        ttk.Label(guess_input_frame, text="Your guess:", style="Body.TLabel").pack(side=tk.LEFT, padx=5)
        
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
        
        ttk.Label(frame, text="🏆 Top Players", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=12
        )
        
        self.leaderboard_tree = ttk.Treeview(
            frame,
            columns=("rank", "username", "rating", "wins", "losses"),
            show="headings",
            height=25
        )
        self.leaderboard_tree.heading("rank", text="Rank")
        self.leaderboard_tree.heading("username", text="Player")
        self.leaderboard_tree.heading("rating", text="Rating")
        self.leaderboard_tree.heading("wins", text="Wins")
        self.leaderboard_tree.heading("losses", text="Losses")
        
        self.leaderboard_tree.column("rank", width=50)
        self.leaderboard_tree.column("username", width=150)
        self.leaderboard_tree.column("rating", width=100)
        self.leaderboard_tree.column("wins", width=80)
        self.leaderboard_tree.column("losses", width=80)
        
        self.leaderboard_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        
        refresh_btn = ttk.Button(frame, text="Refresh", command=self._refresh_leaderboard)
        refresh_btn.grid(row=2, column=0, sticky="w", padx=12, pady=12)
    
    def _build_friends_tab(self, notebook):
        """Build friends tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="👥 Friends")
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # Add friend section
        add_frame = ttk.Frame(frame, style="Panel.TFrame")
        add_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        
        ttk.Label(add_frame, text="Add Friend (by ID):", style="Header.TLabel").pack(side=tk.LEFT, padx=12)
        self.friend_id_entry = ttk.Entry(add_frame, width=10)
        self.friend_id_entry.pack(side=tk.LEFT, padx=5)
        
        add_btn = ttk.Button(add_frame, text="Send Request", command=self._add_friend)
        add_btn.pack(side=tk.LEFT, padx=4)
        
        # Friends list
        ttk.Label(frame, text="👥 Your Friends", style="Header.TLabel").grid(
            row=1, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        
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
        
        self.friends_tree.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
    
    def _setup_network_callbacks(self):
        """Setup network event callbacks."""
        if self.network:
            self.network.on_connected = self._on_connected
            self.network.on_match_found = self._on_match_found
            self.network.on_game_start = self._on_game_start
            self.network.on_opponent_guess = self._on_opponent_guess
            self.network.on_match_end = self._on_match_end
            self.network.on_error = self._on_error
    
    # ========== Auth ==========
    
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
                messagebox.showinfo(
                    "Success",
                    f"Account '{username}' created!\n\nYou can now login."
                )
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
        self.status_label.configure(text=f"✅ Logged in as: {self.network.username}", foreground=SUCCESS)
        self._refresh_leaderboard()
    
    def _show_auth(self):
        """Show auth panel."""
        self.auth_frame.grid()
        self.content_frame.grid_remove()
        self.logout_btn.configure(state="disabled")
        self.status_label.configure(text="❌ Not logged in", foreground=DANGER)
    
    # ========== Matchmaking ==========
    
    def _start_matchmaking(self):
        """Join matchmaking queue."""
        if not self.is_logged_in:
            messagebox.showinfo("Not Logged In", "Login first to play")
            return
        
        self.matchmaking_status.configure(text="🔄 Searching for opponent...")
        self.find_match_btn.configure(state="disabled")
        try:
            self.network.join_matchmaking()
        except Exception as e:
            messagebox.showerror("Error", f"Matchmaking failed: {str(e)}")
            self.find_match_btn.configure(state="normal")
            self.matchmaking_status.configure(text="Ready")
    
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
        
        # Show secret setup
        self.secret_frame.grid()
        self.info_frame.grid()
        self.secret_entry.focus_set()
    
    # ========== Game Setup ==========
    
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
        
        # Send to server
        self.network.set_secret(self.current_match_id, secret)
    
    def _on_game_start(self, data):
        """Handle game start."""
        self.game_started = True
        self.match_status_label.configure(text="✓ Game started!")
        
        # Hide setup, show game
        self.secret_frame.grid_remove()
        self.game_frame.grid()
        
        self.game_log.delete(1.0, tk.END)
        self.game_log.insert(tk.END, "🎮 GAME STARTED!\n")
        self.game_log.insert(tk.END, f"Opponent: {self.opponent_username}\n")
        self.game_log.insert(tk.END, "-" * 60 + "\n\n")
        self.game_log.insert(tk.END, "Make your first guess!\n")
        
        self.guess_entry.focus_set()
    
    # ========== Gameplay ==========
    
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
        winning_guess = data.get('winning_guess')
        guesses_taken = data.get('guesses_taken')
        
        if winner_id == self.network.user_id:
            msg = f"🎉 YOU WON!\n\nYou found the code in {guesses_taken} guess(es)!"
            color = SUCCESS
        else:
            msg = f"😢 YOU LOST!\n\nOpponent found your code!"
            color = DANGER
        
        self.game_log.insert(tk.END, f"\n{'='*60}\n")
        self.game_log.insert(tk.END, msg + "\n")
        self.game_log.see(tk.END)
        
        self.submit_guess_btn.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        
        messagebox.showinfo("Match Over", msg)
        
        # Reset for next match
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
    
    # ========== Leaderboard ==========
    
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
                            player.get('username', ''),
                            player.get('rating', 0),
                            player.get('wins', 0),
                            player.get('losses', 0)
                        ))
            except Exception as e:
                print(f"Error refreshing leaderboard: {e}")
        
        threading.Thread(target=fetch, daemon=True).start()
    
    # ========== Friends ==========
    
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
