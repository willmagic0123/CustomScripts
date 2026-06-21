#!/bin/bash

GH="/data/data/com.termux/files/usr/bin/gh"
GIT="/data/data/com.termux/files/usr/bin/git"
WORKDIR="/data/data/com.termux/files/home/push_to_git"
REPO_ACTIF=""

sigint_signal() {
    echo -e "\nProcess ended."; exit 1
}

trap sigint_signal SIGINT

cd "$WORKDIR"

connect() {
    $GH auth login
    chmod 400 /data/data/com.termux/files/home/.config/gh/hosts.yml
}

disconnect() {
    chmod 600 /data/data/com.termux/files/home/.config/gh/hosts.yml
    $GH auth logout
}

conn_status() {
    $GH auth status
}

choisir_repo() {
    echo -e "\033[33m\nChargement de tes repos...\033[0m"
    mapfile -t REPOS < <($GH repo list --limit 20 --json nameWithOwner -q '.[].nameWithOwner')

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

        # Cloner si pas déjà présent
        if [ ! -d "$WORKDIR/$REPO_NOM" ]; then
            echo -e "\033[33mClonage de $REPO_ACTIF...\033[0m"
            $GH repo clone "$REPO_ACTIF" "$WORKDIR/$REPO_NOM"
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
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM" && $GIT pull
    cd "$WORKDIR"
}

push_repo() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")
    cd "$WORKDIR/$REPO_NOM"
    $GIT add .
    read -p "Message du commit : " msg
    $GIT commit -m "$msg"
    $GIT push
    cd "$WORKDIR"
}

update_file() {
    verifier_repo || return
    REPO_NOM=$(basename "$REPO_ACTIF")

    ls ~/downloads/
    read -p "Nom du fichier (dans ~/downloads/) : " FILE

    if [ -z "$FILE" ]; then
        echo -e "\033[31m❌ Nom de fichier vide.\033[0m"
        return
    fi

    SRC="$HOME/downloads/$FILE"
    DEST="$WORKDIR/$REPO_NOM/$FILE"

    if [ ! -f "$SRC" ]; then
        echo -e "\033[31m❌ Fichier introuvable : $SRC\033[0m"
        return
    fi

    cp "$SRC" "$DEST"
    if [ $? -eq 0 ]; then
        echo -e "\033[32m[OK]\033[0m $FILE copié vers $REPO_NOM/"
    else
        echo -e "\033[31m[ÉCHEC]\033[0m Impossible de copier $FILE"
    fi
}

show_menu() {
    echo -ne "\033[33m"
    cat << EOF

1) connect
2) disconnect
3) connection status
4) choisir un repo${REPO_ACTIF:+ (actif : $REPO_ACTIF)}
5) pull (mettre à jour)
6) push (envoyer les changements)
7) mettre a jour un fichier depuis ~/downloads/
menu) réafficher les options
0) quit

EOF
    echo -ne "\033[0m"
}

show_menu

while true; do
    read -p $'\033[34m[git_tool.sh] >>\033[0m ' choix
    case $choix in
        1) connect ;;
        2) disconnect ;;
        3) conn_status ;;
        4) choisir_repo ;;
        5) pull_repo ;;
        6) push_repo ;;
        7) update_file ;;
        menu) show_menu ;;
        0) exit 0 ;;
        *) echo "Choix invalide" ;;
    esac
    echo
done
