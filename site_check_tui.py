import os
import re
import datetime
import random
import string
import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Input, Button, RichLog, Label
from textual.screen import ModalScreen

class SiteInputDialog(ModalScreen[str]):
    """A reusable pop-up modal to input or change the target website."""
    
    CSS = """
    SiteInputDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }

    #dialog_box {
        width: 40;
        height: auto;
        padding: 1;
        background: #242424;
        border: thick #3498db;
    }

    #dialog_box Label {
        text-style: bold;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
        color: #3498db;
    }

    #dialog_box Input {
        margin-bottom: 1;
    }

    #dialog_buttons {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog_box"):
            yield Label("Configuration du Site")
            yield Input(placeholder="Ex: cleanviewqc.com", id="modal_site_input")
            with Container(id="dialog_buttons"):
                yield Button("Valider", variant="success", id="btn_confirm")
                yield Button("Annuler", variant="error", id="btn_cancel")

    def on_mount(self) -> None:
        self.query_one("#modal_site_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm":
            site_value = self.query_one("#modal_site_input", Input).value.strip()
            self.dismiss(site_value)
        elif event.button.id == "btn_cancel":
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())


class SiteCheckApp(App):
    """Asynchronous streaming optimization to log results instantly."""
    
    CSS = """
    Screen {
        background: #1a1a1a;
    }
    
    #main_layout {
        height: 1fr;
        width: 100%;
    }
    
    #sidebar {
        width: 8;
        height: 100%;
        background: #242424;
        border-right: solid #3498db;
        padding: 1 0;
    }
    
    #sidebar Label {
        text-style: bold;
        text-align: center;
        color: #3498db;
        margin-bottom: 1;
        width: 100%;
    }
    
    #button_tray {
        width: 100%;
        height: 1fr;
        scrollbar-gutter: stable;
        padding: 0 1;
    }

    #button_tray Button {
        min-width: 100%;
        width: 100%;
        margin-bottom: 1;
        height: 3;
        padding: 0;
        content-align: center middle;
        border: none;
    }
    
    #output_container {
        width: 1fr;
        height: 100%;
    }
    
    RichLog {
        margin: 1;
        border: solid #444;
        background: #0f0f0f;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quitter"),
        ("c", "clear_log", "Effacer Log"),
        ("s", "change_site", "Changer Site"),
        ("a", "run_all_diagnostics", "Tout Lancer"),
        ("h", "show_help_menu", "Index Fonctions")
    ]

    def on_mount(self) -> None:
        if os.path.exists("/data/data/com.com.termux") or os.path.exists("/data/data/com.termux"):
            self.env = "termux"
            self.work_dir = Path.home() / "tool_projects/site-diagnostic"
        else:
            self.env = "ubuntu"
            self.work_dir = Path.home() / "site-diagnostic"
            
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        session_id = "".join(random.choices(string.ascii_lowercase, k=6))
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file_path = self.work_dir / f"session_{timestamp}_{session_id}.log"
        
        self.target_site = ""
        
        self.write_to_log(f"[bold blue]Dossier de travail :[/] {self.work_dir}")
        self.write_to_log(f"[bold blue]Session de log active :[/] {self.log_file_path}\n")
        self.action_show_help_menu()
        self.action_change_site()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(id="main_layout"):
            with Vertical(id="sidebar"):
                yield Label("MENU")
                with ScrollableContainer(id="button_tray"):
                    yield Button("S", id="btn_change_site", variant="default")
                    yield Button("?", id="btn_help", variant="warning")
                    yield Button("0", id="btn_run_all", variant="success")
                    yield Button("1", id="btn_dns", variant="primary")
                    yield Button("2", id="btn_ping", variant="primary")
                    yield Button("3", id="btn_http", variant="primary")
                    yield Button("4", id="btn_headers", variant="primary")
                    yield Button("5", id="btn_trace", variant="primary")
                    yield Button("6", id="btn_whois", variant="primary")
                    yield Button("7", id="btn_sec", variant="primary")
                    yield Button("8", id="btn_perf", variant="primary")
            
            with Container(id="output_container"):
                yield RichLog(id="output_log", highlight=True, markup=True)
                
        yield Footer()

    def print_target_status(self) -> None:
        site_str = f"[bold underline cyan]{self.target_site}[/]" if self.target_site else "[bold red][Aucun][/]"
        self.write_to_log(f"[bold]>>> SITE TARGET ACTIF :[/] {site_str}\n")

    def action_change_site(self) -> None:
        def handle_site_selection(chosen_site: str) -> None:
            if chosen_site:
                cleaned = re.sub(r"^https?://", "", chosen_site)
                cleaned = re.sub(r"/+$", "", cleaned)
                
                self.target_site = cleaned
                self.write_to_log(f"[bold green][SITE MIS À JOUR][/]")
                self.print_target_status()

        self.push_screen(SiteInputDialog(), handle_site_selection)

    def action_show_help_menu(self) -> None:
        self.write_to_log("\n[bold cyan]==================================================[/]")
        self.write_to_log("[bold cyan]       INDEX DES FONCTIONS DE DIAGNOSTIC SITE     [/]")
        self.write_to_log("[bold cyan]==================================================[/]")
        self.print_target_status()
        self.write_to_log("  [bold yellow]Bouton [S] / Touche [s][/] : Ouvrir la boîte de dialogue de configuration")
        self.write_to_log("  [bold yellow]?[/] : Afficher cet index d'aide des commandes")
        self.write_to_log("  [bold green]0[/] : Tout Lancer ([bold]RUN ALL[/]) de 1 à 8 séquentiellement")
        self.write_to_log("  [bold blue]1[/] : [bold]DNS[/] - Résolution d'adresse IP (dig)")
        self.write_to_log("  [bold blue]2[/] : [bold]PING[/] - Test de paquets et calcul de latence moyenne")
        self.write_to_log("  [bold blue]3[/] : [bold]HTTP/SSL[/] - État du code HTTP et validité SSL")
        self.write_to_log("  [bold blue]4[/] : [bold]En-têtes[/] - Inspection des serveurs backend")
        self.write_to_log("  [bold blue]5[/] : [bold]Traceroute[/] - Route d'acheminement réseau complet")
        self.write_to_log("  [bold blue]6[/] : [bold]WHOIS[/] - Données d'enregistrement du domaine")
        self.write_to_log("  [bold blue]7[/] : [bold]Sécurité[/] - Audit des en-têtes (HSTS, CSP, X-Frame)")
        self.write_to_log("  [bold blue]8[/] : [bold]Perf[/] - Analyse des temps de réponse (TTFB, DNS, TCP)")
        self.write_to_log("[bold cyan]==================================================[/]\n")

    def write_to_log(self, message: str) -> None:
        try:
            log_widget = self.query_one("#output_log", RichLog)
            log_widget.write(message)
        except Exception:
            pass
            
        clean_msg = re.sub(r"\[.*?\]", "", message)
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(clean_msg + "\n")

    def action_clear_log(self) -> None:
        self.query_one("#output_log", RichLog).clear()

    def action_run_all_diagnostics(self) -> None:
        if self.target_site:
            self.run_worker(self.run_all_sequence(self.target_site))
        else:
            self.write_to_log("[bold red][ERREUR][/] Veuillez d'abord configurer une cible via le bouton [S] ou la touche [s].")

    async def run_all_sequence(self, site: str) -> None:
        self.write_to_log(f"\n[bold yellow]>>> DÉBUT DE L'ANALYSE COMPLÈTE POUR: {site} <<<[/]")
        await self.check_dns(site)
        await self.check_ping(site)
        await self.check_http(site)
        await self.check_headers(site)
        await self.check_trace(site)
        await self.check_whois(site)
        await self.check_security(site)
        await self.check_performance(site)
        self.write_to_log(f"\n[bold yellow]>>> FIN DE L'ANALYSE COMPLÈTE <<<[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "btn_change_site":
            self.action_change_site()
            return
            
        if btn_id == "btn_help":
            self.action_show_help_menu()
            return

        if not self.target_site:
            self.write_to_log("[bold red][ERREUR][/] Aucun site configuré. Appuyez sur [S] pour configurer une cible.")
            return
            
        site = self.target_site

        if btn_id == "btn_run_all":
            self.run_worker(self.run_all_sequence(site))
            return

        # Use Textual Worker thread pool to execute asynchronously and avoid GUI locks
        if btn_id == "btn_dns":
            self.run_worker(self.check_dns(site))
        elif btn_id == "btn_ping":
            self.run_worker(self.check_ping(site))
        elif btn_id == "btn_http":
            self.run_worker(self.check_http(site))
        elif btn_id == "btn_headers":
            self.run_worker(self.check_headers(site))
        elif btn_id == "btn_trace":
            self.run_worker(self.check_trace(site))
        elif btn_id == "btn_whois":
            self.run_worker(self.check_whois(site))
        elif btn_id == "btn_sec":
            self.run_worker(self.check_security(site) or asyncio.sleep(0))
        elif btn_id == "btn_perf":
            self.run_worker(self.check_performance(site))

    async def async_run_cmd(self, args: list) -> str:
        """Executes system calls asynchronously to keep output logs flowing in real-time."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return stdout.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"Error executing command: {str(e)}"

    # --- 1. DNS ---
    async def check_dns(self, site: str) -> None:
        self.write_to_log("\n--- Resolution DNS ---")
        if getattr(self, 'env', 'ubuntu') == "termux":
            out = await self.async_run_cmd(["dig", "+short", site])
            if out.strip():
                self.write_to_log("[green][OK][/] Le domaine résout vers :")
                for ip in out.strip().splitlines():
                    self.write_to_log(f"    {ip}")
            else:
                self.write_to_log("[red][ECHEC][/] Aucune résolution DNS ou 'dig' non trouvé.")
        else:
            out = await self.async_run_cmd(["dig", "+short", site])
            if out.strip():
                self.write_to_log("[green][OK][/] Le domaine résout vers :")
                for ip in out.strip().splitlines():
                    self.write_to_log(f"    {ip}")
            else:
                self.write_to_log("[red][ECHEC][/] Aucune résolution DNS trouvée.")

    # --- 2. PING ---
    async def check_ping(self, site: str) -> None:
        self.write_to_log("\n--- Test PING (latence réseau) ---")
        out = await self.async_run_cmd(["ping", "-c", "5", site])
        
        if "100% packet loss" in out or not out.strip():
            self.write_to_log("[red][ECHEC][/] Le site ne répond pas au ping.")
        elif "bytes from" in out:
            self.write_to_log("[green][OK][/] Le site répond au ping.")
            stats = re.search(r"min/avg/max/\w+\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)", out)
            if stats:
                min_t, avg_t, max_t = stats.groups()
                self.write_to_log(f"    Latence moyenne : {avg_t} ms")
                self.write_to_log(f"    Min / Max       : {min_t} ms / {max_t} ms")
            else:
                self.write_to_log("    (Statistiques détaillées non disponibles)")

    # --- 3. HTTP STATUS ---
    async def check_http(self, site: str) -> None:
        self.write_to_log("\n--- Test HTTP/HTTPS (état réel) ---")
        fmt = "%{http_code} %{time_total} %{ssl_verify_result} %{url_effective}"
        out = await self.async_run_cmd(["curl", "-sL", "-o", "/dev/null", "-w", fmt, "--max-time", "10", f"https://{site}"])
        
        parts = out.strip().split()
        if not parts or parts[0] == "000":
            self.write_to_log("[red][ECHEC][/] Aucune réponse HTTP reçue.")
            return
            
        code, time_total, ssl_ok, url_final = parts[0], parts[1], parts[2], parts[3]
        
        if code == "200":
            self.write_to_log("[green][OK][/] Code HTTP 200 - le site répond normalement.")
        elif code in ["301", "302", "307", "308"]:
            self.write_to_log(f"[yellow][REDIRECTION][/] Code HTTP {code} - le site redirige.")
        else:
            self.write_to_log(f"[red][ERREUR] Code HTTP {code}.")
            
        self.write_to_log(f"    Temps de réponse total : {time_total}s")
        self.write_to_log(f"    URL finale             : {url_final}")
        self.write_to_log("[green][OK][/] Certificat SSL valide." if ssl_ok == "0" else "[red][ATTENTION][/] Problème avec le certificat SSL.")

    # --- 4. HEADERS GENERAUX ---
    async def check_headers(self, site: str) -> None:
        self.write_to_log("\n--- En-têtes principaux ---")
        out = await self.async_run_cmd(["curl", "-sIL", "--max-time", "10", f"https://{site}"])
        
        server = re.search(r"(?i)^server:\s*(.*)", out, re.M)
        vercel = re.search(r"(?i)^x-vercel-id:\s*(.*)", out, re.M)
        
        if server:
            self.write_to_log(f"    Serveur       : {server.group(1).strip()}")
        if vercel:
            self.write_to_log(f"    Région Vercel : {vercel.group(1).strip()}")
        if not server and not vercel:
            self.write_to_log("    [yellow][INFO][/] Aucun en-tête reconnu trouvé.")

    # --- 5. TRACEROUTE ---
    async def check_trace(self, site: str) -> None:
        self.write_to_log("\n--- Traceroute (chemin réseau) ---")
        out = await self.async_run_cmd(["traceroute", "-m", "15", "-w", "2", site])
        lines = [l for l in out.splitlines() if re.match(r"^\s*\d+", l)]
        total_hops = len(lines)
        
        if total_hops > 0:
            self.write_to_log(f"[green][OK][/] Trajet tracé en {total_hops} sauts.")
            self.write_to_log("    Derniers sauts :")
            for line in lines[-5:]:
                self.write_to_log(f"    {line.strip()}")
        else:
            self.write_to_log("[yellow][INCONNU ou ABSENT][/] Impossible de tracer le chemin.")

    # --- 6. WHOIS ---
    async def check_whois(self, site: str) -> None:
        self.write_to_log("\n--- Informations du domaine (WHOIS) ---")
        out = await self.async_run_cmd(["whois", site])
        reg = re.search(r"(?i)^Registrar:\s*(.*)", out, re.M)
        exp = re.search(r"(?i)^(?:Registry Expiry Date|Expiry Date|Expiration Date):\s*(.*)", out, re.M)
        cre = re.search(r"(?i)^(?:Creation Date|Created):\s*(.*)", out, re.M)
        
        if reg or exp:
            self.write_to_log("[green][OK][/] Informations trouvées.")
            if reg: self.write_to_log(f"    Registrar  : {reg.group(1).strip()}")
            if cre: self.write_to_log(f"    Créé le    : {cre.group(1).strip()}")
            if exp: self.write_to_log(f"    Expire le  : {exp.group(1).strip()}")
        else:
            self.write_to_log("[yellow][INCONNU ou ABSENT][/] Aucune information WHOIS standard trouvée.")

    # --- 7. SECURITE ---
    async def check_security(self, site: str) -> None:
        self.write_to_log("\n--- En-têtes de sécurité ---")
        out = await self.async_run_cmd(["curl", "-sIL", "--max-time", "10", f"https://{site}"])
        
        sec_headers = {
            "strict-transport-security": "Force HTTPS (HSTS)",
            "x-content-type-options": "Empêche le MIME-sniffing",
            "x-frame-options": "Protection contre le clickjacking",
            "content-security-policy": "Politique de sécurité du contenu (CSP)",
            "referrer-policy": "Contrôle des infos de référent envoyées"
        }
        
        for h, desc in sec_headers.items():
            if re.search(f"(?i)^{h}:", out, re.M):
                self.write_to_log(f"    [green][PRESENT][/] {h} - {desc}")
            else:
                self.write_to_log(f"    [yellow][ABSENT][/]  {h} - {desc}")

    # --- 8. PERFORMANCE ---
    async def check_performance(self, site: str) -> None:
        self.write_to_log("\n--- Performance détaillée ---")
        fmt = "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total} %{url_effective}"
        out_t = await self.async_run_cmd(["curl", "-sL", "-o", "/dev/null", "-w", fmt, "--max-time", "15", f"https://{site}"])
        
        parts = out_t.strip().split()
        if not parts or parts[4] == "0.000000":
            self.write_to_log("[red][ECHEC][/] Impossible de mesurer la performance.")
            return
            
        self.write_to_log(f"    URL finale          : {parts[5]}")
        self.write_to_log(f"    Résolution DNS      : {parts[0]}s")
        self.write_to_log(f"    Connexion TCP       : {parts[1]}s")
        self.write_to_log(f"    Handshake TLS       : {parts[2]}s")
        self.write_to_log(f"    Premier octet reçu  : {parts[3]}s")
        self.write_to_log(f"    Temps total         : {parts[4]}s")

if __name__ == "__main__":
    SiteCheckApp().run()
