"""
launcher.py
Unified launcher for Dead Injured Neo with automatic server startup
Handles server startup, port selection, and application launch
"""

import os
import sys
import subprocess
import time
import socket
import tkinter as tk
from tkinter import messagebox
import threading
from pathlib import Path

class DeadInjuredNeoLauncher:
    """Launcher that manages server and client application."""
    
    def __init__(self):
        self.server_process = None
        self.server_port = 5000
        self.server_running = False
        self.server_url = None
        
    def is_port_available(self, port):
        """Check if a port is available."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return True
        except OSError:
            return False
    
    def find_available_port(self, start_port=5000, max_attempts=10):
        """Find an available port."""
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port):
                return port
        return None
    
    def start_server(self):
        """Start the Flask server."""
        print("🚀 Starting Dead Injured Neo Server...")
        
        # Find available port
        self.server_port = self.find_available_port()
        if not self.server_port:
            print("❌ No available ports found!")
            return False
        
        self.server_url = f'http://localhost:{self.server_port}'
        
        # Check if server.py exists
        if not os.path.exists('server.py'):
            print("❌ server.py not found!")
            messagebox.showerror(
                "Server Error",
                "server.py not found.\n\n"
                "Make sure server.py is in the same folder as launcher.py"
            )
            return False
        
        try:
            # Start server process
            if sys.platform == 'win32':
                # Windows
                self.server_process = subprocess.Popen(
                    [sys.executable, 'server.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # macOS/Linux
                self.server_process = subprocess.Popen(
                    [sys.executable, 'server.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            print(f"✅ Server started on {self.server_url}")
            self.server_running = True
            
            # Wait for server to be ready
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            messagebox.showerror("Server Error", f"Failed to start server:\n{e}")
            return False
    
    def start_client(self):
        """Start the client application."""
        print("🎮 Starting Dead Injured Neo Client...")
        
        try:
            # Import and launch the GUI
            from dead_injured_neo import DeadInjuredNeoApp
            
            root = tk.Tk()
            app = DeadInjuredNeoApp(root)
            
            # Update server URL in network client
            if hasattr(app, 'network_client'):
                app.network_client.server_url = self.server_url
            
            print("✅ Client launched!")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Failed to start client: {e}")
            messagebox.showerror("Client Error", f"Failed to start client:\n{e}")
    
    def cleanup(self):
        """Clean up server process on exit."""
        if self.server_process:
            print("\n🛑 Shutting down server...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except Exception as e:
                print(f"Error stopping server: {e}")
                try:
                    self.server_process.kill()
                except:
                    pass
    
    def run(self):
        """Main launcher logic."""
        print("=" * 60)
        print("🎮 DEAD INJURED NEO - LAUNCHER")
        print("=" * 60)
        
        # Start server
        if not self.start_server():
            return
        
        # Start client
        try:
            self.start_client()
        finally:
            self.cleanup()
        
        print("\n✅ Goodbye!")
        sys.exit(0)


def main():
    """Entry point."""
    launcher = DeadInjuredNeoLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
