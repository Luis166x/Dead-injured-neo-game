"""
dead_injured_neo.py
Modern dark-themed Tkinter GUI for Dead Injured Neo with online multiplayer.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import Game
from ai import AI
from history import GuessHistory
from helper import GuessingHelper
from trainer import TrainingSession
from network_client import NetworkClient
from online_mode import OnlineMode
from utils import valid_code, format_result

# ---------------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------------

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
BORDER      = "#2a2e3d"

FONT_TITLE  = ("Segoe UI Semibold", 18)
FONT_HEADER = ("Segoe UI Semibold", 12)
FONT_BODY   = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 11)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# SERVER_URL = 'http://192.168.1.11:5000'  # Local network
SERVER_URL = 'http://localhost:5000'        # Local machine (for testing)
# SERVER_URL = 'https://your-deployed-server.com'  # Production server

# ---------------------------------------------------------------------------
# Statistics tracker
# ---------------------------------------------------------------------------

class Statistics:
    """Tracks game statistics during the session."""

    def __init__(self):
        self.player_wins = 0
        self.ai_wins = 0
        self.games_played = 0
        self.total_player_turns = 0
        self.total_ai_turns = 0
        self.fastest_player_win = float('inf')
        self.fastest_ai_win = float('inf')

    def record_game(self, winner, player_turns, ai_turns):
        self.games_played += 1
        self.total_player_turns += player_turns
        self.total_ai_turns += ai_turns

        if winner == "PLAYER":
            self.player_wins += 1
            if player_turns < self.fastest_player_win:
                self.fastest_player_win = player_turns
        elif winner == "AI":
            self.ai_wins += 1
            if ai_turns < self.fastest_ai_win:
                self.fastest_ai_win = ai_turns

    def get_player_win_percentage(self):
        if self.games_played == 0:
            return 0.0
        return (self.player_wins / self.games_played) * 100

    def get_ai_win_percentage(self):
        if self.games_played == 0:
            return 0.0
        return (self.ai_wins / self.games_played) * 100

    def get_average_player_turns(self):
        if self.player_wins == 0:
            return 0.0
        return self.total_player_turns / self.player_wins

    def get_average_ai_turns(self):
        if self.ai_wins == 0:
            return 0.0
        return self.total_ai_turns / self.ai_wins

    def get_stats_summary(self):
        summary = f"Games: {self.games_played} | "
        summary += f"You: {self.player_wins}W ({self.get_player_win_percentage():.1f}%) | "
        summary += f"AI: {self.ai_wins}W ({self.get_ai_win_percentage():.1f}%)"
        return summary

# ---------------------------------------------------------------------------
# Main application with tabbed interface
# ---------------------------------------------------------------------------

class DeadInjuredNeoApp:
    """Main application with multiple game modes."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._configure_window()
        self._configure_style()

        # Backend state
        self.game = Game()
        self.ai = AI(difficulty="normal", personality="logical")
        self.player_history = GuessHistory()
        self.ai_history = GuessHistory()
        self.statistics = Statistics()
        
        self.helper = GuessingHelper()
        self.trainer = None
        
        # Network - Initialize with server URL
        self.network_client = NetworkClient(server_url=SERVER_URL)

        # UI state
        self.game_started = False
        self.current_difficulty = tk.StringVar(value="normal")
        self.current_personality = tk.StringVar(value="logical")

        self._build_ui()
        self._bind_events()
        self._refresh_status()

    def _configure_window(self):
        self.root.title("Dead Injured Neo - Online Edition")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 700)
        self.root.configure(bg=BG)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
        style.configure("Header.TLabel", background=PANEL, foreground=ACCENT, font=FONT_HEADER)
        style.configure("Body.TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
        style.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM, font=FONT_SMALL)
        style.configure("Status.TLabel", background=PANEL, foreground=TEXT, font=FONT_HEADER)
        style.configure("Secret.TLabel", background=PANEL, foreground=SUCCESS, font=FONT_MONO)
        style.configure("Stats.TLabel", background=BG, foreground=TEXT_DIM, font=FONT_SMALL)

        style.configure("TButton", background=ACCENT, foreground="#ffffff",
                        font=FONT_BODY, borderwidth=0, padding=8)
        style.map("TButton",
                  background=[("active", ACCENT_HOVER), ("disabled", "#3a3f52")],
                  foreground=[("disabled", "#6b7080")])

        style.configure("Secondary.TButton", background=PANEL_ALT, foreground=TEXT,
                         font=FONT_BODY, borderwidth=0, padding=8)
        style.map("Secondary.TButton",
                  background=[("active", BORDER), ("disabled", "#2a2e3d")],
                  foreground=[("disabled", "#6b7080")])

        style.configure("Treeview",
                        background=PANEL_ALT, fieldbackground=PANEL_ALT,
                        foreground=TEXT, rowheight=26, borderwidth=0, font=FONT_BODY)
        style.configure("Treeview.Heading",
                        background=PANEL, foreground=ACCENT,
                        font=FONT_HEADER, borderwidth=0, relief="flat")
        style.map("Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT,
                        insertcolor=TEXT, borderwidth=0, padding=6, font=FONT_MONO)

        style.configure("TCombobox", fieldbackground=PANEL_ALT, foreground=TEXT,
                        borderwidth=0, padding=4, font=FONT_BODY)

        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", padding=[20, 10])

    def _build_ui(self):
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        # Build tabs
        self._build_game_mode()
        self._build_helper_mode()
        self._build_trainer_mode()
        self._build_online_mode()

    def _build_game_mode(self):
        """Main game mode tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Game Mode")
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self._build_header(frame)
        self._build_settings(frame)
        self._build_controls(frame)
        self._build_history_panels(frame)
        self._build_stats_bar(frame)

    def _build_helper_mode(self):
        """Helper mode tab for guessing opponent's code."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Helper Mode")
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        title = ttk.Label(frame, text="Opponent Guessing Helper", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        input_panel = ttk.Frame(frame, style="Panel.TFrame")
        input_panel.grid(row=1, column=0, sticky="ew", padx=12, pady=12)

        ttk.Label(input_panel, text="Your last guess:", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )

        entry_frame = ttk.Frame(input_panel, style="Panel.TFrame")
        entry_frame.grid(row=0, column=1, sticky="w", padx=12, pady=(12, 6))

        self.helper_guess_entry = ttk.Entry(entry_frame, width=10)
        self.helper_guess_entry.grid(row=0, column=0, padx=(0, 8))

        ttk.Label(entry_frame, text="Dead:", style="Header.TLabel").grid(row=0, column=1)
        self.helper_dead_spin = ttk.Spinbox(entry_frame, from_=0, to=4, width=3)
        self.helper_dead_spin.set(0)
        self.helper_dead_spin.grid(row=0, column=2, padx=(4, 12))

        ttk.Label(entry_frame, text="Injured:", style="Header.TLabel").grid(row=0, column=3)
        self.helper_injured_spin = ttk.Spinbox(entry_frame, from_=0, to=4, width=3)
        self.helper_injured_spin.set(0)
        self.helper_injured_spin.grid(row=0, column=4, padx=4)

        submit_btn = ttk.Button(entry_frame, text="Submit", command=self._helper_submit)
        submit_btn.grid(row=0, column=5, padx=(12, 0))

        main_frame = ttk.Frame(frame, style="Panel.TFrame")
        main_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="Suggested Guesses", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        self.helper_suggestions_text = scrolledtext.ScrolledText(
            main_frame, height=20, width=50, bg=PANEL_ALT, fg=TEXT, font=FONT_MONO
        )
        self.helper_suggestions_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        ttk.Label(main_frame, text="Elimination Analysis", style="Header.TLabel").grid(
            row=0, column=1, sticky="w", padx=12, pady=(12, 6)
        )
        self.helper_analysis_text = scrolledtext.ScrolledText(
            main_frame, height=20, width=50, bg=PANEL_ALT, fg=TEXT, font=FONT_MONO
        )
        self.helper_analysis_text.grid(row=1, column=1, sticky="nsew", padx=12, pady=(0, 12))

        self.helper_status = ttk.Label(frame, text="Remaining: 5040 possibilities", style="Status.TLabel")
        self.helper_status.grid(row=3, column=0, sticky="ew", padx=12, pady=12)

        reset_btn = ttk.Button(frame, text="Reset Helper", style="Secondary.TButton", command=self._helper_reset)
        reset_btn.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 12))

    def _build_trainer_mode(self):
        """Training mode tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Training Mode")
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        title = ttk.Label(frame, text="Learning the Algorithm", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        control_panel = ttk.Frame(frame, style="Panel.TFrame")
        control_panel.grid(row=1, column=0, sticky="ew", padx=12, pady=12)
        control_panel.grid_columnconfigure(0, weight=1)

        ttk.Label(control_panel, text="Make a guess:", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=12
        )

        entry_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        entry_frame.grid(row=0, column=1, sticky="w", padx=12, pady=12)

        self.trainer_guess_entry = ttk.Entry(entry_frame, width=10)
        self.trainer_guess_entry.grid(row=0, column=0, padx=(0, 8))

        submit_btn = ttk.Button(entry_frame, text="Submit", command=self._trainer_submit)
        submit_btn.grid(row=0, column=1, padx=(0, 12))

        hint_btn = ttk.Button(entry_frame, text="Show Hint", style="Secondary.TButton", command=self._trainer_hint)
        hint_btn.grid(row=0, column=2, padx=(0, 12))

        reset_btn = ttk.Button(entry_frame, text="New Session", style="Secondary.TButton", command=self._trainer_reset)
        reset_btn.grid(row=0, column=3)

        main_frame = ttk.Frame(frame, style="Panel.TFrame")
        main_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        self.trainer_display = scrolledtext.ScrolledText(
            main_frame, bg=PANEL_ALT, fg=TEXT, font=FONT_BODY, wrap=tk.WORD
        )
        self.trainer_display.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.trainer_status = ttk.Label(frame, text="", style="Status.TLabel")
        self.trainer_status.grid(row=3, column=0, sticky="ew", padx=12, pady=12)

        self._trainer_init()

    def _build_online_mode(self):
        """Online multiplayer tab."""
        try:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text="🌐 Online")
            OnlineMode(frame, self.network_client)
        except Exception as e:
            print(f"Error loading online mode: {e}")

    # ---- Game Mode Methods ----

    def _build_header(self, parent):
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew")

        title = ttk.Label(header, text="Dead Injured Neo", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            header,
            text="Dead = correct digit & position   |   "
                 "Injured = correct digit, wrong position   |   "
                 "Neo = no correct digits",
            style="Dim.TLabel"
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 10))

    def _build_settings(self, parent):
        settings_panel = ttk.Frame(parent, style="Panel.TFrame")
        settings_panel.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(settings_panel, text="Difficulty:", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=12
        )
        difficulty_combo = ttk.Combobox(
            settings_panel,
            textvariable=self.current_difficulty,
            values=["easy", "normal", "hard", "insane"],
            state="readonly",
            width=12
        )
        difficulty_combo.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=12)

        ttk.Label(settings_panel, text="AI Personality:", style="Header.TLabel").grid(
            row=0, column=2, sticky="w", padx=12, pady=12
        )
        personality_combo = ttk.Combobox(
            settings_panel,
            textvariable=self.current_personality,
            values=["logical", "casual", "lucky", "detective", "neo"],
            state="readonly",
            width=12
        )
        personality_combo.grid(row=0, column=3, sticky="w", padx=(0, 12), pady=12)

    def _build_controls(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame")
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        left = ttk.Frame(panel, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        ttk.Label(left, text="Your Secret Code", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        self.secret_entry = ttk.Entry(left, width=10)
        self.secret_entry.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.start_button = ttk.Button(left, text="Start Game", command=self.start_game)
        self.start_button.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        center = ttk.Frame(panel, style="Panel.TFrame")
        center.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        ttk.Label(center, text="Your Guess", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        self.guess_entry = ttk.Entry(center, width=10)
        self.guess_entry.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.guess_entry.configure(state="disabled")

        self.submit_button = ttk.Button(
            center, text="Submit Guess", command=self.submit_guess, state="disabled"
        )
        self.submit_button.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        right = ttk.Frame(panel, style="Panel.TFrame")
        right.grid(row=0, column=2, sticky="nsew", padx=12, pady=12)

        self.restart_button = ttk.Button(
            right, text="Restart Game", style="Secondary.TButton",
            command=self.restart_game, state="disabled"
        )
        self.restart_button.grid(row=0, column=0, sticky="w")

        self.hint_button = ttk.Button(
            right, text="Advanced Hint", style="Secondary.TButton",
            command=self.show_hint, state="disabled"
        )
        self.hint_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.turn_label = ttk.Label(right, text="Turn: 0", style="Dim.TLabel")
        self.turn_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.status_label = ttk.Label(
            panel,
            text="Enter your secret code and press Start Game.",
            style="Status.TLabel",
            anchor="w"
        )
        self.status_label.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 12))

        self.reveal_frame = ttk.Frame(panel, style="Panel.TFrame")
        self.reveal_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))
        self.reveal_frame.grid_columnconfigure(0, weight=1)
        self.reveal_frame.grid_columnconfigure(1, weight=1)
        self.reveal_frame.grid_remove()

        self.player_secret_label = ttk.Label(
            self.reveal_frame, text="", style="Secret.TLabel", anchor="center"
        )
        self.player_secret_label.grid(row=0, column=0, sticky="ew", padx=6, pady=4)

        self.ai_secret_label = ttk.Label(
            self.reveal_frame, text="", style="Secret.TLabel", anchor="center"
        )
        self.ai_secret_label.grid(row=0, column=1, sticky="ew", padx=6, pady=4)

    def _build_history_panels(self, parent):
        player_panel = ttk.Frame(parent, style="Panel.TFrame")
        player_panel.grid(row=3, column=0, sticky="nsew", padx=(0, 6))
        player_panel.grid_rowconfigure(1, weight=1)

        ttk.Label(player_panel, text="Player History", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.player_tree = self._make_tree(player_panel)
        self.player_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))

        ai_panel = ttk.Frame(parent, style="Panel.TFrame")
        ai_panel.grid(row=3, column=1, sticky="nsew", padx=(6, 0))
        ai_panel.grid_rowconfigure(1, weight=1)

        ttk.Label(ai_panel, text="AI History", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.ai_tree = self._make_tree(ai_panel)
        self.ai_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))

    def _make_tree(self, parent):
        tree = ttk.Treeview(
            parent,
            columns=("guess", "dead", "injured", "neo"),
            show="headings",
            height=10
        )
        tree.heading("guess",   text="Guess")
        tree.heading("dead",    text="Dead")
        tree.heading("injured", text="Injured")
        tree.heading("neo",     text="Neo")

        tree.column("guess",   width=90,  anchor="center", stretch=True)
        tree.column("dead",    width=70,  anchor="center", stretch=True)
        tree.column("injured", width=90,  anchor="center", stretch=True)
        tree.column("neo",     width=70,  anchor="center", stretch=True)

        tree.tag_configure("odd",  background=PANEL_ALT)
        tree.tag_configure("even", background=PANEL)
        return tree

    def _build_stats_bar(self, parent):
        stats_bar = ttk.Frame(parent)
        stats_bar.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        stats_bar.grid_columnconfigure(0, weight=1)

        self.stats_label = ttk.Label(stats_bar, text="", style="Stats.TLabel")
        self.stats_label.grid(row=0, column=0, sticky="w")

    # ---- Game Mode Events ----

    def _bind_events(self):
        self.root.bind("<Return>", self._on_enter)

    def _on_enter(self, _event):
        if self.game_started and not self.game.is_game_over():
            self.submit_guess()
        elif not self.game_started:
            self.start_game()

    def start_game(self):
        secret = self.secret_entry.get().strip()

        if not valid_code(secret):
            messagebox.showerror(
                "Invalid Secret",
                "Your secret must be exactly 4 unique digits (0-9)."
            )
            return

        self.game.reset()
        self.ai = AI(
            difficulty=self.current_difficulty.get(),
            personality=self.current_personality.get()
        )
        self.player_history.clear()
        self.ai_history.clear()
        self._clear_trees()
        self.reveal_frame.grid_remove()

        self.game.set_player_secret(secret)
        self.game_started = True

        self.secret_entry.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.guess_entry.configure(state="normal")
        self.guess_entry.delete(0, tk.END)
        self.guess_entry.focus_set()
        self.submit_button.configure(state="normal")
        self.restart_button.configure(state="normal")
        self.hint_button.configure(state="normal")

        self._set_status(
            f"Game started. AI ({self.current_difficulty.get()}) has chosen its secret. Make your guess.",
            SUCCESS
        )
        self._refresh_status()

    def submit_guess(self):
        if not self.game_started:
            messagebox.showinfo("Start First", "Please start the game before guessing.")
            return

        if self.game.is_game_over():
            messagebox.showinfo("Game Over", "The game is over. Press Restart to play again.")
            return

        guess = self.guess_entry.get().strip()

        if not valid_code(guess):
            messagebox.showerror(
                "Invalid Guess",
                "Your guess must be exactly 4 unique digits (0-9)."
            )
            return

        try:
            dead, injured, neo = self.game.player_guess(guess)
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror("Error", str(exc))
            return

        self.player_history.add_guess(guess, dead, injured, neo)
        self._add_row(self.player_tree, self.player_history.last_guess(), "player")
        self.guess_entry.delete(0, tk.END)

        if self.game.is_game_over():
            self._end_game()
            return

        self._set_status("AI is thinking...", WARNING)
        self.root.update_idletasks()

        try:
            ai_guess = self.ai.make_guess()
            ai_dead, ai_injured, ai_neo = self.game.ai_guess(ai_guess)
            self.ai.update(ai_guess, ai_dead, ai_injured)
        except RuntimeError as exc:
            messagebox.showerror("AI Error", str(exc))
            return

        self.ai_history.add_guess(ai_guess, ai_dead, ai_injured, ai_neo)
        self._add_row(self.ai_tree, self.ai_history.last_guess(), "ai")

        if self.game.is_game_over():
            self._end_game()
            return

        self._set_status(
            f"Your guess {guess}: {format_result(dead, injured, neo)}   |   "
            f"AI guessed {ai_guess}: {format_result(ai_dead, ai_injured, ai_neo)}",
            TEXT
        )
        self._refresh_status()

    def _end_game(self):
        winner = self.game.winner()
        p_turns, a_turns = self.game.get_turn_counts()

        self.statistics.record_game(winner, p_turns, a_turns)

        if winner == "PLAYER":
            msg = (f"Congratulations! You won in {p_turns} turn(s)!\n\n"
                   f"AI's secret was: {self.game.get_ai_secret()}\n"
                   f"AI difficulty: {self.current_difficulty.get()}")
            color = SUCCESS
        elif winner == "AI":
            msg = (f"The AI won in {a_turns} turn(s)!\n\n"
                   f"AI's secret was: {self.game.get_ai_secret()}\n"
                   f"Your secret: {self.game.player_secret}")
            color = DANGER
        else:
            msg = "Game over."
            color = TEXT

        messagebox.showinfo("Game Over", msg)

        self.player_secret_label.configure(text=f"Your secret: {self.game.player_secret}")
        self.ai_secret_label.configure(text=f"AI secret:   {self.game.get_ai_secret()}")
        self.reveal_frame.grid()

        self._set_status(f"Game over — {winner} wins. Press Restart to play again.", color)

        self.guess_entry.configure(state="disabled")
        self.submit_button.configure(state="disabled")
        self.hint_button.configure(state="disabled")
        self._refresh_status()

    def restart_game(self):
        self.game.reset()
        self.ai.reset()
        self.player_history.clear()
        self.ai_history.clear()
        self._clear_trees()
        self.reveal_frame.grid_remove()
        self.player_secret_label.configure(text="")
        self.ai_secret_label.configure(text="")

        self.game_started = False

        self.secret_entry.configure(state="normal")
        self.secret_entry.delete(0, tk.END)
        self.start_button.configure(state="normal")
        self.guess_entry.configure(state="disabled")
        self.guess_entry.delete(0, tk.END)
        self.submit_button.configure(state="disabled")
        self.restart_button.configure(state="disabled")
        self.hint_button.configure(state="disabled")

        self._set_status("Enter your secret code and press Start Game.", TEXT)
        self._refresh_status()
        self.secret_entry.focus_set()

    def show_hint(self):
        """Shows advanced intelligent hints."""
        if not self.game_started or self.game.is_game_over():
            messagebox.showinfo("No Hint", "Start a game to receive hints.")
            return

        hints = self.ai.get_intelligent_hints()
        hint_text = "\n\n".join(hints)

        messagebox.showinfo("Advanced Hints", hint_text)

    # ---- Helper Mode Methods ----

    def _helper_submit(self):
        guess = self.helper_guess_entry.get().strip()
        
        if not valid_code(guess):
            messagebox.showerror("Invalid Guess", "Guess must be 4 unique digits.")
            return

        try:
            dead = int(self.helper_dead_spin.get())
            injured = int(self.helper_injured_spin.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Dead and Injured must be numbers.")
            return

        try:
            self.helper.add_feedback(guess, dead, injured)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        self.helper_guess_entry.delete(0, tk.END)
        self.helper_dead_spin.set(0)
        self.helper_injured_spin.set(0)

        self._helper_update_display()

    def _helper_update_display(self):
        self.helper_suggestions_text.delete(1.0, tk.END)
        suggestions = self.helper.get_top_suggestions(5)
        self.helper_suggestions_text.insert(tk.END, "Top Suggestions:\n\n")
        for i, sug in enumerate(suggestions, 1):
            self.helper_suggestions_text.insert(tk.END, f"{i}. {sug}\n")

        self.helper_analysis_text.delete(1.0, tk.END)
        if self.helper.get_history():
            self.helper_analysis_text.insert(tk.END, "Feedback History:\n\n")
            for record in self.helper.get_history():
                self.helper_analysis_text.insert(
                    tk.END,
                    f"Guess: {record['guess']} → Dead: {record['dead']}, Injured: {record['injured']}\n"
                )

        remaining = self.helper.get_remaining_count()
        self.helper_status.configure(text=f"Remaining: {remaining} possibilities")

    def _helper_reset(self):
        self.helper.reset()
        self.helper_guess_entry.delete(0, tk.END)
        self.helper_suggestions_text.delete(1.0, tk.END)
        self.helper_analysis_text.delete(1.0, tk.END)
        self.helper_status.configure(text="Remaining: 5040 possibilities")

    # ---- Trainer Mode Methods ----

    def _trainer_init(self):
        self.trainer = TrainingSession()
        self._trainer_update_display()

    def _trainer_submit(self):
        guess = self.trainer_guess_entry.get().strip()
        
        if not valid_code(guess):
            messagebox.showerror("Invalid Guess", "Guess must be 4 unique digits.")
            return

        result, error = self.trainer.submit_guess(guess)
        if error:
            messagebox.showerror("Error", error)
            return

        self.trainer_guess_entry.delete(0, tk.END)
        self._trainer_update_display()

        if self.trainer.is_solved():
            messagebox.showinfo(
                "Solved!",
                f"You found it! The secret was: {self.trainer.secret}\n\n"
                f"It took {len(self.trainer.guess_history)} guess(es).\n\n"
                "Click 'New Session' to try again."
            )

    def _trainer_hint(self):
        hint = self.trainer.get_training_hint()
        messagebox.showinfo("Training Hint", hint)

    def _trainer_reset(self):
        self._trainer_init()

    def _trainer_update_display(self):
        self.trainer_display.delete(1.0, tk.END)

        text = "📚 TRAINING MODE - Learn the Elimination Algorithm\n"
        text += "=" * 60 + "\n\n"

        if self.trainer.current_step == 0:
            text += "🎯 Goal: Find the secret code in as few guesses as possible.\n\n"
            text += "The AI uses elimination logic:\n"
            text += "  1. Make a guess\n"
            text += "  2. Get feedback (Dead, Injured, Neo)\n"
            text += "  3. Eliminate impossible codes\n"
            text += "  4. Repeat until solved!\n\n"
            text += "Try your first guess (e.g., 0123):\n"

        history = self.trainer.guess_history
        if history:
            text += "Guess History:\n"
            text += "-" * 60 + "\n"
            for i, record in enumerate(history, 1):
                text += f"{i}. Guess: {record['guess']} → "
                text += f"Dead: {record['dead']}, Injured: {record['injured']}\n"

        text += "\n" + "-" * 60 + "\n"
        text += f"Possibilities remaining: {len(self.trainer.possible_codes)}\n\n"

        if len(self.trainer.possible_codes) > 1:
            text += "How to narrow down:\n"
            test_guess = self.trainer.possible_codes[0]
            breakdown, _ = self.trainer.get_elimination_breakdown(test_guess)
            text += f"\nIf you guess '{test_guess}':\n"
            for item in breakdown[:5]:
                text += f"  • {item['feedback']}: {item['count']} codes ({item['percentage']:.1f}%)\n"

        self.trainer_display.insert(tk.END, text)

    # ---- Helper Methods ----

    def _add_row(self, tree, record, owner):
        neo_text = "Yes" if record["neo"] else "No"
        tag = "odd" if len(tree.get_children()) % 2 else "even"
        tree.insert(
            "", "end",
            values=(record["guess"], record["dead"], record["injured"], neo_text),
            tags=(tag,)
        )
        tree.see(tree.get_children()[-1])

    def _clear_trees(self):
        self.player_tree.delete(*self.player_tree.get_children())
        self.ai_tree.delete(*self.ai_tree.get_children())

    def _set_status(self, text, color=TEXT):
        self.status_label.configure(text=text, foreground=color)

    def _refresh_status(self):
        p_turns, a_turns = self.game.get_turn_counts()
        self.turn_label.configure(
            text=f"Turn — You: {p_turns}   AI: {a_turns}   "
                 f"|   AI possibilities: {self.ai.remaining_possibilities()}"
        )
        self.stats_label.configure(text=self.statistics.get_stats_summary())

def launch():
    """Entry point used by main.py."""
    root = tk.Tk()
    DeadInjuredNeoApp(root)
    root.mainloop()
