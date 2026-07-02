#!/usr/bin/env python3
import os
import subprocess
import shutil
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Button, RichLog, Label, Input
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

# --- Dialog Modal for text inputs ---
class InputModal(ModalScreen):
    def __init__(self, prompt: str, placeholder: str = ""):
        super().__init__()
        self.prompt = prompt
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.prompt, id="modal-label"),
            Input(placeholder=self.placeholder, id="modal-input"),
            Horizontal(
                Button("Submit", variant="primary", id="submit-btn"),
                Button("Cancel", variant="error", id="cancel-btn"),
                id="modal-buttons"
            ),
            id="modal-dialog"
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


# --- Main TUI App ---
class GitToolApp(App):
    CSS = """
    Grid {
        grid-size: 2;
        grid-columns: 1fr 2fr;
        padding: 1;
    }
    #sidebar {
        overflow-y: scroll;
        border-right: solid $accent;
        padding-right: 1;
    }
    #sidebar Button {
        margin-bottom: 1;
        width: 100%;
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
    #modal-dialog {
        grid-size: 1;
        background: $surface;
        padding: 2;
        border: thick $primary;
        width: 50;
        height: 15;
        align: center middle;
    }
    #modal-buttons {
        margin-top: 1;
        align: center middle;
    }
    #modal-buttons Button {
        margin: 0 1;
    }
    """

    TITLE = f"Git Tool TUI ({ENV.upper()})"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.repo_actif = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(f"Env: {ENV} | Active Repo: None", id="status-bar")
        yield Grid(
            Vertical(
                Label("🔐 GitHub Auth"),
                Button("Connect", id="btn_connect"),
                Button("Disconnect", id="btn_disconnect"),
                Button("Status Connection", id="btn_conn_status"),
                
                Label("📁 Repo Selection"),
                Button("Choose Repo", id="btn_choose_repo"),
                
                Label("🔄 Git Operations"),
                Button("Git Pull", id="btn_pull"),
                Button("Git Push", id="btn_push"),
                Button("Repo Status", id="btn_status"),
                Button("Commit Log", id="btn_log"),
                Button("Local Diff", id="btn_diff"),
                
                Label("🛠️ Advanced Git"),
                Button("Stash Manager", id="btn_stash"),
                Button("Restore Files", id="btn_restore"),
                Button("Branch Manager", id="btn_branch"),
                Button("Undo Last Commit (Reset)", id="btn_reset"),
                
                Label("📂 System & Updates"),
                Button("Import from Downloads", id="btn_import"),
                Button("Clean Downloads", id="btn_clean_dl"),
                Button("Update Tool", id="btn_update_tool"),
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

    def update_status(self):
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"Env: {ENV} | Active Repo: {self.repo_actif or 'None'}")

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
            self.log_widget.write("[red]❌ No repository selected. Click 'Choose Repo' first.[/red]")
            return False
        return True

    # --- Event Handler Router ---
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
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

                def select_repo_callback(choice):
                    if choice and choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(repos):
                            self.repo_actif = repos[idx]
                            self.update_status()
                            repo_nom = self.repo_actif.split("/")[-1]
                            repo_path = WORKDIR / repo_nom
                            if not repo_path.exists():
                                self.log_widget.write(f"[yellow]Cloning {self.repo_actif}...[/yellow]")
                                res_clone = self.run_cmd([GH, "repo", "clone", self.repo_actif, str(repo_path)])
                                self.log_widget.write(res_clone.stdout + res_clone.stderr)
                            self.log_widget.write(f"[green]✅ Active Repo set to: {self.repo_actif}[/green]")
                        else:
                            self.log_widget.write("[red]Invalid Choice.[/red]")

                prompt_str = "\n".join([f"{i+1}) {r}" for i, r in enumerate(repos)]) + "\n\nEnter Repo Number:"
                self.push_screen(InputModal(prompt_str), select_repo_callback)

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

                    self.push_screen(InputModal("Enter Commit Message:"), do_commit)

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
                prompt = "1) Stash changes\n2) Pop changes\n3) List Stashes\n\nEnter choice (1-3):"
                def stash_cb(choice):
                    if choice == "1":
                        self.log_widget.write(self.run_cmd([GIT, "stash"], cwd=repo_path).stdout)
                    elif choice == "2":
                        self.log_widget.write(self.run_cmd([GIT, "stash", "pop"], cwd=repo_path).stdout)
                    elif choice == "3":
                        self.log_widget.write(self.run_cmd([GIT, "stash", "list"], cwd=repo_path).stdout)
                self.push_screen(InputModal(prompt), stash_cb)

            elif btn_id == "btn_restore":
                stat = self.run_cmd([GIT, "status", "--short"], cwd=repo_path).stdout
                prompt = f"Modified Files:\n{stat}\nType file name to restore or 'all':"
                def restore_cb(target):
                    if target == "all":
                        self.run_cmd([GIT, "restore", "."], cwd=repo_path)
                        self.log_widget.write("[green]Restored all files.[/green]")
                    elif target:
                        res = self.run_cmd([GIT, "restore", target], cwd=repo_path)
                        self.log_widget.write(f"[green]Restored {target}[/green]\n{res.stderr}")
                self.push_screen(InputModal(prompt), restore_cb)

            elif btn_id == "btn_branch":
                prompt = "1) View branches\n2) Create branch\n3) Checkout branch\nEnter choice:"
                def branch_cb(choice):
                    if choice == "1":
                        self.log_widget.write(self.run_cmd([GIT, "branch", "-a"], cwd=repo_path).stdout)
                    elif choice == "2":
                        self.push_screen(InputModal("New branch name:"), lambda name: self.log_widget.write(self.run_cmd([GIT, "checkout", "-b", name], cwd=repo_path).stdout + self.run_cmd([GIT, "checkout", "-b", name], cwd=repo_path).stderr) if name else None)
                    elif choice == "3":
                        avail = self.run_cmd([GIT, "branch"], cwd=repo_path).stdout
                        self.push_screen(InputModal(f"{avail}\nCheckout branch name:"), lambda name: self.log_widget.write(self.run_cmd([GIT, "checkout", name], cwd=repo_path).stdout + self.run_cmd([GIT, "checkout", name], cwd=repo_path).stderr) if name else None)
                self.push_screen(InputModal(prompt), branch_cb)

            elif btn_id == "btn_reset":
                last_log = self.run_cmd([GIT, "log", "--oneline", "-1"], cwd=repo_path).stdout
                prompt = f"Last Commit:\n{last_log}\nUndo this commit? (y/n):"
                def reset_cb(ans):
                    if ans.lower() == 'y':
                        self.log_widget.write(self.run_cmd([GIT, "reset", "HEAD~1"], cwd=repo_path).stdout)
                self.push_screen(InputModal(prompt), reset_cb)

            elif btn_id == "btn_import":
                if not DL_DIR.exists():
                    self.log_widget.write(f"[red]Downloads folder doesn't exist: {DL_DIR}[/red]")
                    return
                files = os.listdir(DL_DIR)
                if not files:
                    self.log_widget.write("[yellow]No files available in downloads.[/yellow]")
                    return
                prompt = "\n".join([f"{f}" for f in files]) + "\n\nEnter exact filename to copy:"
                def file_cb(filename):
                    if filename in files:
                        src_file = DL_DIR / filename
                        subdirs = [p for p in repo_path.rglob('*') if p.is_dir() and ".git" not in p.parts][:15]
                        dest_prompt = "1) Root (/) \n" + "\n".join([f"{i+2}) {p.relative_to(repo_path)}" for i, p in enumerate(subdirs)]) + "\n\nDestination choice number:"
                        def dest_cb(d_choice):
                            dest = repo_path
                            if d_choice.isdigit() and int(d_choice) >= 2:
                                idx = int(d_choice) - 2
                                if idx < len(subdirs): dest = subdirs[idx]
                            shutil.copy(src_file, dest / filename)
                            self.log_widget.write(f"[green]Copied {filename} to {dest.relative_to(repo_path)}[/green]")
                        self.push_screen(InputModal(dest_prompt), dest_cb)
                self.push_screen(InputModal(prompt), file_cb)

        elif btn_id == "btn_clean_dl":
            if DL_DIR.exists() and os.listdir(DL_DIR):
                def clean_cb(ans):
                    if ans.lower() == 'y':
                        for f in os.listdir(DL_DIR):
                            os.remove(DL_DIR / f)
                        self.log_widget.write("[green]Cleared downloads directory.[/green]")
                self.push_screen(InputModal(f"Delete everything in {DL_DIR}? (y/n)"), clean_cb)
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
