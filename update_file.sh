#!/bin/bash

if [ -z "$1" ]; then
    read -p "File name: " FILE
else
    FILE="$1"
fi

echo "Choisir le repo de destination :"
echo "  1) Cleanview"
echo "  2) CustomScripts-"
read -p "Choix : " REPO_CHOIX

case $REPO_CHOIX in
    1) DEST_REPO="Cleanview" ;;
    2) DEST_REPO="CustomScripts-" ;;
    *) echo "Choix invalide"; exit 1 ;;
esac

cp "$HOME/downloads/$FILE" "$HOME/push_to_git/$DEST_REPO/$FILE"

if [ $? -eq 0 ]; then
    echo -e "\033[32m[OK]\033[0m $FILE copié vers $DEST_REPO/"
else
    echo -e "\033[31m[ECHEC]\033[0m Impossible de copier $FILE"
fi
