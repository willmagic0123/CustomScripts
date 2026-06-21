#!/bin/bash

# Analyseur de logs de session
# Compatible Termux et Ubuntu WSL

# ============================================================
# DÉTECTION DE L'ENVIRONNEMENT
# ============================================================

if [ -d "/data/data/com.termux" ]; then
    ENV="termux"
    LOG_DIR="$HOME/tool_projects/site-diagnostic"
else
    ENV="ubuntu"
    LOG_DIR="$HOME/site-diagnostic"
fi

sigint_signal() {
    echo -e "\nProcess ended."; exit 1
}

trap sigint_signal SIGINT

# --- Choisir le fichier log ---
choose_log() {
    echo ""
    echo "--- Fichiers de session disponibles ---"
    echo "  Dossier : $LOG_DIR"
    echo ""

    mapfile -t LOGS < <(ls -t "$LOG_DIR"/session_*.log 2>/dev/null)

    if [ ${#LOGS[@]} -eq 0 ]; then
        echo -e "\033[31m[ECHEC]\033[0m Aucun fichier session_*.log trouve dans $LOG_DIR"
        exit 1
    fi

    for i in "${!LOGS[@]}"; do
        FNAME=$(basename "${LOGS[$i]}")
        SIZE=$(wc -c < "${LOGS[$i]}" | xargs)
        SIZE_KO=$(echo "$SIZE / 1024" | bc 2>/dev/null)
        echo "    $((i+1))) $FNAME (${SIZE_KO} Ko)"
    done

    echo ""
    read -p "Choisir un fichier (1-${#LOGS[@]}) : " CHOICE

    if ! [[ "$CHOICE" =~ ^[0-9]+$ ]] || [ "$CHOICE" -lt 1 ] || [ "$CHOICE" -gt ${#LOGS[@]} ]; then
        echo -e "\033[31m[ERREUR]\033[0m Choix invalide."
        exit 1
    fi

    LOG_FILE="${LOGS[$((CHOICE-1))]}"
    echo ""
    echo -e "\033[32m[OK]\033[0m Analyse de : $(basename $LOG_FILE)"
    echo ""
}

# --- 1. Analyse traceroute ---
analyze_traceroute() {
    echo "--- Analyse Traceroute ---"

    TRACE_LINES=$(grep -E '^\s+[0-9]+\s+' "$LOG_FILE")

    if [ -z "$TRACE_LINES" ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucune donnee traceroute trouvee dans ce log."
        echo ""
        return
    fi

    TOTAL=$(echo "$TRACE_LINES" | wc -l)
    echo "    Sauts totaux            : $TOTAL"

    TIMEOUTS=$(echo "$TRACE_LINES" | grep -c '\* \* \*')
    echo "    Sauts sans reponse      : $TIMEOUTS"

    RESPONDED=$((TOTAL - TIMEOUTS))
    echo "    Sauts avec reponse      : $RESPONDED"

    echo ""

    echo "    Prefixes d'adresses recurrents :"
    echo "$TRACE_LINES" | grep -oE '([0-9a-f:]+::[0-9a-f:]*|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})' | \
        grep -oE '^[^:\.]+[:\.][^:\.]+' | \
        sort | uniq -c | sort -rn | head -5 | while read count prefix; do
            echo "        $prefix  apparait $count fois"
        done

    echo ""

    echo "    Frontieres reseau detectees :"
    PREV=""
    BOUNDARY=0
    while IFS= read -r line; do
        if echo "$line" | grep -q '\* \* \*'; then
            if [ -n "$PREV" ]; then
                BOUNDARY=$((BOUNDARY+1))
                echo "        Frontiere $BOUNDARY detectee au saut $(echo "$line" | awk '{print $1}')"
                echo "            Avant : $PREV"
            fi
        else
            PREV=$(echo "$line" | grep -oE '([0-9a-f:]+::[0-9a-f:\.]*|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})' | head -1)
        fi
    done <<< "$TRACE_LINES"

    if [ "$BOUNDARY" -eq 0 ]; then
        echo "        Aucune frontiere detectee."
    fi

    echo ""
}

# --- 2. Analyse latence ping ---
analyze_ping() {
    echo "--- Analyse Latence Ping ---"

    PING_LINES=$(grep -E "Latence moyenne|Min / Max|Jitter" "$LOG_FILE")

    if [ -z "$PING_LINES" ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucune donnee ping trouvee dans ce log."
        echo ""
        return
    fi

    echo "$PING_LINES" | while IFS= read -r line; do
        echo "    $line"
    done

    JITTER_COUNT=$(grep -c "Jitter eleve" "$LOG_FILE")
    if [ "$JITTER_COUNT" -gt 0 ]; then
        echo -e "    \033[33m[ATTENTION]\033[0m Jitter eleve detecte $JITTER_COUNT fois dans la session."
    else
        echo -e "    \033[32m[OK]\033[0m Aucun jitter eleve detecte."
    fi

    echo ""
}

# --- 3. Analyse codes HTTP ---
analyze_http() {
    echo "--- Analyse Codes HTTP ---"

    HTTP_LINES=$(grep -E "Code HTTP|URL finale" "$LOG_FILE")

    if [ -z "$HTTP_LINES" ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucune donnee HTTP trouvee dans ce log."
        echo ""
        return
    fi

    OK=$(grep -c "Code HTTP 200" "$LOG_FILE" || true)
    REDIRECT=$(grep -cE "Code HTTP 30[0-9]|Code HTTP 308" "$LOG_FILE" || true)
    CLIENT_ERR=$(grep -c "ERREUR CLIENT" "$LOG_FILE" || true)
    SERVER_ERR=$(grep -c "ERREUR SERVEUR" "$LOG_FILE" || true)

    [ "$OK" -gt 0 ]         && echo -e "    \033[32m[OK]\033[0m         Reponses 200    : $OK"
    [ "$REDIRECT" -gt 0 ]   && echo -e "    \033[33m[REDIRECTION]\033[0m Redirections    : $REDIRECT"
    [ "$CLIENT_ERR" -gt 0 ] && echo -e "    \033[31m[ERREUR]\033[0m     Erreurs client  : $CLIENT_ERR"
    [ "$SERVER_ERR" -gt 0 ] && echo -e "    \033[31m[ERREUR]\033[0m     Erreurs serveur : $SERVER_ERR"

    URLS=$(grep "URL finale" "$LOG_FILE" | awk -F': ' '{print $2}' | sort -u)
    if [ -n "$URLS" ]; then
        echo ""
        echo "    URLs finales observees :"
        echo "$URLS" | while read -r url; do
            echo "        $url"
        done
    fi

    echo ""
}

# --- 4. Analyse SSL ---
analyze_ssl() {
    echo "--- Analyse SSL ---"

    SSL_OK=$(grep -c "Certificat SSL valide" "$LOG_FILE" || true)
    SSL_FAIL=$(grep -c "Probleme avec le certificat SSL" "$LOG_FILE" || true)

    if [ "$SSL_OK" -eq 0 ] && [ "$SSL_FAIL" -eq 0 ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucune donnee SSL trouvee dans ce log."
        echo ""
        return
    fi

    [ "$SSL_OK" -gt 0 ]   && echo -e "    \033[32m[OK]\033[0m      Certificat valide detecte $SSL_OK fois."
    [ "$SSL_FAIL" -gt 0 ] && echo -e "    \033[31m[ATTENTION]\033[0m Probleme SSL detecte $SSL_FAIL fois."

    echo ""
}

# --- 5. Analyse performance ---
analyze_performance() {
    echo "--- Analyse Performance ---"

    PERF_LINES=$(grep -E "Temps total|Taille de la page|ATTENTION.*2s|Resolution DNS|Premier octet" "$LOG_FILE")

    if [ -z "$PERF_LINES" ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucune donnee de performance trouvee dans ce log."
        echo ""
        return
    fi

    echo "$PERF_LINES" | while IFS= read -r line; do
        echo "    $line"
    done

    SLOW=$(grep -c "superieur a 2s" "$LOG_FILE" || true)
    if [ "$SLOW" -gt 0 ]; then
        echo -e "    \033[33m[ATTENTION]\033[0m Temps de reponse lent detecte $SLOW fois."
    else
        echo -e "    \033[32m[OK]\033[0m Aucun temps de reponse lent detecte."
    fi

    echo ""
}

# --- 6. Analyse securite ---
analyze_security() {
    echo "--- Analyse Securite ---"

    ABSENT=$(grep "ABSENT" "$LOG_FILE" | grep -oE '[a-z]+-[a-z-]+' | sort -u)
    PRESENT=$(grep "PRESENT" "$LOG_FILE" | grep -oE '[a-z]+-[a-z-]+' | sort -u)

    if [ -z "$ABSENT" ] && [ -z "$PRESENT" ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucune donnee de securite trouvee dans ce log."
        echo ""
        return
    fi

    if [ -n "$PRESENT" ]; then
        echo -e "    \033[32m[PRESENT]\033[0m En-tetes de securite detectes :"
        echo "$PRESENT" | while read -r h; do
            echo "        $h"
        done
    fi

    if [ -n "$ABSENT" ]; then
        echo -e "    \033[33m[ABSENT]\033[0m  En-tetes manquants :"
        echo "$ABSENT" | while read -r h; do
            echo "        $h"
        done
    fi

    echo ""
}

# --- TOUT ANALYSER ---
analyze_all() {
    analyze_traceroute
    analyze_ping
    analyze_http
    analyze_ssl
    analyze_performance
    analyze_security
}

show_menu() {
    echo
    echo -ne "\033[33m"
    echo "  Environnement : $ENV"
    echo ""
    echo "1) Traceroute (prefixes, frontieres reseau)"
    echo "2) Latence ping (moyenne, jitter)"
    echo "3) Codes HTTP (statuts, URLs)"
    echo "4) SSL (validite)"
    echo "5) Performance (temps, taille)"
    echo "6) Securite (en-tetes presents/absents)"
    echo "7) Tout analyser"
    echo "log) changer de fichier log"
    echo "menu) reafficher les options"
    echo "0) quit"
    echo -ne "\033[0m"
    echo
}

choose_log
show_menu

while true; do
    read -p $'\033[34m[log_analyzer.sh] >>\033[0m ' choix
    case $choix in
        1) analyze_traceroute ;;
        2) analyze_ping ;;
        3) analyze_http ;;
        4) analyze_ssl ;;
        5) analyze_performance ;;
        6) analyze_security ;;
        7) analyze_all ;;
        log) choose_log; show_menu ;;
        menu) show_menu ;;
        0) exit 0 ;;
        *) echo "Choix invalide" ;;
    esac
    echo
done
