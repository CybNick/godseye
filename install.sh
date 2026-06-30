#!/bin/bash
# ╔═══════════════════════════════════════════════╗
# ║   GodsEye v3.0 Installer — Kali Linux         ║
# ║   Installs as global command: godseye         ║
# ╚═══════════════════════════════════════════════╝

RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'; CYAN='\033[96m'; RESET='\033[0m'; BOLD='\033[1m'

echo -e "${RED}${BOLD}"
echo "  ██████╗  ██████╗ ██████╗ ███████╗███████╗██╗   ██╗███████╗"
echo " ██╔════╝ ██╔═══██╗██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝██╔════╝"
echo " ██║  ███╗██║   ██║██║  ██║███████╗█████╗   ╚████╔╝ █████╗  "
echo " ██║   ██║██║   ██║██║  ██║╚════██║██╔══╝    ╚██╔╝  ██╔══╝  "
echo " ╚██████╔╝╚██████╔╝██████╔╝███████║███████╗   ██║   ███████╗"
echo "  ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚══════╝"
echo -e "${RESET}"
echo -e "${CYAN}  GodsEye v3.0 Installer${RESET}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Please run with sudo: sudo bash install.sh${RESET}"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${CYAN}[*] Installing system dependencies...${RESET}"
apt-get update -qq 2>/dev/null
apt-get install -y -qq python3 python3-pip whois dnsutils nmap curl git 2>/dev/null

echo -e "${CYAN}[*] Installing Python dependencies...${RESET}"
pip3 install -q --break-system-packages requests 2>/dev/null

echo -e "${CYAN}[*] Installing optional tools...${RESET}"
if ! command -v theHarvester &> /dev/null; then
    pip3 install -q --break-system-packages theHarvester 2>/dev/null
fi

echo -e "${CYAN}[*] Setting up GodsEye v3.0...${RESET}"

mkdir -p /opt/godseye
cp "$SCRIPT_DIR/godseye_v3.py" /opt/godseye/godseye_v3.py
chmod +x /opt/godseye/godseye_v3.py

# Create the global "godseye" command
cat > /usr/local/bin/godseye << 'WRAPPER'
#!/bin/bash
python3 /opt/godseye/godseye_v3.py "$@"
WRAPPER
chmod +x /usr/local/bin/godseye

echo ""
echo -e "${GREEN}${BOLD}[✓] GodsEye v3.0 installed!${RESET}"
echo ""
echo -e "${CYAN}Run it from anywhere now:${RESET}"
echo -e "  ${BOLD}godseye certifiedhacker.com${RESET}"
echo ""
echo -e "${CYAN}Other commands:${RESET}"
echo -e "  ${BOLD}godseye --configure${RESET}     Set up API keys (Shodan, Hunter.io, HIBP)"
echo -e "  ${BOLD}godseye --update${RESET}        Pull latest version from GitHub"
echo -e "  ${BOLD}godseye target.com --output ~/reports/${RESET}"
echo -e "  ${BOLD}godseye target.com --modules whois,dns,ports${RESET}"
echo ""
echo -e "${RED}⚠  For authorized penetration testing only.${RESET}"
