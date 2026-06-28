#!/bin/bash
# ╔═══════════════════════════════════════╗
# ║     GodsEye Installer — Kali Linux    ║
# ╚═══════════════════════════════════════╝

RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
RESET='\033[0m'
BOLD='\033[1m'

echo -e "${RED}${BOLD}"
echo "  ██████╗  ██████╗ ██████╗ ███████╗███████╗██╗   ██╗███████╗"
echo " ██╔════╝ ██╔═══██╗██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝██╔════╝"
echo " ██║  ███╗██║   ██║██║  ██║███████╗█████╗   ╚████╔╝ █████╗  "
echo " ██║   ██║██║   ██║██║  ██║╚════██║██╔══╝    ╚██╔╝  ██╔══╝  "
echo " ╚██████╔╝╚██████╔╝██████╔╝███████║███████╗   ██║   ███████╗"
echo "  ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚══════╝"
echo -e "${RESET}"
echo -e "${CYAN}  GodsEye Installer v1.0${RESET}"
echo -e "${YELLOW}  For Kali Linux / Parrot OS / Ubuntu${RESET}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Tip: Run with sudo for system-wide install${RESET}"
fi

echo -e "${CYAN}[*] Updating package lists...${RESET}"
apt-get update -qq 2>/dev/null

echo -e "${CYAN}[*] Installing system dependencies...${RESET}"
apt-get install -y -qq \
    python3 \
    python3-pip \
    whois \
    dnsutils \
    nmap \
    curl \
    git \
    2>/dev/null

echo -e "${CYAN}[*] Installing Python dependencies...${RESET}"
pip3 install -q \
    requests \
    dnspython \
    python-whois \
    beautifulsoup4 \
    colorama \
    tqdm \
    2>/dev/null

echo -e "${CYAN}[*] Installing optional tools...${RESET}"
# theHarvester
if ! command -v theHarvester &> /dev/null; then
    pip3 install -q theHarvester 2>/dev/null
    echo -e "${GREEN}[+] theHarvester installed${RESET}"
fi

# Sublist3r
if [ ! -d "/opt/Sublist3r" ]; then
    git clone -q https://github.com/aboul3la/Sublist3r.git /opt/Sublist3r 2>/dev/null
    pip3 install -q -r /opt/Sublist3r/requirements.txt 2>/dev/null
    echo -e "${GREEN}[+] Sublist3r installed${RESET}"
fi

echo -e "${CYAN}[*] Setting up GodsEye...${RESET}"

# Copy to /opt
mkdir -p /opt/godseye
cp godseye.py /opt/godseye/
chmod +x /opt/godseye/godseye.py

# Create global command
cat > /usr/local/bin/godseye << 'EOF'
#!/bin/bash
python3 /opt/godseye/godseye.py "$@"
EOF
chmod +x /usr/local/bin/godseye

echo ""
echo -e "${GREEN}${BOLD}[✓] GodsEye installed successfully!${RESET}"
echo ""
echo -e "${CYAN}Usage:${RESET}"
echo -e "  ${BOLD}godseye certifiedhacker.com${RESET}"
echo -e "  ${BOLD}godseye target.com --skip-ports${RESET}"
echo -e "  ${BOLD}godseye target.com --modules whois,dns,subdomains${RESET}"
echo ""
echo -e "${YELLOW}Optional API Keys (add to environment for enhanced results):${RESET}"
echo -e "  export SHODAN_API_KEY='your_key'        # shodan.io"
echo -e "  export HUNTER_API_KEY='your_key'        # hunter.io"
echo -e "  export HIBP_API_KEY='your_key'          # haveibeenpwned.com"
echo -e "  export VIRUSTOTAL_API_KEY='your_key'    # virustotal.com"
echo ""
echo -e "${RED}⚠  For authorized penetration testing only.${RESET}"
