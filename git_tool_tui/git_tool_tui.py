#!/usr/bin/env python3
import os
import subprocess
import shutil
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Button, RichLog, Label, Input, OptionList
from textual.widgets.option_list import Option
from textual.screen import ModalScreen

# --- Environment Detection ---
IS_TERMUX = os.path.exists("/data/data/com.termux")
if IS_TERMUX:
    ENV = "termux"
    GH = "/data/data/com.termux/files/usr/bin/gh"
    GIT = "/data/data/com.termux/files/usr/bin/git"
    WORKDIR = Path("/data/data/com.termux/files/home/push_to_git")
    TOOL_BIN = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr")) / "bin"
    HOSTS_YML = Path("/data/data/com.termux/files/home/.config/gh/hosts.yml")
    DL_DIR = Path(os.environ.get("HOME", "")) / "downloads"
else:
    ENV = "wsl"
    GH = shutil.which("gh") or "gh"
    GIT = shutil.which("git") or "git"
    WORKDIR = Path("/home/linux_admin/Github/top-repo")
    TOOL_BIN = Path("/usr/local/bin")
    HOSTS_YML = Path.home() / ".config/gh/hosts.yml"
    DL_DIR = Path("/mnt/c/Users/Dev1d/OneDrive/Bureau/Downloads")

# Create workdir if missing
WORKDIR.mkdir(parents=True, exist_ok=True)


# --- 1. Pure Text Input Modal (For Commits, Branch Names, etc.) ---
class TextInputModal(ModalScreen):
    def __init__(self, title: str, placeholder: str = ""):
        super().__init__()
        self.title_text = title
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.title_text, id="modal-title"),
            Input(placeholder=self.placeholder, id="modal-input"),
            Horizontal(
                Button("Submit", variant="primary", id="submit-btn"),
                Button("Cancel", variant="error", id="cancel-btn"),
                id="modal-buttons"
            ),
            id="text-modal-dialog"
        )

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self.dismiss(self.query_one(Input).value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


# --- 2. Upgraded Selection List Modal (For Repos, Stash, Branches, etc.) ---
class SelectionModal(ModalScreen):
    def __init__(self, title: str, options: list):
        super().__init__()
        self.title_text = title
        self.options_data = options

    def compose(self) -> ComposeResult:
        option_widgets = [Option(disp, id=val) for val, disp in self.options_data]
        yield Vertical(
            Label(self.title_text, id="modal-title"),
            OptionList(*option_widgets, id="modal-option-list"),
            Horizontal(
                Button("Cancel", variant="error", id="cancel-btn"),
                id="modal-buttons"
            ),
            id="select-modal-dialog"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option and event.option.id is not None:
            self.dismiss(event.option.id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


# --- Main TUI App ---
class GitToolApp(App):
    CSS = """
    Grid {
        grid-size: 2;
        grid-columns: 8 1fr; 
        padding: 0;
    }
    #sidebar {
        overflow-y: scroll;
        border-right: solid $accent;
        padding-right: 0;
    }
    #sidebar Button {
        margin-bottom: 0;
        width: 100%;
        height: 1; 
        border: none;
        min-width: 0;       
        padding: 0;         
        background: $surface;
        color: $text;
    }
    
    /* Highlight clearly when navigated via arrow keys */
    #sidebar Button:focus {
        background: $accent;
        color: $surface;
        text-style: bold;
    }
    
    #console-container {
        padding-left: 1;
    }
    RichLog {
        background: $background;
        border: tall $primary;
    }
    #status-bar {
        background: $surface;
        padding: 0 1;
        color: $text;
        height: 1;
    }
    
    /* --- Popups Styling --- */
    #text-modal-dialog, #select-modal-dialog {
        background: $surface;
        padding: 1 2;        
        border: thick $primary;
        width: 90%;
        height: auto;
        align: center middle;
    }
    #select-modal-dialog {
        max-height: 75%;
    }
    #modal-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #modal-option-list {
        height: 8;
        border: solid $secondary;
        margin-bottom: 1;
    }
    #modal-input {
        margin-bottom: 1;
        height: 3;
    }
    #modal-buttons {
        align: center middle;
        height: 3;
        width: 100%;
    }
    #modal-buttons Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    TITLE = f"Git Tool TUI ({ENV.upper()})"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "press_button('btn_connect')", "Connect"),
        ("2", "press_button('btn_disconnect')", "Disconnect"),
        ("3", "press_button('btn_conn_status')", "Conn Status"),
        ("4", "press_button('btn_choose_repo')", "Choose Repo"),
        ("5", "press_button('btn_pull')", "Pull"),
        ("6", "press_button('btn_push')", "Push"),
        ("7", "press_button('btn_import')", "Import File"),
        ("8", "press_button('btn_clean_dl')", "Clean DL"),
        ("9", "press_button('btn_status')", "Status"),
    ]

    def __init__(self):
        super().__init__()
        self.repo_actif = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(f"Env: {ENV} | Active Repo: None", id="status-bar")
        yield Grid(
            Vertical(
                Button("Menu", id="btn_menu_guide"),
                Button("1", id="btn_connect"),
                Button("2", id="btn_disconnect"),
                Button("3", id="btn_conn_status"),
                Button("4", id="btn_choose_repo"),
                Button("5", id="btn_pull"),
                Button("6", id="btn_push"),
                Button("7", id="btn_import"),
                Button("8", id="btn_clean_dl"),
                Button("9", id="btn_status"),
                Button("10", id="btn_log"),
                Button("11", id="btn_diff"),
                Button("12", id="btn_stash"),
                Button("13", id="btn_restore"),
                Button("14", id="btn_branch"),
                Button("15", id="btn_reset"),
                Button("16", id="btn_update_tool"),
                id="sidebar"
            ),
            Vertical(
                RichLog(highlight=True, markup=True, id="console"),
                id="console-container"
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self.log_widget = self.query_one("#console", RichLog)
        self.log_widget.write(f"[yellow][ENV][/yellow] Working Directory initialized at: {WORKDIR}")
        self.print_menu_guide()
        # Direct keyboard focus to the menu sidebar right away
        self.query_one("#btn_menu_guide", Button).focus()

    def update_status(self):
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"Env: {ENV} | Active Repo: {self.repo_actif or 'None'}")

    def print_menu_guide(self):
        guide_text = (
            "\n[yellow]------------------- FUNCTION DIRECTORY MAP -------------------[/yellow]\n"
            "  [bold]1)[/bold]  connect                              [bold]9)[/bold]  status du repo\n"
            "  [bold]2)[/bold]  disconnect                           [bold]10)[/bold] log des commits\n"
            "  [bold]3)[/bold]  connection status                    [bold]11)[/bold] diff (modifications locales)\n"
            "  [bold]4)[/bold]  choisir un repo                      [bold]12)[/bold] stash (mettre de cote)\n"
            "  [bold]5)[/bold]  pull (mettre à jour)                 [bold]13)[/bold] restore (annuler modifications)\n"
            "  [bold]6)[/bold]  push (envoyer les changements)       [bold]14)[/bold] branch (gestion des branches)\n"
            "  [bold]7)[/bold]  mettre a jour depuis downloads/      [bold]15)[/bold] reset (annuler le dernier commit)\n"
            "  [bold]8)[/bold]  nettoyer downloads/                  [bold]16)[/bold] mettre a jour git_tool.sh\n"
            "[yellow]--------------------------------------------------------------[/yellow]\n"
        )
        self.log_widget.write(guide_text)

    def action_press_button(self, button_id: str) -> None:
        try:
            btn = self.query_one(f"#{button_id}", Button)
            btn.press()
        except Exception:
            pass

    # --- Utility execution wrappers ---
    def unlock_hosts(self):
        if HOSTS_YML.exists():
            HOSTS_YML.chmod(0o600)

    def lock_hosts(self):
        if HOSTS_YML.exists():
            HOSTS_YML.chmod(0o400)

    def run_cmd(self, cmd: list, cwd: Path = WORKDIR, capture=True):
        self.unlock_hosts()
        try:
            if capture:
                res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
                self.lock_hosts()
                return res
            else:
                self.unlock_hosts()
                subprocess.run(cmd, cwd=str(cwd))
                self.lock_hosts()
                return None
        except Exception as e:
            self.lock_hosts()
            self.log_widget.write(f"[red]Error executing command: {e}[/red]")

    def check_network(self) -> bool:
        res = subprocess.run(["ping", "-c", "1", "-W", "2", "github.com"], capture_output=True)
        if res.returncode != 0:
            self.log_widget.write("[red]❌ No internet connection. Check network.[/red]")
            return False
        return True

    def check_repo_active(self) -> bool:
        if not self.repo_actif:
            self.log_widget.write("[red]❌ No repository selected. Click button '4' first.[/red]")
            return False
        return True

    # --- Event Handler Router ---
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "btn_menu_guide":
            self.print_menu_guide()
            return

        self.log_widget.write(f"\n[bold cyan]> Executing action...[/bold cyan]")

        if btn_id == "btn_connect":
            if self.check_network():
                self.log_widget.write("[yellow]Launching GitHub Authentication. Check terminal window...[/yellow]")
                with self.suspend():
                    self.unlock_hosts()
                    os.system(f"{GH} auth login")
                    if ENV == "wsl":
                        os.system(f"{GH} auth setup-git")
                    self.lock_hosts()
                self.log_widget.write("[green]Returned from Auth login flow.[/green]")

        elif btn_id == "btn_disconnect":
            self.unlock_hosts()
            res = subprocess.run([GH, "auth", "logout", "-y"], capture_output=True, text=True)
            self.lock_hosts()
            self.log_widget.write(res.stdout or res.stderr)

        elif btn_id == "btn_conn_status":
            if self.check_network():
                res = self.run_cmd([GH, "auth", "status"])
                self.log_widget.write(res.stdout + res.stderr)

        elif btn_id == "btn_choose_repo":
            if self.check_network():
                res = self.run_cmd([GH, "repo", "list", "--limit", "20", "--json", "nameWithOwner", "-q", ".[].nameWithOwner"])
                repos = [r.strip() for r in res.stdout.strip().split("\n") if r.strip()]
                if not repos:
                    self.log_widget.write("[yellow]No repos found. Are you authenticated?[/yellow]")
                    return

                def select_repo_callback(chosen_repo):
                    if chosen_repo:
                        self.repo_actif = chosen_repo
                        self.update_status()
                        repo_nom = self.repo_actif.split("/")[-1]
                        repo_path = WORKDIR / repo_nom
                        if not repo_path.exists():
                            self.log_widget.write(f"[yellow]Cloning {self.repo_actif}...[/yellow]")
                            res_clone = self.run_cmd([GH, "repo", "clone", self.repo_actif, str(repo_path)])
                            self.log_widget.write(res_clone.stdout + res_clone.stderr)
                        self.log_widget.write(f"[green]✅ Active Repo set to: {self.repo_actif}[/green]")

                options = []
                for r in repos:
                    clean_name = r.split('/')[-1] if '/' in r else r
                    display_name = clean_name if len(clean_name) <= 24 else f"{clean_name[:21]}..."
                    options.append((r, display_name))

                self.push_screen(SelectionModal("CHOOSE A REPOSITORY", options), select_repo_callback)

        elif btn_id in ["btn_pull", "btn_push", "btn_status", "btn_log", "btn_diff", "btn_stash", "btn_restore", "btn_branch", "btn_reset", "btn_import"]:
            if not self.check_repo_active():
                return
            repo_path = WORKDIR / self.repo_actif.split("/")[-1]

            if btn_id == "btn_pull":
                if self.check_network():
                    res = self.run_cmd([GIT, "pull"], cwd=repo_path)
                    self.log_widget.write(res.stdout + res.stderr)

            elif btn_id == "btn_push":
                if self.check_network():
                    res_br = self.run_cmd([GIT, "branch", "--show-current"], cwd=repo_path)
                    branch = res_br.stdout.strip()
                    self.log_widget.write(f"[yellow]Current Branch: {branch}[/yellow]")
                    
                    def do_commit(commit_msg):
                        if commit_msg:
                            self.run_cmd([GIT, "add", "."], cwd=repo_path)
                            self.run_cmd([GIT, "commit", "-m", commit_msg], cwd=repo_path)
                            res_p = self.run_cmd([GIT, "push"], cwd=repo_path)
                            self.log_widget.write(res_p.stdout + res_p.stderr)

                    self.push_screen(TextInputModal("ENTER COMMIT MESSAGE"), do_commit)

            elif btn_id == "btn_status":
                res = self.run_cmd([GIT, "status"], cwd=repo_path)
                self.log_widget.write(res.stdout)

            elif btn_id == "btn_log":
                res = self.run_cmd([GIT, "log", "--oneline", "-10"], cwd=repo_path)
                self.log_widget.write(res.stdout)

            elif btn_id == "btn_diff":
                res = self.run_cmd([GIT, "diff"], cwd=repo_path)
                self.log_widget.write(res.stdout if res.stdout else "[yellow]No local changes diffed.[/yellow]")

            elif btn_id == "btn_stash":
                options = [
                    ("1", "1) Stash changes"),
                    ("2", "2) Pop changes"),
                    ("3", "3) List Stashes")
                ]
                def stash_cb(choice):
                    if choice == "1":
                        self.log_widget.write(self.run_cmd([GIT, "stash"], cwd=repo_path).stdout)
                    elif choice == "2":
                        self.log_widget.write(self.run_cmd([GIT, "stash", "pop"], cwd=repo_path).stdout)
                    elif choice == "3":
                        self.log_widget.write(self.run_cmd([GIT, "stash", "list"], cwd=repo_path).stdout)
                self.push_screen(SelectionModal("STASH OPERATIONS", options), stash_cb)

            elif btn_id == "btn_restore":
                stat = self.run_cmd([GIT, "status", "--short"], cwd=repo_path).stdout
                modified_lines = [line.strip().split()[-1] for line in stat.strip().split('\n') if line.strip()]
                
                options = [("all", "✨ Restore All Files")] + [(f, f"📄 {f}") for f in modified_lines]
                
                def restore_cb(target):
                    if target == "all":
                        self.run_cmd([GIT, "restore", "."], cwd=repo_path)
                        self.log_widget.write("[green]Restored all files.[/green]")
                    elif target:
                        res = self.run_cmd([GIT, "restore", target], cwd=repo_path)
                        self.log_widget.write(f"[green]Restored {target}[/green]\n{res.stderr}")
                self.push_screen(SelectionModal("CHOOSE FILE TO RESTORE", options), restore_cb)

            elif btn_id == "btn_branch":
                options = [
                    ("1", "1) View branches"),
                    ("2", "2) Create branch"),
                    ("3", "3) Checkout branch")
                ]
                def branch_cb(choice):
                    if choice == "1":
                        self.log_widget.write(self.run_cmd([GIT, "branch", "-a"], cwd=repo_path).stdout)
                    elif choice == "2":
                        self.push_screen(TextInputModal("NEW BRANCH NAME"), lambda name: self.log_widget.write(self.run_cmd([GIT, "checkout", "-b", name], cwd=repo_path).stdout if name else ""))
                    elif choice == "3":
                        avail = self.run_cmd([GIT, "branch"], cwd=repo_path).stdout
                        br_list = [b.replace("*", "").strip() for b in avail.strip().split("\n") if b.strip()]
                        br_options = [(b, f"🌿 {b}") for b in br_list]
                        self.push_screen(SelectionModal("SELECT BRANCH TO CHECKOUT", br_options), lambda name: self.log_widget.write(self.run_cmd([GIT, "checkout", name], cwd=repo_path).stdout if name else ""))
                self.push_screen(SelectionModal("BRANCH MANAGEMENT", options), branch_cb)

            elif btn_id == "btn_reset":
                options = [("y", "Yes, undo last commit"), ("n", "No, keep it")]
                def reset_cb(ans):
                    if ans == "y":
                        self.log_widget.write(self.run_cmd([GIT, "reset", "HEAD~1"], cwd=repo_path).stdout)
                self.push_screen(SelectionModal("UNDO LAST COMMIT?", options), reset_cb)

            elif btn_id == "btn_import":
                if not DL_DIR.exists():
                    self.log_widget.write(f"[red]Downloads folder doesn't exist: {DL_DIR}[/red]")
                    return
                files = os.listdir(DL_DIR)
                if not files:
                    self.log_widget.write("[yellow]No files available in downloads.[/yellow]")
                    return
                
                file_options = [(f, f"📁 {f}") for f in files]
                def file_cb(filename):
                    if filename:
                        src_file = DL_DIR / filename
                        subdirs = [p for p in repo_path.rglob('*') if p.is_dir() and ".git" not in p.parts][:15]
                        
                        dest_options = [("root", "🏠 Root (/)")] + [(str(p), f"📂 {p.relative_to(repo_path)}") for p in subdirs]
                        def dest_cb(d_choice):
                            if d_choice:
                                dest = repo_path if d_choice == "root" else Path(d_choice)
                                shutil.copy(src_file, dest / filename)
                                self.log_widget.write(f"[green]Copied {filename} to {dest.relative_to(repo_path)}[/green]")
                        self.push_screen(SelectionModal("CHOOSE TARGET DESTINATION", dest_options), dest_cb)
                self.push_screen(SelectionModal("SELECT FILE TO IMPORT", file_options), file_cb)

        elif btn_id == "btn_clean_dl":
            if DL_DIR.exists() and os.listdir(DL_DIR):
                options = [("y", "Yes, delete everything"), ("n", "No, keep files")]
                def clean_cb(ans):
                    if ans == 'y':
                        for f in os.listdir(DL_DIR):
                            os.remove(DL_DIR / f)
                        self.log_widget.write("[green]Cleared downloads directory.[/green]")
                self.push_screen(SelectionModal("DELETE EVERYTHING IN DOWNLOADS?", options), clean_cb)
            else:
                self.log_widget.write("[yellow]Downloads directory is already empty.[/yellow]")

        elif btn_id == "btn_update_tool":
            if ENV == "wsl":
                if shutil.which("update_git_wsl.sh"):
                    subprocess.run(["update_git_wsl.sh"])
                    self.log_widget.write("[green]Executed update_git_wsl.sh[/green]")
                else:
                    self.log_widget.write("[red]update_git_wsl.sh not found in PATH.[/red]")
            else:
                src_script = DL_DIR / "git_tool.sh"
                if src_script.exists():
                    self.unlock_hosts()
                    shutil.copy(src_script, TOOL_BIN / "git_tool.sh")
                    (TOOL_BIN / "git_tool.sh").chmod(0o755)
                    self.lock_hosts()
                    self.log_widget.write("[green]Updated git_tool.sh in local bins.[/green]")
                else:
                    self.log_widget.write(f"[red]Missing source update script file at: {src_script}[/red]")


if __name__ == "__main__":
    app = GitToolApp()
    app.run()
