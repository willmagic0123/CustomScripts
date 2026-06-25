#!/bin/bash

# --- Detection environnement ---
if [ -d "/data/data/com.termux" ]; then
    ENV="termux"
    GH="/data/data/com.termux/files/usr/bin/gh"
    GIT="/data/data/com.termux/files/usr/bin/git"
    WORKDIR="/data/data/com.termux/files/home/push_to_git"
    TOOL_BIN="$PREFIX/bin"
    HOSTS_YML="/data/data/com.termux/files/home/.config/gh/hosts.yml"
else
    ENV="wsl"
    GH=$(which gh)
    GIT=$(which git)
    WORKDIR="/home/linux_admin/Github/top-repo"
    TOOL_BIN="/usr/local/bin"
    HOSTS_YML="$HOME/.config/gh/hosts.yml"
fi

REPO_ACTIF=""

sigint_signal() {
    echo -e "\nProcess ended."; exit 1
}

trap sigint_signal SIGINT

cd "$WORKDIR"

echo -e "\033[33m[ENV]\033[0m Environnement detecte : $ENV"

# --- Gestion hosts.yml ---
unlock_hosts() {
    chmod 600 "$HOSTS_YML" 2>/dev/null
}

lock_hosts() {
    chmod 400 "$HOSTS_YML" 2>/dev/null
}

# --- Verification connexion internet ---
check_network() {
    if ! ping -c 1 -W 2 github.com &>/dev/null; then
        echo -e "\033[31m❌ Pas de connexion internet. Verifie ton reseau.\033[0m"
        return 1
    fi
    return 0
}

connect() {
    check_network || return
    unlock_hosts
    $GH auth login
    if [ "$ENV" = "wsl" ]; then
        $GH auth setup-git
    fi
    lock_hosts
}

disconnect() {
    unlock_hosts
    $GH auth logout
    lock_hosts
}

conn_status() {
    check_network || return
    unlock_hosts
    $GH auth status
    lock_hosts
}

choisir_repo() {
    check_network || return
    echo -e "\033[33m\nChargement de tes repos...\033[0m"
    unlock_hosts
    mapfile -t REPOS < <($GH repo list --limit 20 --json nameWithOwner -q '.[].nameWithOwner')
    lock_hosts

    if [ ${#REPOS[@]} -eq 0 ]; then
        echo "Aucun repo trouvé. Es-tu connecté ? (option 1)"
        return
    fi

    echo -e "\033[33m\nChoisis un repo :\033[0m"
    for i in "${!REPOS[@]}"; do
        echo "  $((i+1))) ${REPOS[$i]}"
    done
    echo ""

    read -p $'\033[34m[git_tool.sh] Numéro du repo >>\033[0m ' num
    if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#REPOS[@]}" ]; then
        REPO_ACTIF="${REPOS[$((num-1))]}"
        REPO_NOM=$(basename "$REPO_ACTIF")

        if [ ! -d "$WORKDIR/$REPO_NOM" ]; then
            echo -e "\033[33mClonage de $REPO_ACTIF...\033[0m"
            unlock_hosts
            $GH repo clone "$REPO_ACTIF" "$WORKDIR/$REPO_NOM"
            lock_hosts
        fi

        echo -e "\033[32m✅ Repo actif : $REPO_ACTIF\033[0m"
    else
        echo "Choix invalide."
    fi
}

verifier_repo() {
    if [ -z "$REPO_ACTIF" ]; then
        echo -e "\033[31m❌ Aucun repo sélectionné. Utilise l'option 4 d'abord.\033[0m"
        return 1
    fi
    return 0
}

pull_repo() {
    verifier_repo || return
    check_network || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    unlock_hosts
    cd "$WORKDIR/$REPO_NOM" && $GIT pull
    lock_hosts
    cd "$WORKDIR"
}

push_repo() {
    verifier_repo || return
    check_network || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"

    BRANCH=$($GIT branch --show-current)
    echo -e "\033[33m[INFO]\033[0m Branche courante : $BRANCH"
    if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
        read -p "Tu n'es pas sur main/master. Continuer quand meme ? (o/n) : " CONFIRM
        if [ "$CONFIRM" != "o" ]; then
            echo -e "\033[33m[INFO]\033[0m Push annule."
            cd "$WORKDIR"
            return
        fi
    fi

    $GIT add .
    read -p "Message du commit : " msg
    unlock_hosts
    $GIT commit -m "$msg"
    $GIT push
    lock_hosts
    cd "$WORKDIR"
}

repo_status() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- Status du repo ---"
    $GIT status
    cd "$WORKDIR"
}

repo_log() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- 10 derniers commits ---"
    $GIT log --oneline -10
    cd "$WORKDIR"
}

repo_diff() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- Differences locales ---"
    $GIT diff
    cd "$WORKDIR"
}

repo_stash() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- Gestion du stash ---"
    echo -ne "\033[33m"
    echo "  1) Mettre de cote les modifications (stash)"
    echo "  2) Recuperer les modifications (stash pop)"
    echo "  3) Voir la liste des stashs"
    echo "  0) Annuler"
    echo -ne "\033[0m"
    read -p "Choix : " stash_choix
    case $stash_choix in
        1) $GIT stash; echo -e "\033[32m[OK]\033[0m Modifications mises de cote." ;;
        2) $GIT stash pop; echo -e "\033[32m[OK]\033[0m Modifications recuperees." ;;
        3) $GIT stash list ;;
        0) echo "Annule." ;;
        *) echo "Choix invalide." ;;
    esac
    cd "$WORKDIR"
}

repo_restore() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- Fichiers modifies ---"
    $GIT status --short
    echo ""
    read -p "Nom du fichier a restaurer (ou 'all' pour tout restaurer) : " FICHIER
    if [ "$FICHIER" = "all" ]; then
        read -p "Restaurer TOUS les fichiers modifies ? Les changements seront perdus. (o/n) : " CONFIRM
        if [ "$CONFIRM" = "o" ]; then
            $GIT restore .
            echo -e "\033[32m[OK]\033[0m Tous les fichiers restaures."
        else
            echo -e "\033[33m[INFO]\033[0m Restauration annulee."
        fi
    elif [ -n "$FICHIER" ]; then
        $GIT restore "$FICHIER"
        echo -e "\033[32m[OK]\033[0m $FICHIER restaure."
    else
        echo -e "\033[31m❌ Nom de fichier vide.\033[0m"
    fi
    cd "$WORKDIR"
}

repo_branch() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- Gestion des branches ---"
    echo -ne "\033[33m"
    echo "  1) Voir toutes les branches"
    echo "  2) Creer une nouvelle branche"
    echo "  3) Changer de branche"
    echo "  0) Annuler"
    echo -ne "\033[0m"
    read -p "Choix : " branch_choix
    case $branch_choix in
        1)
            echo ""
            $GIT branch -a
            ;;
        2)
            read -p "Nom de la nouvelle branche : " NOM_BRANCHE
            if [ -n "$NOM_BRANCHE" ]; then
                $GIT checkout -b "$NOM_BRANCHE"
                echo -e "\033[32m[OK]\033[0m Branche '$NOM_BRANCHE' creee et activee."
            else
                echo -e "\033[31m❌ Nom de branche vide.\033[0m"
            fi
            ;;
        3)
            echo ""
            echo "Branches disponibles :"
            $GIT branch
            echo ""
            read -p "Nom de la branche : " NOM_BRANCHE
            if [ -n "$NOM_BRANCHE" ]; then
                $GIT checkout "$NOM_BRANCHE"
            else
                echo -e "\033[31m❌ Nom de branche vide.\033[0m"
            fi
            ;;
        0) echo "Annule." ;;
        *) echo "Choix invalide." ;;
    esac
    cd "$WORKDIR"
}

repo_reset() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    echo ""
    echo "--- Annuler le dernier commit ---"
    echo "Dernier commit :"
    $GIT log --oneline -1
    echo ""
    read -p "Annuler ce commit ? Les fichiers resteront modifies localement. (o/n) : " CONFIRM
    if [ "$CONFIRM" = "o" ]; then
        $GIT reset HEAD~1
        echo -e "\033[32m[OK]\033[0m Dernier commit annule. Fichiers toujours presents localement."
    else
        echo -e "\033[33m[INFO]\033[0m Annulation abandonnee."
    fi
    cd "$WORKDIR"
}

update_file() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    REPO_PATH="$WORKDIR/$REPO_NOM"

    if [ "$ENV" = "wsl" ]; then
        DL_DIR="/mnt/c/Users/Dev1d/OneDrive/Bureau/Downloads"
    else
        DL_DIR="$HOME/downloads"
    fi

    echo -e "\033[33mFichiers disponibles dans $DL_DIR :\033[0m"
    ls "$DL_DIR/"
    echo ""
    read -p "Nom du fichier : " FILE

    if [ -z "$FILE" ]; then
        echo -e "\033[31m❌ Nom de fichier vide.\033[0m"
        return
    fi

    SRC="$DL_DIR/$FILE"

    if [ ! -f "$SRC" ]; then
        echo -e "\033[31m❌ Fichier introuvable : $SRC\033[0m"
        return
    fi

    echo -e "\033[33m\nDestination dans $REPO_NOM/ :\033[0m"
    echo "  1) Racine ($REPO_NOM/)"

    mapfile -t SOUS_DOSSIERS < <(find "$REPO_PATH" -mindepth 1 -maxdepth 2 -type d ! -path "*/.git*" | sort)

    for i in "${!SOUS_DOSSIERS[@]}"; do
        AFFICHAGE="${SOUS_DOSSIERS[$i]#$REPO_PATH/}"
        echo "  $((i+2))) $AFFICHAGE/"
    done
    echo ""

    read -p "Choix de destination : " DEST_CHOIX

    if [ "$DEST_CHOIX" = "1" ]; then
        DEST_DIR="$REPO_PATH"
    elif [[ "$DEST_CHOIX" =~ ^[0-9]+$ ]] && [ "$DEST_CHOIX" -ge 2 ] && [ "$DEST_CHOIX" -le "$((${#SOUS_DOSSIERS[@]}+1))" ]; then
        DEST_DIR="${SOUS_DOSSIERS[$((DEST_CHOIX-2))]}"
    else
        echo -e "\033[31m❌ Choix invalide.\033[0m"
        return
    fi

    cp "$SRC" "$DEST_DIR/$FILE"
    if [ $? -eq 0 ]; then
        AFFICHAGE_DEST="${DEST_DIR#$WORKDIR/}"
        echo -e "\033[32m[OK]\033[0m $FILE copié vers $AFFICHAGE_DEST/"
    else
        echo -e "\033[31m[ÉCHEC]\033[0m Impossible de copier $FILE"
    fi
}

clean_downloads() {
    echo ""

    if [ "$ENV" = "wsl" ]; then
        DL_DIR="/mnt/c/Users/Dev1d/OneDrive/Bureau/Downloads"
    else
        DL_DIR="$HOME/downloads"
    fi

    FILES=$(ls "$DL_DIR/" 2>/dev/null)

    if [ -z "$FILES" ]; then
        echo -e "\033[33m[INFO]\033[0m Le dossier $DL_DIR est deja vide."
        echo ""
        return
    fi

    echo "Fichiers trouves dans $DL_DIR :"
    echo "$FILES" | while read -r f; do
        echo "    $f"
    done

    echo ""
    read -p "Confirmer la suppression de tous ces fichiers ? (o/n) : " CONFIRM

    if [ "$CONFIRM" = "o" ]; then
        rm -f "$DL_DIR"/*
        echo -e "\033[32m[OK]\033[0m Fichiers supprimes."
    else
        echo -e "\033[33m[INFO]\033[0m Suppression annulee."
    fi
    echo ""
}

update_git_tool() {
    echo ""
    if [ "$ENV" = "wsl" ]; then
        if command -v update_git_wsl.sh &>/dev/null; then
            update_git_wsl.sh
        else
            echo -e "\033[31m❌ update_git_wsl.sh introuvable dans le PATH.\033[0m"
        fi
    else
        SRC="$HOME/downloads/git_tool.sh"
        if [ ! -f "$SRC" ]; then
            echo -e "\033[31m❌ git_tool.sh introuvable : $SRC\033[0m"
            echo -e "\033[33m[INFO]\033[0m Place la nouvelle version dans ~/downloads/ et reessaie."
            echo ""
            return
        fi
        unlock_hosts
        cp "$SRC" "$TOOL_BIN/git_tool.sh"
        chmod +x "$TOOL_BIN/git_tool.sh"
        lock_hosts
        if [ $? -eq 0 ]; then
            echo -e "\033[32m[OK]\033[0m git_tool.sh mis a jour dans $TOOL_BIN/"
            echo -e "\033[33m[INFO]\033[0m Relance le script pour utiliser la nouvelle version."
        else
            echo -e "\033[31m❌ Echec de la mise a jour.\033[0m"
        fi
    fi
    echo ""
}

show_prompt() {
    if [ -n "$REPO_ACTIF" ]; then
        REPO_NOM=$(basename "$REPO_ACTIF")
        REPO_PATH="$WORKDIR/$REPO_NOM"
        if [ -d "$REPO_PATH" ]; then
            BRANCH=$(cd "$REPO_PATH" && $GIT branch --show-current 2>/dev/null)
            MODIFS=$(cd "$REPO_PATH" && $GIT status --short 2>/dev/null | wc -l | xargs)
            printf '\033[34m[git_tool.sh | %s | %s modifs] >>\033[0m ' "$BRANCH" "$MODIFS"
            return
        fi
    fi
    printf '\033[34m[git_tool.sh] >>\033[0m '
}

show_menu() {
    echo -ne "\033[33m"
    cat << EOF

1)  connect
2)  disconnect
3)  connection status
4)  choisir un repo${REPO_ACTIF:+ (actif : $REPO_ACTIF)}
5)  pull (mettre à jour)
6)  push (envoyer les changements)
7)  mettre a jour un fichier depuis downloads/
8)  nettoyer downloads/
9)  status du repo
10) log des commits
11) diff (modifications locales)
12) stash (mettre de cote)
13) restore (annuler modifications d'un fichier)
14) branch (gestion des branches)
15) reset (annuler le dernier commit)
16) mettre a jour git_tool.sh
menu) réafficher les options
0)  quit

EOF
    echo -ne "\033[0m"
}

show_menu

while true; do
    show_prompt
    read -r choix
    case $choix in
        1) connect ;;
        2) disconnect ;;
        3) conn_status ;;
        4) choisir_repo ;;
        5) pull_repo ;;
        6) push_repo ;;
        7) update_file ;;
        8) clean_downloads ;;
        9) repo_status ;;
        10) repo_log ;;
        11) repo_diff ;;
        12) repo_stash ;;
        13) repo_restore ;;
        14) repo_branch ;;
        15) repo_reset ;;
        16) update_git_tool ;;
        menu) show_menu ;;
        0) exit 0 ;;
        *) echo "Choix invalide" ;;
    esac
    echo
done
