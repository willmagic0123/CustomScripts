#!/bin/bash

# Outil de diagnostic web complet - menu interactif

sigint_signal() {
    echo -e "\nProcess ended."; exit 1
}

trap sigint_signal SIGINT

cd /data/data/com.termux/files/home/tool_projects/site-diagnostic/
echo
echo -e "Now in: [\033[34m$(pwd)\033[0m]"


SESSION_ID="$(pwgen --no-numerals --no-vowels 6 1)"
LOG_FILE="/data/data/com.termux/files/home/tool_projects/site-diagnostic/session_$(date +"%Y-%m-%d_%H-%M-%S")_$SESSION_ID.log"
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1
SITE=""

ask_site() {
    if [ -z "$SITE" ]; then
        read -p "Site a tester (ex: cleanviewqc.com) : " SITE
        SITE=$(echo "$SITE" | sed 's|https://||' | sed 's|http://||')
        SITE=$(echo "$SITE" | sed 's|/$||')
    fi
}

# --- 1. DNS ---
check_dns() {
    ask_site
    echo ""
    echo "--- Resolution DNS ---"
    if command -v dig &> /dev/null; then
        DIG_RESULT=$(dig +short "$SITE" 2>&1)
        if [ -n "$DIG_RESULT" ]; then
            echo -e "\033[32m[OK]\033[0m Le domaine resout vers :"
            echo "$DIG_RESULT" | while read -r ip; do
                echo "    $ip"
            done
        else
            echo -e "\033[31m[ECHEC]\033[0m Aucune resolution DNS trouvee."
        fi
    else
        echo -e "\033[33m[INFO]\033[0m 'dig' non installe (pkg install dnsutils)."
    fi
    echo ""
}

# --- 2. PING ---
check_ping() {
    ask_site
    echo ""
    echo "--- Test PING (latence reseau) ---"
    PING_RESULT=$(ping -c 5 "$SITE" 2>&1)

    if echo "$PING_RESULT" | grep -q "100% packet loss"; then
        echo -e "\033[31m[ECHEC]\033[0m Le site ne repond pas au ping."
    elif echo "$PING_RESULT" | grep -q "bytes from"; then
        STATS_LINE=$(echo "$PING_RESULT" | grep -E "min/avg/max")
        NUMS=($(echo "$STATS_LINE" | grep -oE '[0-9]+\.[0-9]+|[0-9]+'))
        MIN=${NUMS[0]}
        AVG=${NUMS[1]}
        MAX=${NUMS[2]}

        echo -e "\033[32m[OK]\033[0m Le site repond au ping."

        if [ -n "$AVG" ]; then
            echo "    Latence moyenne : ${AVG} ms"
            echo "    Min / Max       : ${MIN} ms / ${MAX} ms"

            DIFF=$(echo "$MAX - $MIN" | bc -l 2>/dev/null)
            IS_HIGH=$(echo "$DIFF > 200" | bc -l 2>/dev/null)
            if [ "$IS_HIGH" = "1" ]; then
                echo -e "    \033[33m[ATTENTION]\033[0m Jitter eleve (connexion instable)."
            fi
        else
            echo "    (Statistiques detaillees non disponibles sur ce systeme)"
        fi
    else
        echo -e "\033[33m[INCONNU]\033[0m Impossible d'interpreter le resultat du ping."
    fi
    echo ""
}

# --- 3. HTTP STATUS ---
check_http() {
    ask_site
    echo ""
    echo "--- Test HTTP/HTTPS (etat reel du site) ---"
    CURL_RESULT=$(curl -sL -o /dev/null -w "%{http_code} %{time_total} %{ssl_verify_result} %{url_effective}" --max-time 10 "https://$SITE")
    HTTP_CODE=$(echo "$CURL_RESULT" | awk '{print $1}')
    TIME_TOTAL=$(echo "$CURL_RESULT" | awk '{print $2}')
    SSL_OK=$(echo "$CURL_RESULT" | awk '{print $3}')
    URL_FINAL=$(echo "$CURL_RESULT" | awk '{print $4}')

    if [ -z "$HTTP_CODE" ] || [ "$HTTP_CODE" = "000" ]; then
        echo -e "\033[31m[ECHEC]\033[0m Aucune reponse HTTP recue."
    else
        case $HTTP_CODE in
            200) echo -e "\033[32m[OK]\033[0m Code HTTP 200 - le site repond normalement." ;;
            301|302|307|308) echo -e "\033[33m[REDIRECTION]\033[0m Code HTTP $HTTP_CODE - le site redirige." ;;
            4*) echo -e "\033[31m[ERREUR CLIENT]\033[0m Code HTTP $HTTP_CODE." ;;
            5*) echo -e "\033[31m[ERREUR SERVEUR]\033[0m Code HTTP $HTTP_CODE." ;;
            *) echo -e "\033[33m[INATTENDU]\033[0m Code HTTP $HTTP_CODE." ;;
        esac

        echo "    Temps de reponse total : ${TIME_TOTAL}s"
        echo "    URL finale             : ${URL_FINAL}"

        if [ "$SSL_OK" = "0" ]; then
            echo -e "    \033[32m[OK]\033[0m Certificat SSL valide."
        else
            echo -e "    \033[31m[ATTENTION]\033[0m Probleme avec le certificat SSL."
        fi
    fi
    echo ""
}

# --- 4. HEADERS GENERAUX ---
check_headers() {
    ask_site
    echo ""
    echo "--- En-tetes principaux ---"
    HEADERS=$(curl -sIL --max-time 10 "https://$SITE")
    SERVER=$(echo "$HEADERS" | grep -i "^server:" | tail -1 | cut -d' ' -f2-)
    VERCEL_ID=$(echo "$HEADERS" | grep -i "^x-vercel-id:" | tail -1 | cut -d' ' -f2-)

    if [ -n "$SERVER" ]; then
        echo "    Serveur       : $SERVER"
    fi
    if [ -n "$VERCEL_ID" ]; then
        echo "    Region Vercel : $VERCEL_ID"
    fi
    if [ -z "$SERVER" ] && [ -z "$VERCEL_ID" ]; then
        echo -e "    \033[33m[INFO]\033[0m Aucun en-tete reconnu trouve."
    fi
    echo ""
}

# --- 5. TRACEROUTE ---
check_traceroute() {
    ask_site
    echo ""
    echo "--- Traceroute (chemin reseau) ---"
    if command -v traceroute &> /dev/null; then
        TRACE_RESULT=$(traceroute -m 15 -w 2 "$SITE" 2>&1)
        TOTAL_HOPS=$(echo "$TRACE_RESULT" | grep -cE '^\s*[0-9]+')
        TIMEOUT_HOPS=$(echo "$TRACE_RESULT" | grep -o '\* \* \*' | wc -l)

        if [ "$TOTAL_HOPS" -gt 0 ]; then
            echo -e "\033[32m[OK]\033[0m Trajet trace en $TOTAL_HOPS sauts."
            if [ "$TIMEOUT_HOPS" -gt 0 ]; then
                echo -e "    \033[33m[INFO]\033[0m $TIMEOUT_HOPS saut(s) sans reponse (pare-feu intermediaire, souvent normal)."
            fi
            echo "    Derniers sauts :"
            echo "$TRACE_RESULT" | grep -E '^\s*[0-9]+' | tail -50 | sed 's/^/    /'
        else
            echo -e "\033[33m[INCONNU]\033[0m Impossible de tracer le chemin."
        fi
    else
        echo -e "\033[33m[INFO]\033[0m 'traceroute' non installe (pkg install traceroute)."
    fi
    echo ""
}

# --- 6. WHOIS ---
check_whois() {
    ask_site
    echo ""
    echo "--- Informations du domaine (WHOIS) ---"
    if command -v whois &> /dev/null; then
        WHOIS_RESULT=$(whois "$SITE" 2>&1)
        REGISTRAR=$(echo "$WHOIS_RESULT" | grep -i "^Registrar:" | head -1 | cut -d: -f2- | xargs)
        EXPIRY=$(echo "$WHOIS_RESULT" | grep -iE "^Registry Expiry Date:|^Expiry Date:|^Expiration Date:" | head -1 | cut -d: -f2- | xargs)
        CREATED=$(echo "$WHOIS_RESULT" | grep -iE "^Creation Date:|^Created:" | head -1 | cut -d: -f2- | xargs)

        if [ -n "$REGISTRAR" ] || [ -n "$EXPIRY" ]; then
            echo -e "\033[32m[OK]\033[0m Informations trouvees."
            [ -n "$REGISTRAR" ] && echo "    Registrar  : $REGISTRAR"
            [ -n "$CREATED" ]   && echo "    Cree le    : $CREATED"
            [ -n "$EXPIRY" ]    && echo "    Expire le  : $EXPIRY"
        else
            echo -e "\033[33m[INCONNU]\033[0m Aucune information whois standard trouvee."
        fi
    else
        echo -e "\033[33m[INFO]\033[0m 'whois' non installe (pkg install whois)."
    fi
    echo ""
}

# --- 7. SECURITE ---
check_security() {
    ask_site
    echo ""
    echo "--- En-tetes de securite ---"
    HEADERS=$(curl -sIL --max-time 10 "https://$SITE")

    declare -A SEC_HEADERS=(
        ["strict-transport-security"]="Force HTTPS (HSTS)"
        ["x-content-type-options"]="Empeche le MIME-sniffing"
        ["x-frame-options"]="Protection contre le clickjacking"
        ["content-security-policy"]="Politique de securite du contenu (CSP)"
        ["referrer-policy"]="Controle des infos de referent envoyees"
    )

    for h in "${!SEC_HEADERS[@]}"; do
        VAL=$(echo "$HEADERS" | grep -i "^${h}:" | tail -1 | cut -d: -f2- | xargs)
        if [ -n "$VAL" ]; then
            echo -e "    \033[32m[PRESENT]\033[0m $h - ${SEC_HEADERS[$h]}"
        else
            echo -e "    \033[33m[ABSENT]\033[0m  $h - ${SEC_HEADERS[$h]}"
        fi
    done
    echo ""
}

# --- 8. PERFORMANCE ---
check_performance() {
    ask_site
    echo ""
    echo "--- Performance detaillee ---"

    TIMING=$(curl -sL -o /dev/null -w "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total} %{url_effective}" --max-time 15 "https://$SITE")
    SIZE=$(curl -sL --max-time 15 "https://$SITE" | wc -c)

    DNS_T=$(echo "$TIMING" | awk '{print $1}')
    CONNECT_T=$(echo "$TIMING" | awk '{print $2}')
    TLS_T=$(echo "$TIMING" | awk '{print $3}')
    FIRSTBYTE_T=$(echo "$TIMING" | awk '{print $4}')
    TOTAL_T=$(echo "$TIMING" | awk '{print $5}')
    URL_FINAL=$(echo "$TIMING" | awk '{print $6}')

    if [ -z "$TOTAL_T" ] || [ "$TOTAL_T" = "0.000000" ]; then
        echo -e "\033[31m[ECHEC]\033[0m Impossible de mesurer la performance."
    else
        echo "    URL finale          : ${URL_FINAL}"
        echo "    Resolution DNS      : ${DNS_T}s"
        echo "    Connexion TCP       : ${CONNECT_T}s"
        echo "    Handshake TLS       : ${TLS_T}s"
        echo "    Premier octet recu  : ${FIRSTBYTE_T}s"
        echo "    Temps total         : ${TOTAL_T}s"

        if [ -n "$SIZE" ] && [ "$SIZE" -gt 0 ]; then
            SIZE_KO=$(echo "$SIZE / 1024" | bc 2>/dev/null)
            echo "    Taille de la page   : ${SIZE_KO} Ko"
        fi

        IS_SLOW=$(echo "$TOTAL_T > 2" | bc -l 2>/dev/null)
        if [ "$IS_SLOW" = "1" ]; then
            echo -e "    \033[33m[ATTENTION]\033[0m Temps de reponse total superieur a 2s."
        else
            echo -e "    \033[32m[OK]\033[0m Temps de reponse correct."
        fi
    fi
    echo ""
}

# --- 10. SAUVEGARDER HTML ---
save_html() {
    ask_site
    echo ""
    echo "--- Sauvegarde du contenu HTML ---"

    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
    CLEAN_SITE=$(echo "$SITE" | sed 's|www\.||' | sed 's|\.|-|g')
    SAVE_DIR="/data/data/com.termux/files/home/tool_projects/site-diagnostic"
    HTML_FILE="${SAVE_DIR}/${CLEAN_SITE}_${TIMESTAMP}_$SESSION_ID.html"

    mkdir -p "$SAVE_DIR"
    curl -sL --max-time 15 "https://$SITE" -o "$HTML_FILE"

    if [ $? -eq 0 ] && [ -s "$HTML_FILE" ]; then
        SIZE_KO=$(wc -c < "$HTML_FILE" | xargs)
        SIZE_KO=$(echo "$SIZE_KO / 1024" | bc 2>/dev/null)
        echo -e "\033[32m[OK]\033[0m HTML sauvegarde :"
        echo "    Chemin  : $HTML_FILE"
        echo "    Taille  : ${SIZE_KO} Ko"
    else
        echo -e "\033[31m[ECHEC]\033[0m Impossible de sauvegarder le HTML."
    fi
    echo ""
}

# --- 11. PAGINATION ---
check_pagination() {
    ask_site
    echo ""
    echo "--- Analyse de la pagination ---"

    # Télécharger le HTML de la page
    HTML=$(curl -sL --max-time 15 "https://$SITE")

    if [ -z "$HTML" ]; then
        echo -e "\033[31m[ECHEC]\033[0m Impossible de recuperer le contenu de la page."
        echo ""
        return
    fi

    # 1. Meta tags rel=next / rel=prev
    echo "  -- Meta tags (rel=next / rel=prev) --"
    REL_NEXT=$(echo "$HTML" | grep -oE '<link[^>]*rel="next"[^>]*>' | head -3)
    REL_PREV=$(echo "$HTML" | grep -oE '<link[^>]*rel="prev"[^>]*>' | head -3)

    if [ -n "$REL_NEXT" ]; then
        NEXT_URL=$(echo "$REL_NEXT" | grep -oE 'href="[^"]+"' | cut -d'"' -f2)
        echo -e "    \033[32m[PRESENT]\033[0m rel=next -> $NEXT_URL"
    else
        echo -e "    \033[33m[ABSENT]\033[0m  rel=next non trouve."
    fi

    if [ -n "$REL_PREV" ]; then
        PREV_URL=$(echo "$REL_PREV" | grep -oE 'href="[^"]+"' | cut -d'"' -f2)
        echo -e "    \033[32m[PRESENT]\033[0m rel=prev -> $PREV_URL"
    else
        echo -e "    \033[33m[ABSENT]\033[0m  rel=prev non trouve."
    fi

    echo ""

    # 2. Liens de pagination dans le HTML
    echo "  -- Liens de pagination detectes dans le HTML --"
    PAGINATION_LINKS=$(echo "$HTML" | grep -oE 'href="[^"]*[?/]page[=/][0-9]+"' | sort -u)

    if [ -n "$PAGINATION_LINKS" ]; then
        COUNT=$(echo "$PAGINATION_LINKS" | wc -l)
        echo -e "    \033[32m[OK]\033[0m $COUNT lien(s) de pagination trouves :"
        echo "$PAGINATION_LINKS" | while read -r link; do
            URL=$(echo "$link" | cut -d'"' -f2)
            echo "        $URL"
        done

        # Trouver le numero de page max
        MAX_PAGE=$(echo "$PAGINATION_LINKS" | grep -oE '[0-9]+' | sort -n | tail -1)
        [ -n "$MAX_PAGE" ] && echo -e "    \033[32m[INFO]\033[0m Page maximum detectee : $MAX_PAGE"
    else
        echo -e "    \033[33m[INFO]\033[0m Aucun lien de pagination standard trouve."
    fi

    echo ""

    # 3. Sitemap.xml
    echo "  -- Sitemap.xml --"
    SITEMAP=$(curl -sL --max-time 10 "https://$SITE/sitemap.xml" 2>&1)

    if echo "$SITEMAP" | grep -q "<urlset\|<sitemapindex"; then
        TOTAL_URLS=$(echo "$SITEMAP" | grep -c "<loc>" || true)
        PAGINATED_URLS=$(echo "$SITEMAP" | grep -c "page=" || true)

        echo -e "    \033[32m[OK]\033[0m sitemap.xml trouve."
        echo "        Total URLs indexees  : $TOTAL_URLS"
        [ "$PAGINATED_URLS" -gt 0 ] && echo "        URLs paginées        : $PAGINATED_URLS"

        echo "        Liste des URLs :"
        echo "$SITEMAP" | grep -oE '<loc>[^<]+</loc>' | \
            sed 's/<loc>//;s/<\/loc>//' | head -10 | while read -r url; do
            echo "            $url"
        done

        [ "$TOTAL_URLS" -gt 10 ] && echo "        ... ($TOTAL_URLS URLs au total)"
    else
        echo -e "    \033[33m[INFO]\033[0m Aucun sitemap.xml trouve sur https://$SITE/sitemap.xml"
    fi

    echo ""
}

# --- 9. TOUT LANCER ---
run_all() {
    check_dns
    check_ping
    check_http
    check_headers
    check_security
    check_performance
    check_traceroute
    check_whois
}

show_menu() {
    echo
    echo -ne "\033[33m"
    echo "1)  DNS (resolution)"
    echo "2)  Ping (latence)"
    echo "3)  HTTP/HTTPS (statut, SSL, URL finale)"
    echo "4)  En-tetes generaux (serveur)"
    echo "5)  Traceroute (chemin reseau)"
    echo "6)  Whois (infos domaine)"
    echo "7)  Securite (en-tetes de securite)"
    echo "8)  Performance (timing detaille, URL finale)"
    echo "9)  Tout lancer"
    echo "10) Sauvegarder le HTML de la page"
    echo "11) Pagination (liens, meta tags, sitemap)"
    echo "site) changer de site (actuel: ${SITE:-aucun})"
    echo "menu) reafficher les options"
    echo "0)  quit"
    echo -ne "\033[0m"
    echo
}

show_menu

while true; do
    read -p $'\033[34m[site_check.sh] >>\033[0m ' choix
    case $choix in
        1) check_dns ;;
        2) check_ping ;;
        3) check_http ;;
        4) check_headers ;;
        5) check_traceroute ;;
        6) check_whois ;;
        7) check_security ;;
        8) check_performance ;;
        9) run_all ;;
        10) save_html ;;
	11) check_pagination ;;
        site) SITE=""; ask_site ;;
        menu) show_menu ;;
        0) exit 0 ;;
        *) echo "Choix invalide" ;;
    esac
    echo
done
