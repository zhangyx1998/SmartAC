"""
Console module for vision application.
Provides interactive terminal commands in a separate thread.
"""

import sys
import threading
import json
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional, Callable


class Console:
    def __init__(self):
        self.current_input = ""
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # Configuration
        self.server_url = ""

        # Domain storage: name -> (x1, y1, x2, y2) in normalized coordinates (0.0-1.0)
        self.domains: Dict[str, Tuple[float, float, float, float]] = {}

        # Prompt state - False when executing command (to prevent double prompt)
        self.has_prompt = True

        # Mouse selection state
        self.mouse_selection_pending = False
        self.mouse_selection_domain = ""
        self.mouse_down_pos = None
        self.mouse_up_pos = None

        # Command handlers
        self.commands = {
            "help": self.cmd_help,
            "server": self.cmd_server,
            "domain": self.cmd_domain,
        }

    def log(self, message: str):
        """Print log message while preserving the interactive prompt."""
        with self.lock:
            # Erase current line (prompt + input)
            total_chars = 2 + len(self.current_input)  # "> " + input
            sys.stdout.write(
                "\b" * total_chars + " " * total_chars + "\b" * total_chars
            )
            sys.stdout.flush()

            # Print the log message
            print(message)

            # Restore prompt only if we're not executing a blocking command
            # The prompt will be restored by the command execution flow
            if self.has_prompt:
                sys.stdout.write(f"> {self.current_input}")
                sys.stdout.flush()

    def start(self):
        """Start the console thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._console_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the console thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _console_loop(self):
        """Main console loop running in separate thread."""
        print("\n=== Vision Console ===")
        print("Type 'help' for available commands")
        sys.stdout.write("> ")
        sys.stdout.flush()

        while self.running:
            try:
                # Read one character at a time
                import select
                import termios
                import tty

                # Save terminal settings
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())

                    # Check if input is available (with timeout)
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.1)

                    if rlist:
                        c = sys.stdin.read(1)
                        command: str | None = None
                        with self.lock:
                            if c == "\n" or c == "\r":
                                if self.current_input:
                                    print()  # New line after input
                                    command = self.current_input.strip()
                                    self.current_input = ""
                            elif c == "\x7f" or c == "\b":  # Backspace
                                if self.current_input:
                                    self.current_input = self.current_input[:-1]
                                    sys.stdout.write("\b \b")
                                    sys.stdout.flush()
                            elif c == "\x03":  # Ctrl+C
                                print("^C")
                                self.current_input = ""
                                sys.stdout.write("> ")
                                sys.stdout.flush()
                            elif c.isprintable():
                                self.current_input += c
                                sys.stdout.write(c)
                                sys.stdout.flush()
                        if command is not None:
                            self.has_prompt = False
                            self._execute_command(command)
                            self.has_prompt = True
                            sys.stdout.write("> ")
                            sys.stdout.flush()
                finally:
                    # Restore terminal settings
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

            except Exception as e:
                self.log(f"Console error: {e}")
                break

    def _execute_command(self, cmd_line: str):
        """Parse and execute a command."""
        if not cmd_line:
            return

        parts = cmd_line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in self.commands:
            try:
                self.commands[cmd](args)
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")

    def cmd_help(self, args: str):
        """Show help message."""
        print("Available commands:")
        print("  help                     - Show this help message")
        print("  server [url]             - Get/set server URL")
        print("  domain list              - List all domains and their coordinates")
        print("  domain add <name>        - Add domain (use mouse to select region)")
        print("  domain del <name>        - Delete domain by name")
        print("  domain clear             - Delete all domains")
        print("  domain save <path>       - Save domains to JSON or YAML file")
        print("  domain load <path>       - Load domains from JSON or YAML file")

    def cmd_server(self, args: str):
        """Get or set server URL."""
        args = args.strip()
        if args:
            self.server_url = args
            print(f"Server URL set to: {args}")
        else:
            if self.server_url:
                print(f"Current server URL: {self.server_url}")
            else:
                print("Server URL not set")

    def cmd_domain(self, args: str):
        """Handle domain subcommands."""
        parts = args.split(None, 1)
        if not parts:
            print(
                "Error: domain requires a subcommand (list, add, del, clear, save, load)"
            )
            return

        subcmd = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""

        if subcmd == "list":
            self._domain_list()
        elif subcmd == "add":
            self._domain_add(subargs)
        elif subcmd == "del":
            self._domain_del(subargs)
        elif subcmd == "clear":
            self._domain_clear()
        elif subcmd == "save":
            self._domain_save(subargs)
        elif subcmd == "load":
            self._domain_load(subargs)
        else:
            print(f"Error: unknown domain subcommand: {subcmd}")

    def _domain_list(self):
        """List all domains."""
        if not self.domains:
            print("No domains defined")
            return

        print(f"Domains ({len(self.domains)}) [normalized coordinates 0.0-1.0]:")
        for name, (x1, y1, x2, y2) in sorted(self.domains.items()):
            print(f"  {name}: ({x1:.4f}, {y1:.4f}) -> ({x2:.4f}, {y2:.4f})")

    def _domain_add(self, name: str):
        """Add a domain with mouse selection."""
        name = name.strip()
        if not name:
            print("Error: domain name required")
            return

        if name in self.domains:
            print(f"Error: domain '{name}' already exists")
            return

        # Signal that we're waiting for mouse selection
        self.mouse_selection_pending = True
        self.mouse_selection_domain = name
        self.mouse_down_pos = None
        self.mouse_up_pos = None

        # Set pending domain name in display for preview
        from display import display

        display.pending_domain_name = name
        display.selection_start = None
        display.selection_current = None

        print(
            f"Select region for domain '{name}' by dragging mouse in OpenCV window..."
        )

        # Wait for selection to complete
        import time

        while self.mouse_selection_pending:
            time.sleep(0.1)

    def _domain_del(self, name: str):
        """Delete a domain."""
        name = name.strip()
        if not name:
            print("Error: domain name required")
            return

        if name not in self.domains:
            print(f"Error: domain '{name}' does not exist")
            return

        del self.domains[name]
        print(f"Deleted domain '{name}'")

    def _domain_clear(self):
        """Clear all domains."""
        count = len(self.domains)
        self.domains.clear()
        print(f"Cleared {count} domain(s)")

    def _domain_save(self, path: str):
        """Save domains to file."""
        path = path.strip()
        if not path:
            print("Error: path required")
            return

        filepath = Path(path)
        suffix = filepath.suffix.lower()

        # Convert domains to serializable format with float coordinates
        data = {
            name: {
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2),
            }
            for name, (x1, y1, x2, y2) in self.domains.items()
        }

        try:
            if suffix == ".json":
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)
            elif suffix in (".yml", ".yaml"):
                with open(filepath, "w") as f:
                    yaml.dump(data, f, default_flow_style=False)
            else:
                print(
                    f"Error: unsupported file format '{suffix}' (use .json, .yml, or .yaml)"
                )
                return

            print(f"Saved {len(self.domains)} domain(s) to {path}")
        except Exception as e:
            print(f"Error saving domains: {e}")

    def _domain_load(self, path: str):
        """Load domains from file."""
        path = path.strip()
        if not path:
            print("Error: path required")
            return

        filepath = Path(path)

        if not filepath.exists():
            print(f"Error: file not found: {path}")
            return

        suffix = filepath.suffix.lower()

        try:
            if suffix == ".json":
                with open(filepath, "r") as f:
                    data = json.load(f)
            elif suffix in (".yml", ".yaml"):
                with open(filepath, "r") as f:
                    data = yaml.safe_load(f)
            else:
                print(
                    f"Error: unsupported file format '{suffix}' (use .json, .yml, or .yaml)"
                )
                return

            # Validate and load domains
            loaded_count = 0
            for name, coords in data.items():
                if name in self.domains:
                    print(f"Error: domain '{name}' already exists")
                    return

                # Validate coordinates
                if not all(k in coords for k in ["x1", "y1", "x2", "y2"]):
                    print(f"Error: invalid coordinates for domain '{name}'")
                    return

                # Convert to floats for normalized coordinates
                self.domains[name] = (
                    float(coords["x1"]),
                    float(coords["y1"]),
                    float(coords["x2"]),
                    float(coords["y2"]),
                )
                loaded_count += 1

            print(f"Loaded {loaded_count} domain(s) from {path}")
        except Exception as e:
            print(f"Error loading domains: {e}")

    def handle_mouse_event(self, event, x: int, y: int, flags, param):
        """Handle mouse events from OpenCV window."""
        if not self.mouse_selection_pending:
            return

        if event == 1:  # cv2.EVENT_LBUTTONDOWN
            if not self.mouse_down_pos:
                # First click - set first corner
                self.mouse_down_pos = (x, y)
            else:
                # Second click - set second corner and complete
                self.mouse_up_pos = (x, y)

                # Get frame dimensions from display to normalize coordinates
                from display import display

                # We need to get frame dimensions - store them in display
                if (
                    hasattr(display, "_last_frame_shape")
                    and display._last_frame_shape is not None
                ):
                    h, w = display._last_frame_shape

                    # Calculate bounding box (pixels)
                    x1_px = min(self.mouse_down_pos[0], self.mouse_up_pos[0])
                    y1_px = min(self.mouse_down_pos[1], self.mouse_up_pos[1])
                    x2_px = max(self.mouse_down_pos[0], self.mouse_up_pos[0])
                    y2_px = max(self.mouse_down_pos[1], self.mouse_up_pos[1])

                    # Normalize to 0.0-1.0 range
                    x1 = x1_px / w
                    y1 = y1_px / h
                    x2 = x2_px / w
                    y2 = y2_px / h

                    # Store domain with normalized coordinates
                    self.domains[self.mouse_selection_domain] = (x1, y1, x2, y2)

                    self.log(
                        f"Domain '{self.mouse_selection_domain}' added: ({x1:.4f}, {y1:.4f}) -> ({x2:.4f}, {y2:.4f})"
                    )
                else:
                    self.log("Error: Could not get frame dimensions")

                # Clear pending domain in display
                from display import display

                display.pending_domain_name = None
                display.selection_start = None
                display.selection_current = None

                # Reset selection state
                self.mouse_selection_pending = False
                self.mouse_selection_domain = ""
                self.mouse_down_pos = None
                self.mouse_up_pos = None
        elif event == 2:  # cv2.EVENT_RBUTTONDOWN
            # Right click cancels the first anchor
            if self.mouse_down_pos:
                self.mouse_down_pos = None
                from display import display

                display.selection_start = None
                self.log("First corner cancelled, click to place new first corner")


# Global console instance
console = Console()


def log(message: str):
    """Global log function for convenience."""
    console.log(message)
