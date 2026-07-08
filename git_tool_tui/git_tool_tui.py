#!/usr/bin/env python3
import os
import subprocess
import shutil
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Button, RichLog, Label, Input, OptionList, DirectoryTree
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

WORKDIR.mkdir(parents=True, exist_ok=True)


# --- Text Input Modal ---
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


# --- Selection Modal ---
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


# --- Warning Modal ---
class WarningModal(ModalScreen):
    def __init__(self, title: str, message: str):
        super().__init__()
        self.title_text = title
        self.message = message

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.title_text, id="modal-title"),
            Label(self.message, id="warning-message"),
            Horizontal(
                Button("⚠ Continuer quand meme", variant="warning", id="confirm-btn"),
                Button("Annuler", variant="primary", id="cancel-btn"),
                id="modal-buttons"
            ),
            id="warning-modal-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-btn")


# --- Directory Browser Modal ---
class DirectoryModal(ModalScreen):
    def __init__(self, root_path: Path):
        super().__init__()
        self.root_path = root_path
        self.current_path = root_path

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"📂 {self.current_path}", id="modal-title"),
            OptionList(id="dir-list"),
            Horizontal(
                Button("⬆ Parent", variant="default", id="parent-btn"),
                Button("✓ Select", variant="primary", id="select-btn"),
                Button("Cancel", variant="error", id="cancel-btn"),
                id="modal-buttons"
            ),
            id="dir-modal-dialog"
        )

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        dir_list = self.query_one("#dir-list", OptionList)
        dir_list.clear_options()
        self.query_one("#modal-title", Label).update(f"📂 {self.current_path}")
        try:
            entries = sorted(self.current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                icon = "📁" if entry.is_dir() else "📄"
                dir_list.add_option(Option(f"{icon} {entry.name}", id=str(entry)))
        except PermissionError:
            dir_list.add_option(Option("⚠ Permission denied", id="__error__"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id and event.option.id != "__error__":
            selected = Path(event.option.id)
            if selected.is_dir():
                self.current_path = selected
                self.refresh_list()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "parent-btn":
            if self.current_path != self.root_path:
                self.current_path = self.current_path.parent
                self.refresh_list()
        elif event.button.id == "select-btn":
            self.dismiss(self.current_path)
        elif event.button.id == "cancel-btn":
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
    #text-modal-dialog, #select-modal-dialog, #warning-modal-dialog, #dir-modal-dialog {
        background: $surface;
        padding: 1 2;
        border: thick $primary;
        width: 90%;
        height: auto;
        align: center middle;
    }
    #select-modal-dialog, #dir-modal-dialog {
        max-height: 75%;
    }
    #warning-modal-dialog {
        border: thick $warning;
    }
    #warning-message {
        width: 100%;
        text-align: center;
        color: $warning;
        margin-bottom: 1;
    }
    #modal-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #modal-option-list, #dir-list {
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
        ("0", "press_button('btn_sync_fix')", "Sync Fix"),
        ("b", "press_button('btn_browse')", "Browse"),
        ("up", "focus_prev_sidebar", "Up"),
        ("down", "focus_next_sidebar", "Down"),
    ]

    SIDEBAR_BUTTONS = [
        "btn_menu_guide", "btn_connect", "btn_disconnect", "btn_conn_status",
        "btn_choose_repo", "btn_pull", "btn_push", "btn_import", "btn_clean_dl",
        "btn_status", "btn_log", "btn_diff", "btn_stash", "btn_restore",
        "btn_branch", "btn_reset", "btn_update_tool", "btn_sync_fix", "btn_browse",
        "btn_gitignore"
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
                Button("17", id="btn_sync_fix"),
                Button("18", id="btn_browse"),
                Button("19", id="btn_gitignore"),
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
        self.log_widget.write(f"[yellow][ENV][/yellow] Working Directory: {WORKDIR}")
        self.print_menu_guide()
        self.query_one("#btn_menu_guide", Button).focus()

    def update_status(self):
        self.query_one("#status-bar", Label).update(
            f"Env: {ENV} | Active Repo: {self.repo_actif or 'None'}"
        )

    def print_menu_guide(self):
        self.log_widget.write(
            "\n[yellow]--- FUNCTION MAP ---[/yellow]\n"
            "  [bold]1)[/bold]  connect\n"
            "  [bold]2)[/bold]  disconnect\n"
            "  [bold]3)[/bold]  conn status\n"
            "  [bold]4)[/bold]  choisir repo\n"
            "  [bold]5)[/bold]  pull\n"
            "  [bold]6)[/bold]  push\n"
            "  [bold]7)[/bold]  import file\n"
            "  [bold]8)[/bold]  clean downloads\n"
            "  [bold]9)[/bold]  status\n"
            "  [bold]10)[/bold] log\n"
            "  [bold]11)[/bold] diff\n"
            "  [bold]12)[/bold] stash\n"
            "  [bold]13)[/bold] restore\n"
            "  [bold]14)[/bold] branch\n"
            "  [bold]15)[/bold] reset\n"
            "  [bold]16)[/bold] update tool\n"
            "  [bold]17)[/bold] sync fix\n"
            "  [bold]18)[/bold] browse dirs\n"
            "  [bold]19)[/bold] gitignore\n"
            "[yellow]--------------------[/yellow]\n"
        )

    def action_press_button(self, button_id: str) -> None:
        try:
            self.query_one(f"#{button_id}", Button).press()
        except Exception:
            pass

    def action_focus_prev_sidebar(self) -> None:
        focused = self.focused
        if focused and hasattr(focused, "id") and focused.id in self.SIDEBAR_BUTTONS:
            idx = self.SIDEBAR_BUTTONS.index(focused.id)
            if idx > 0:
                self.query_one(f"#{self.SIDEBAR_BUTTONS[idx - 1]}", Button).focus()

    def action_focus_next_sidebar(self) -> None:
        focused = self.focused
        if focused and hasattr(focused, "id") and focused.id in self.SIDEBAR_BUTTONS:
            idx = self.SIDEBAR_BUTTONS.index(focused.id)
            if idx < len(self.SIDEBAR_BUTTONS) - 1:
                self.query_one(f"#{self.SIDEBAR_BUTTONS[idx + 1]}", Button).focus()

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
                subprocess.run(cmd, cwd=str(cwd))
                self.lock_hosts()
                return None
        except Exception as e:
            self.lock_hosts()
            self.log_widget.write(f"[red]Error: {e}[/red]")

    def check_network(self) -> bool:
        res = subprocess.run(["ping", "-c", "1", "-W", "2", "github.com"], capture_output=True)
        if res.returncode != 0:
            self.log_widget.write("[red]❌ No internet connection.[/red]")
            return False
        return True

    def check_repo_active(self) -> bool:
        if not self.repo_actif:
            self.log_widget.write("[red]❌ No repo selected. Use button 4 first.[/red]")
            return False
        return True

    # --- Utilitaire: commit + push ---
    def _propose_commit_push(self, repo_path: Path, message: str):
        def commit_now_cb(choice):
            if choice == "y":
                self.run_cmd([GIT, "add", ".gitignore"], cwd=repo_path)
                res_commit = self.run_cmd([GIT, "commit", "-m", message], cwd=repo_path)
                self.log_widget.write(res_commit.stdout + res_commit.stderr)
                res_push = self.run_cmd([GIT, "push"], cwd=repo_path)
                self.log_widget.write(res_push.stdout + res_push.stderr)
                self.log_widget.write("[green]✅ Commit et push effectues.[/green]")
            else:
                self.log_widget.write("[yellow]N\'oublie pas de committer manuellement (bouton 6).[/yellow]")
        self.push_screen(
            SelectionModal("COMMITTER ET PUSHER MAINTENANT ?", [
                ("y", "✅ Oui, committer et pusher maintenant"),
                ("n", "⏳ Non, je le ferai manuellement")
            ]),
            commit_now_cb
        )

    # --- Utilitaire: choisir via liste ou manuel ---
    def _pick_entry(self, repo_path: Path, title: str, callback):
        options = [
            ("browse", "📂 Choisir dans la liste des fichiers/dossiers"),
            ("manual", "✏️  Saisir manuellement un pattern")
        ]
        def mode_cb(mode):
            if mode == "browse":
                try:
                    entries = sorted(repo_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
                    file_options = []
                    for e in entries:
                        if e.name.startswith("."):
                            continue
                        icon = "📁" if e.is_dir() else "📄"
                        suffix = "/" if e.is_dir() else ""
                        file_options.append((e.name + suffix, f"{icon} {e.name}{suffix}"))
                    self.push_screen(SelectionModal(title, file_options), callback)
                except Exception as e:
                    self.log_widget.write(f"[red]Erreur: {e}[/red]")
            elif mode == "manual":
                self.push_screen(
                    TextInputModal(title, placeholder="ex: *.log, venv/, __pycache__/"),
                    callback
                )
        self.push_screen(SelectionModal("MODE DE SELECTION", options), mode_cb)

    # --- Option 1: ajout simple (pas encore tracke) ---
    def _gitignore_add_simple(self, repo_path: Path, gitignore_path: Path):
        def add_cb(entry):
            if not entry:
                return
            if gitignore_path.exists():
                existing = gitignore_path.read_text().splitlines()
                if entry in existing:
                    self.log_widget.write(f"[yellow]\'{entry}\' est deja dans .gitignore[/yellow]")
                    return
                with open(gitignore_path, "a") as f:
                    f.write(entry + "\n")
            else:
                gitignore_path.write_text(entry + "\n")
            self.log_widget.write(f"[green]✅ \'{entry}\' ajoute au .gitignore[/green]")
            self._propose_commit_push(repo_path, f"add {entry} to .gitignore")

        self._pick_entry(repo_path, "CHOISIR QUOI IGNORER", add_cb)

    # --- Option 2: ajout + untrack (deja tracke) ---
    def _gitignore_add_untrack(self, repo_path: Path, gitignore_path: Path):
        def add_cb(entry):
            if not entry:
                return
            if gitignore_path.exists():
                existing = gitignore_path.read_text().splitlines()
                if entry in existing:
                    self.log_widget.write(f"[yellow]\'{entry}\' est deja dans .gitignore[/yellow]")
                else:
                    with open(gitignore_path, "a") as f:
                        f.write(entry + "\n")
                    self.log_widget.write(f"[green]✅ \'{entry}\' ajoute au .gitignore[/green]")
            else:
                gitignore_path.write_text(entry + "\n")
                self.log_widget.write(f"[green]✅ \'{entry}\' ajoute au .gitignore[/green]")

            def confirm_untrack(confirmed):
                if confirmed:
                    entry_clean = entry.rstrip("/")
                    res_rm = self.run_cmd([GIT, "rm", "-r", "--cached", entry_clean], cwd=repo_path)
                    self.log_widget.write(res_rm.stdout + res_rm.stderr)
                    self.log_widget.write(f"[green]✅ \'{entry_clean}\' retire du tracking git.[/green]")
                    self._propose_commit_push(repo_path, f"remove {entry_clean} from tracking")
                else:
                    self.log_widget.write("[yellow]git rm --cached annule.[/yellow]")

            self.push_screen(
                WarningModal(
                    f"⚠ RETIRER DU TRACKING GIT",
                    f"\'{entry}\' sera retire du tracking git\n(git rm --cached).\nLe fichier local reste intact.\nContinuer ?"
                ),
                confirm_untrack
            )

        self._pick_entry(repo_path, "CHOISIR QUOI IGNORER ET UNTRACKER", add_cb)

    # --- Option 3: enlever une entree du .gitignore ---
    def _gitignore_remove(self, repo_path: Path, gitignore_path: Path):
        if not gitignore_path.exists() or not gitignore_path.read_text().strip():
            self.log_widget.write("[yellow]Le .gitignore est vide ou inexistant.[/yellow]")
            return

        lines = [l for l in gitignore_path.read_text().splitlines() if l.strip()]
        self.log_widget.write("\n[yellow]Contenu actuel du .gitignore :[/yellow]")
        for l in lines:
            self.log_widget.write(f"  {l}")

        options = [(l, f"🗑  {l}") for l in lines]

        def remove_cb(entry):
            if not entry:
                return
            new_lines = [l for l in lines if l != entry]
            gitignore_path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""))
            self.log_widget.write(f"[green]✅ \'{entry}\' enleve du .gitignore[/green]")

            # Proposer de remettre dans le tracking
            def retrack_cb(choice):
                if choice == "y":
                    entry_clean = entry.rstrip("/")
                    res_add = self.run_cmd([GIT, "add", entry_clean], cwd=repo_path)
                    self.log_widget.write(res_add.stdout + res_add.stderr)
                    self.log_widget.write(f"[green]✅ \'{entry_clean}\' remis dans le tracking git.[/green]")
                    self._propose_commit_push(repo_path, f"unignore {entry_clean}")
                else:
                    self._propose_commit_push(repo_path, f"remove {entry} from .gitignore")

            self.push_screen(
                SelectionModal(f"REMETTRE \'{entry}\' DANS LE TRACKING ?", [
                    ("y", "✅ Oui, git add (remettre dans le tracking)"),
                    ("n", "⏳ Non, juste enlever du .gitignore")
                ]),
                retrack_cb
            )

        self.push_screen(SelectionModal("CHOISIR LA LIGNE A ENLEVER", options), remove_cb)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn_menu_guide":
            self.print_menu_guide()
            return

        self.log_widget.write(f"\n[bold cyan]> Executing...[/bold cyan]")

        if btn_id == "btn_connect":
            if self.check_network():
                self.log_widget.write("[yellow]Launching GitHub Auth...[/yellow]")
                with self.suspend():
                    self.unlock_hosts()
                    os.system(f"{GH} auth login")
                    if ENV == "wsl":
                        os.system(f"{GH} auth setup-git")
                    self.lock_hosts()
                self.log_widget.write("[green]Returned from auth flow.[/green]")

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
                res = self.run_cmd([GH, "repo", "list", "--limit", "20", "--json",
                                    "nameWithOwner", "-q", ".[].nameWithOwner"])
                repos = [r.strip() for r in res.stdout.strip().split("\n") if r.strip()]
                if not repos:
                    self.log_widget.write("[yellow]No repos found.[/yellow]")
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
                        self.log_widget.write(f"[green]✅ Active Repo: {self.repo_actif}[/green]")

                options = [(r, r.split("/")[-1][:24]) for r in repos]
                self.push_screen(SelectionModal("CHOOSE A REPOSITORY", options), select_repo_callback)

        elif btn_id == "btn_clean_dl":
            if not DL_DIR.exists() or not os.listdir(DL_DIR):
                self.log_widget.write("[yellow]Downloads already empty.[/yellow]")
                return

            files = sorted(os.listdir(DL_DIR))
            self.log_widget.write(f"\n[yellow]📂 Contenu de downloads/:[/yellow]")
            for f in files:
                fpath = DL_DIR / f
                icon = "📁" if fpath.is_dir() else "📄"
                self.log_widget.write(f"  {icon} {f}")

            options = (
                [("__all__", "🗑  Supprimer TOUT")] +
                [(f, f"📄 Supprimer : {f}") for f in files]
            )

            def clean_action_cb(choice):
                if choice == "__all__":
                    def confirm_all(confirmed):
                        if confirmed:
                            for f in os.listdir(DL_DIR):
                                fp = DL_DIR / f
                                if fp.is_file():
                                    fp.unlink()
                                elif fp.is_dir():
                                    shutil.rmtree(fp)
                            self.log_widget.write("[green]✅ Downloads vide.[/green]")
                        else:
                            self.log_widget.write("[yellow]Annule.[/yellow]")
                    self.push_screen(
                        WarningModal("⚠ SUPPRIMER TOUT ?",
                            "Tous les fichiers de downloads/\nseront supprimes definitivement."),
                        confirm_all
                    )
                elif choice:
                    def confirm_one(confirmed):
                        if confirmed:
                            fp = DL_DIR / choice
                            if fp.is_file():
                                fp.unlink()
                            elif fp.is_dir():
                                shutil.rmtree(fp)
                            self.log_widget.write(f"[green]✅ {choice} supprime.[/green]")
                        else:
                            self.log_widget.write("[yellow]Annule.[/yellow]")
                    self.push_screen(
                        WarningModal(f"⚠ SUPPRIMER {choice} ?",
                            f"Le fichier {choice}\nsera supprime definitivement."),
                        confirm_one
                    )

            self.push_screen(SelectionModal("CLEAN DOWNLOADS - CHOISIR ACTION", options), clean_action_cb)

        elif btn_id == "btn_gitignore":
            if not self.check_repo_active():
                return
            repo_path = WORKDIR / self.repo_actif.split("/")[-1]
            gitignore_path = repo_path / ".gitignore"

            options = [
                ("add_simple",  "➕ Ajouter au .gitignore (fichier pas encore tracke)"),
                ("add_untrack", "⚠️  Ajouter + untrack (fichier deja sur GitHub)"),
                ("remove",      "🗑  Enlever une entree du .gitignore"),
            ]

            def gitignore_main_cb(choice):
                if choice == "add_simple":
                    self._gitignore_add_simple(repo_path, gitignore_path)
                elif choice == "add_untrack":
                    self._gitignore_add_untrack(repo_path, gitignore_path)
                elif choice == "remove":
                    self._gitignore_remove(repo_path, gitignore_path)

            self.push_screen(SelectionModal("GITIGNORE - CHOISIR UNE ACTION", options), gitignore_main_cb)

        elif btn_id == "btn_sync_fix":
            if not self.check_repo_active():
                return
            repo_path = WORKDIR / self.repo_actif.split("/")[-1]
            options = [
                ("stash", "🔒 Stash + Pull (garde les changements locaux)"),
                ("reset", "⚠  Reset Hard (ecrase le local avec GitHub)")
            ]
            def sync_choice_cb(choice):
                if choice == "stash":
                    res_stash = self.run_cmd([GIT, "stash"], cwd=repo_path)
                    self.log_widget.write(res_stash.stdout + res_stash.stderr)
                    res_pull = self.run_cmd([GIT, "pull"], cwd=repo_path)
                    self.log_widget.write(res_pull.stdout + res_pull.stderr)
                    self.log_widget.write("[green]✅ Stash + Pull termine.[/green]")
                elif choice == "reset":
                    def confirm_reset(confirmed):
                        if confirmed:
                            res_fetch = self.run_cmd([GIT, "fetch", "origin"], cwd=repo_path)
                            self.log_widget.write(res_fetch.stdout + res_fetch.stderr)
                            res_reset = self.run_cmd([GIT, "reset", "--hard", "origin/main"], cwd=repo_path)
                            self.log_widget.write(res_reset.stdout + res_reset.stderr)
                            self.log_widget.write("[green]✅ Reset hard termine.[/green]")
                        else:
                            self.log_widget.write("[yellow]Reset annule.[/yellow]")
                    self.push_screen(
                        WarningModal(
                            "⚠  ATTENTION - RESET HARD",
                            "Tous les changements locaux non commites\nseront PERDUS definitivement.\nContinuer ?"
                        ),
                        confirm_reset
                    )
            self.push_screen(SelectionModal("SYNC FIX - CHOISIR UNE STRATEGIE", options), sync_choice_cb)

        elif btn_id == "btn_browse":
            if not self.check_repo_active():
                return
            repo_path = WORKDIR / self.repo_actif.split("/")[-1]

            def browse_cb(selected_path):
                if selected_path:
                    try:
                        entries = sorted(selected_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
                        self.log_widget.write(f"\n[yellow]📂 Contenu de {selected_path.relative_to(WORKDIR)}:[/yellow]")
                        for entry in entries:
                            if entry.name.startswith("."):
                                continue
                            icon = "📁" if entry.is_dir() else "📄"
                            self.log_widget.write(f"  {icon} {entry.name}")
                    except Exception as e:
                        self.log_widget.write(f"[red]Erreur: {e}[/red]")

            self.push_screen(DirectoryModal(repo_path), browse_cb)

        elif btn_id in ["btn_pull", "btn_push", "btn_status", "btn_log", "btn_diff",
                        "btn_stash", "btn_restore", "btn_branch", "btn_reset", "btn_import"]:
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
                    self.log_widget.write(f"[yellow]Branch: {branch}[/yellow]")

                    def do_commit(msg):
                        if msg:
                            self.run_cmd([GIT, "add", "."], cwd=repo_path)
                            self.run_cmd([GIT, "commit", "-m", msg], cwd=repo_path)
                            res_p = self.run_cmd([GIT, "push"], cwd=repo_path)
                            self.log_widget.write(res_p.stdout + res_p.stderr)

                    self.push_screen(TextInputModal("COMMIT MESSAGE"), do_commit)

            elif btn_id == "btn_status":
                res = self.run_cmd([GIT, "status"], cwd=repo_path)
                self.log_widget.write(res.stdout)

            elif btn_id == "btn_log":
                res = self.run_cmd([GIT, "log", "--oneline", "-10"], cwd=repo_path)
                self.log_widget.write(res.stdout)

            elif btn_id == "btn_diff":
                res = self.run_cmd([GIT, "diff"], cwd=repo_path)
                self.log_widget.write(res.stdout if res.stdout else "[yellow]No changes.[/yellow]")

            elif btn_id == "btn_stash":
                options = [
                    ("1", "1) Stash changes"),
                    ("2", "2) Pop stash"),
                    ("3", "3) List stashes")
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
                modified = [l.strip().split()[-1] for l in stat.strip().split("\n") if l.strip()]
                options = [("all", "✨ Restore All")] + [(f, f"📄 {f}") for f in modified]

                def restore_cb(target):
                    if target == "all":
                        self.run_cmd([GIT, "restore", "."], cwd=repo_path)
                        self.log_widget.write("[green]Restored all files.[/green]")
                    elif target:
                        self.run_cmd([GIT, "restore", target], cwd=repo_path)
                        self.log_widget.write(f"[green]Restored {target}[/green]")
                self.push_screen(SelectionModal("RESTORE FILE", options), restore_cb)

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
                        self.push_screen(TextInputModal("NEW BRANCH NAME"),
                            lambda name: self.log_widget.write(
                                self.run_cmd([GIT, "checkout", "-b", name], cwd=repo_path).stdout if name else ""))
                    elif choice == "3":
                        avail = self.run_cmd([GIT, "branch"], cwd=repo_path).stdout
                        br_list = [b.replace("*", "").strip() for b in avail.strip().split("\n") if b.strip()]
                        self.push_screen(SelectionModal("CHECKOUT BRANCH",
                            [(b, f"🌿 {b}") for b in br_list]),
                            lambda name: self.log_widget.write(
                                self.run_cmd([GIT, "checkout", name], cwd=repo_path).stdout if name else ""))
                self.push_screen(SelectionModal("BRANCH MANAGEMENT", options), branch_cb)

            elif btn_id == "btn_reset":
                options = [("y", "Yes, undo last commit"), ("n", "No, keep it")]
                def reset_cb(ans):
                    if ans == "y":
                        self.log_widget.write(self.run_cmd([GIT, "reset", "HEAD~1"], cwd=repo_path).stdout)
                self.push_screen(SelectionModal("UNDO LAST COMMIT?", options), reset_cb)

            elif btn_id == "btn_import":
                if not DL_DIR.exists():
                    self.log_widget.write(f"[red]Downloads not found: {DL_DIR}[/red]")
                    return
                files = os.listdir(DL_DIR)
                if not files:
                    self.log_widget.write("[yellow]Downloads is empty.[/yellow]")
                    return

                def file_cb(filename):
                    if filename:
                        src = DL_DIR / filename
                        subdirs = [p for p in repo_path.rglob("*") if p.is_dir() and ".git" not in p.parts][:15]
                        dest_options = [("root", "🏠 Root (/)")] + [(str(p), f"📂 {p.relative_to(repo_path)}") for p in subdirs]
                        def dest_cb(d):
                            if d:
                                dest = repo_path if d == "root" else Path(d)
                                shutil.copy(src, dest / filename)
                                self.log_widget.write(f"[green]Copied {filename} → {dest.relative_to(repo_path)}[/green]")
                        self.push_screen(SelectionModal("CHOOSE DESTINATION", dest_options), dest_cb)
                self.push_screen(SelectionModal("SELECT FILE", [(f, f"📁 {f}") for f in files]), file_cb)

        elif btn_id == "btn_update_tool":
            options = [
                ("cli", "🖥  CLI  - git_tool.sh"),
                ("tui", "🖱  TUI  - git_tool_tui.py"),
            ]
            def update_choice_cb(choice):
                if ENV == "wsl":
                    if choice == "cli":
                        if shutil.which("update_git_wsl.sh"):
                            subprocess.run(["update_git_wsl.sh"])
                            self.log_widget.write("[green]✅ CLI updated via update_git_wsl.sh[/green]")
                        else:
                            self.log_widget.write("[red]update_git_wsl.sh not found in PATH.[/red]")
                    elif choice == "tui":
                        src = DL_DIR / "git_tool_tui.py"
                        if src.exists():
                            dest = WORKDIR / "scripts" / "git_tool_tui" / "git_tool_tui.py"
                            shutil.copy(src, dest)
                            self.log_widget.write(f"[green]✅ TUI updated at {dest}[/green]")
                        else:
                            self.log_widget.write(f"[red]Not found: {src}[/red]")
                else:
                    if choice == "cli":
                        src = DL_DIR / "git_tool.sh"
                        if src.exists():
                            self.unlock_hosts()
                            shutil.copy(src, TOOL_BIN / "git_tool.sh")
                            (TOOL_BIN / "git_tool.sh").chmod(0o755)
                            self.lock_hosts()
                            self.log_widget.write("[green]✅ CLI updated in $PREFIX/bin/[/green]")
                        else:
                            self.log_widget.write(f"[red]Not found: {src}[/red]")
                    elif choice == "tui":
                        src = DL_DIR / "git_tool_tui.py"
                        if src.exists():
                            dest = WORKDIR / "scripts" / "git_tool_tui" / "git_tool_tui.py"
                            shutil.copy(src, dest)
                            self.log_widget.write(f"[green]✅ TUI updated at {dest}[/green]")
                        else:
                            self.log_widget.write(f"[red]Not found: {src}[/red]")

            self.push_screen(SelectionModal("UPDATE TOOL - CHOISIR VERSION", options), update_choice_cb)


if __name__ == "__main__":
    app = GitToolApp()
    app.run()
