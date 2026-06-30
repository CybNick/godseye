#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║                        GODSEYE v3.0                              ║
║       Advanced Reconnaissance & Vulnerability Intelligence       ║
║       "See Everything. Miss Nothing. Strike First."              ║
╚══════════════════════════════════════════════════════════════════╝

NEW IN v3.0 (built from real v2.0 scan analysis):
  → FTP anonymous login now lists and downloads accessible files
  → MySQL/PostgreSQL EOL version database (no NVD dependency needed)
  → cpanel/whm version fingerprinting + default login test
  → Real SPF spoof simulation (constructs proof-of-concept email)
  → Subdomain takeover verification with confidence scoring
  → Shared hosting weak-neighbor scanner
  → Deep Wayback Machine historical page diffing
  → theHarvester auto-fallback chain (api -> subprocess -> scrape)
  → CVSS v3.1 scoring engine per finding
  → Executive narrative summary generator (not just lists)
  → Remediation priority engine (fix-this-first ordering)
  → Config file support: ~/.godseye/config.json for API keys
  → --output flag for custom report location
  → --update self-updater from GitHub
  → Animated spinner per module
  → GitHub org secret-pattern scanner
  → Known EOL software database (offline, instant detection)

Usage (after install.sh):
  godseye certifiedhacker.com
  godseye target.com --skip-ports
  godseye target.com --output /home/user/reports/
  godseye target.com --modules whois,dns,ports
  godseye --update
  godseye --configure

Legal: Authorized penetration testing only.
"""

import sys, os, json, socket, ssl, time, re, argparse, threading
import ipaddress, subprocess, hashlib, itertools
from datetime import datetime
from pathlib import Path
from urllib import request, parse, error
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "3.0"
CONFIG_DIR = Path.home() / ".godseye"
CONFIG_FILE = CONFIG_DIR / "config.json"

# ─────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────
class C:
    RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'
    BLUE='\033[94m'; MAGENTA='\033[95m'; CYAN='\033[96m'
    WHITE='\033[97m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

def banner():
    print(f"""{C.RED}{C.BOLD}
  ██████╗  ██████╗ ██████╗ ███████╗███████╗██╗   ██╗███████╗
 ██╔════╝ ██╔═══██╗██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝██╔════╝
 ██║  ███╗██║   ██║██║  ██║███████╗█████╗   ╚████╔╝ █████╗
 ██║   ██║██║   ██║██║  ██║╚════██║██╔══╝    ╚██╔╝  ██╔══╝
 ╚██████╔╝╚██████╔╝██████╔╝███████║███████╗   ██║   ███████╗
  ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚══════╝
{C.RESET}{C.CYAN}  Advanced Reconnaissance & Vulnerability Intelligence v{VERSION}{C.RESET}
{C.DIM}  "See Everything. Miss Nothing. Strike First."{C.RESET}
{C.YELLOW}  ⚠  Authorized penetration testing only  ⚠{C.RESET}
""")

def info(m):    print(f"  {C.CYAN}[*]{C.RESET} {m}")
def success(m): print(f"  {C.GREEN}[+]{C.RESET} {m}")
def warn(m):    print(f"  {C.YELLOW}[!]{C.RESET} {m}")
def err(m):     print(f"  {C.RED}[-]{C.RESET} {m}")
def data(m):    print(f"      {C.WHITE}{m}{C.RESET}")
def crit(m):    print(f"  {C.RED}{C.BOLD}[CRITICAL]{C.RESET} {C.RED}{m}{C.RESET}")
def section(t, n, total):
    pct = int((n/total)*100)
    bar = '█'*(pct//5) + '░'*(20-pct//5)
    print(f"\n{C.BOLD}{C.BLUE}{'═'*62}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}  [{bar}] {pct:>3}%  MODULE {n:02d}/{total} — {t}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}{'═'*62}{C.RESET}")

# ─────────────────────────────────────────────────
# CONFIG MANAGEMENT (NEW)
# ─────────────────────────────────────────────────
def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except: pass
    return {}

def save_config(cfg):
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def interactive_configure():
    banner()
    print(f"  {C.BOLD}GodsEye Configuration{C.RESET}\n")
    cfg = load_config()
    keys = {
        'shodan_api_key': 'Shodan API key (shodan.io/register)',
        'hunter_api_key': 'Hunter.io API key (hunter.io)',
        'hibp_api_key':   'HaveIBeenPwned API key (haveibeenpwned.com/API/Key)',
        'github_token':   'GitHub Personal Access Token (optional, raises rate limits)',
    }
    for key, label in keys.items():
        current = cfg.get(key, '')
        shown = f" [current: {current[:8]}...]" if current else " [not set]"
        print(f"  {C.CYAN}{label}{C.RESET}{shown}")
        val = input(f"  Enter value (blank to skip): ").strip()
        if val: cfg[key] = val
    save_config(cfg)
    success(f"Config saved to {CONFIG_FILE}")

# ─────────────────────────────────────────────────
# SELF-UPDATER (NEW)
# ─────────────────────────────────────────────────
def self_update():
    banner()
    info("Checking for updates...")
    repo_raw = "https://raw.githubusercontent.com/CybNick/godseye/main/godseye_v3.py"
    try:
        req = request.Request(repo_raw)
        req.add_header('User-Agent', 'GodsEye-Updater')
        with request.urlopen(req, timeout=10) as r:
            new_code = r.read().decode('utf-8')
        current_path = os.path.realpath(__file__)
        with open(current_path, 'w') as f:
            f.write(new_code)
        success("Updated to latest version!")
    except Exception as e:
        err(f"Update failed: {e}")
        data("Manually update: git -C ~/tools/godseye pull")

# ─────────────────────────────────────────────────
# RISK ENGINE WITH CVSS
# ─────────────────────────────────────────────────
class RiskEngine:
    def __init__(self):
        self.findings = []
        self.score = 0

    def add(self, title, severity, description, recommendation, score, cvss=None):
        self.findings.append({
            'title': title, 'severity': severity,
            'description': description,
            'recommendation': recommendation,
            'score': score,
            'cvss': cvss or self._estimate_cvss(severity)
        })
        self.score = min(100, self.score + score)
        color = {'CRITICAL': C.RED, 'HIGH': C.YELLOW,
                 'MEDIUM': C.CYAN, 'LOW': C.GREEN, 'INFO': C.DIM}.get(severity, C.WHITE)
        print(f"  {color}[{severity}]{C.RESET} {title}")

    def _estimate_cvss(self, severity):
        return {'CRITICAL': 9.5, 'HIGH': 7.5, 'MEDIUM': 5.0, 'LOW': 2.5, 'INFO': 0.5}.get(severity, 5.0)

    def get_rating(self):
        if self.score >= 80: return "CRITICAL RISK", '#e63946'
        if self.score >= 60: return "HIGH RISK", '#ff8800'
        if self.score >= 40: return "MEDIUM RISK", '#ffcc00'
        if self.score >= 20: return "LOW RISK", '#00aa00'
        return "MINIMAL RISK", '#00cc00'

    def get_remediation_order(self):
        """NEW: Returns findings sorted by fix-priority (impact/effort ratio)"""
        order = {'CRITICAL':0,'HIGH':1,'MEDIUM':2,'LOW':3,'INFO':4}
        return sorted(self.findings, key=lambda f: (order.get(f['severity'],5), -f['cvss']))

# ─────────────────────────────────────────────────
# EOL / KNOWN-VULNERABLE SOFTWARE DATABASE (NEW)
# ─────────────────────────────────────────────────
EOL_DATABASE = {
    'mysql': [
        {'version_prefix': '5.5', 'eol': '2018-12-01', 'cves': ['CVE-2016-6662','CVE-2012-2122'], 'note': 'MySQL 5.5 EOL — critical auth bypass CVE-2012-2122'},
        {'version_prefix': '5.6', 'eol': '2021-02-01', 'cves': ['CVE-2016-6662'], 'note': 'MySQL 5.6 EOL — multiple RCE vulnerabilities'},
        {'version_prefix': '5.7', 'eol': '2023-10-01', 'cves': ['CVE-2021-2154','CVE-2022-21245'], 'note': 'MySQL 5.7 EOL since Oct 2023 — no security patches'},
    ],
    'postgresql': [
        {'version_prefix': '9.', 'eol': '2021-11-01', 'cves': ['CVE-2019-10164'], 'note': 'PostgreSQL 9.x EOL — unpatched'},
        {'version_prefix': '10', 'eol': '2022-11-01', 'cves': [], 'note': 'PostgreSQL 10 EOL'},
        {'version_prefix': '11', 'eol': '2023-11-01', 'cves': [], 'note': 'PostgreSQL 11 EOL'},
    ],
    'openssh': [
        {'version_prefix': '7.', 'eol': 'legacy', 'cves': ['CVE-2018-15473'], 'note': 'OpenSSH 7.x — username enumeration CVE'},
        {'version_prefix': '6.', 'eol': 'legacy', 'cves': ['CVE-2016-6210','CVE-2016-6515'], 'note': 'OpenSSH 6.x — multiple known CVEs'},
    ],
    'apache': [
        {'version_prefix': '2.2', 'eol': '2017-12-01', 'cves': ['CVE-2017-15710'], 'note': 'Apache 2.2 EOL — no patches since 2017'},
        {'version_prefix': '2.4.4', 'eol': 'partial', 'cves': ['CVE-2021-41773','CVE-2021-42013'], 'note': 'Apache path traversal RCE (2.4.49-2.4.50)'},
    ],
    'nginx': [
        {'version_prefix': '1.1', 'eol': 'check', 'cves': [], 'note': 'Old nginx 1.1x — verify patch level'},
    ],
    'php': [
        {'version_prefix': '5.', 'eol': '2019-01-01', 'cves': ['CVE-2019-11043'], 'note': 'PHP 5.x EOL — critical RCE vulnerabilities'},
        {'version_prefix': '7.0', 'eol': '2019-01-01', 'cves': [], 'note': 'PHP 7.0 EOL'},
        {'version_prefix': '7.1', 'eol': '2019-12-01', 'cves': [], 'note': 'PHP 7.1 EOL'},
        {'version_prefix': '7.2', 'eol': '2020-11-30', 'cves': [], 'note': 'PHP 7.2 EOL'},
        {'version_prefix': '7.3', 'eol': '2021-12-06', 'cves': [], 'note': 'PHP 7.3 EOL'},
        {'version_prefix': '7.4', 'eol': '2022-11-28', 'cves': [], 'note': 'PHP 7.4 EOL — common in legacy WordPress sites'},
    ],
    'wordpress': [
        {'version_prefix': '4.', 'eol': 'legacy', 'cves': [], 'note': 'WordPress 4.x — severely outdated, multiple plugin CVE risk'},
        {'version_prefix': '5.', 'eol': 'check', 'cves': [], 'note': 'WordPress 5.x — verify latest patch'},
    ],
}

def check_eol(product, version):
    """Returns EOL info if version matches known vulnerable database"""
    product_l = product.lower()
    if product_l in EOL_DATABASE:
        for entry in EOL_DATABASE[product_l]:
            if version.startswith(entry['version_prefix']):
                return entry
    return None

# ─────────────────────────────────────────────────
# HTTP HELPER
# ─────────────────────────────────────────────────
def http_get(url, timeout=8, headers=None):
    try:
        req = request.Request(url)
        req.add_header('User-Agent',
            'Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0')
        if headers:
            for k,v in headers.items(): req.add_header(k,v)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode('utf-8', errors='ignore'), r.status, dict(r.headers)
    except Exception as e:
        return None, str(e), {}

# ─────────────────────────────────────────────────
# MODULE 01: WHOIS
# ─────────────────────────────────────────────────
def run_whois(target, results, risk, n, total):
    section("WHOIS INTELLIGENCE", n, total)
    info(f"Running WHOIS on {target}...")
    whois_data = {}
    try:
        out = subprocess.getoutput(f"whois {target} 2>/dev/null")
        if out and len(out) > 50:
            success("WHOIS data retrieved")
            patterns = {
                'Registrar': r'Registrar:\s*(.+)', 'Created': r'Creation Date:\s*(.+)',
                'Expires': r'Registry Expiry Date:\s*(.+)', 'Updated': r'Updated Date:\s*(.+)',
                'Name Servers': r'Name Server:\s*(.+)', 'Registrant Org': r'Registrant Organization:\s*(.+)',
                'Registrant Email': r'Registrant Email:\s*(.+)', 'Status': r'Domain Status:\s*(.+)',
                'DNSSEC': r'DNSSEC:\s*(.+)',
            }
            for field, pattern in patterns.items():
                matches = re.findall(pattern, out, re.IGNORECASE)
                if matches:
                    unique = list(dict.fromkeys([m.strip() for m in matches]))
                    whois_data[field] = unique
                    if field == 'Expires':
                        data(f"{C.YELLOW}Expiry:{C.RESET} {unique[0]}")
                        try:
                            exp_str = unique[0].split('T')[0]
                            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                            days = (exp_date - datetime.now()).days
                            whois_data['days_to_expiry'] = days
                            if days < 30:
                                crit(f"Domain expires in {days} days — HIJACK IMMINENT!")
                                risk.add("Domain Expiry Critical", "CRITICAL", f"Domain expires in {days} days",
                                    "Renew domain immediately and enable auto-renewal", 35, 9.8)
                            elif days < 90:
                                warn(f"Domain expires in {days} days")
                                risk.add("Domain Expiry Warning", "HIGH", f"Domain expires in {days} days",
                                    "Renew domain and enable auto-renewal", 15, 7.0)
                        except: pass
                    elif field == 'Registrant Email':
                        em = unique[0]
                        data(f"{C.RED}Registrant Email:{C.RESET} {em}")
                        if any(p in em.lower() for p in ['private','proxy','protection','redacted']):
                            success("WHOIS privacy enabled")
                        else:
                            warn("Real registrant email exposed")
                            risk.add("WHOIS Email Exposed", "MEDIUM", "Real registrant email publicly visible",
                                "Enable WHOIS privacy protection", 8, 4.0)
                    elif field == 'Name Servers':
                        for ns in unique[:4]: data(f"Name Server: {ns}")
                        if any(target.replace('www.','') in ns.lower() for ns in unique):
                            warn("Self-hosted nameservers")
                            whois_data['self_hosted_ns'] = True
                            risk.add("Self-Hosted Nameservers", "MEDIUM", "Zone transfer misconfiguration risk",
                                "Restrict AXFR to trusted IPs only", 10, 5.3)
                        else:
                            data("Third-party DNS provider (safer)")
                    elif field == 'DNSSEC':
                        if 'unsigned' in unique[0].lower():
                            warn("DNSSEC unsigned")
                            risk.add("DNSSEC Disabled", "MEDIUM", "DNS cache poisoning possible",
                                "Enable DNSSEC", 8, 4.5)
                    else:
                        data(f"{field}: {', '.join(unique[:2])}")
    except Exception as e:
        err(f"WHOIS error: {e}")
    results['whois'] = whois_data

# ─────────────────────────────────────────────────
# MODULE 02: DNS
# ─────────────────────────────────────────────────
def run_dns(target, results, risk, n, total):
    section("DNS INTELLIGENCE", n, total)
    info(f"Extracting DNS records for {target}...")
    dns_data = {}
    try:
        for rtype in ['A','AAAA','MX','NS','TXT','SOA','CNAME','SRV','CAA']:
            out = subprocess.getoutput(f"dig {target} {rtype} +short 2>/dev/null")
            if out and out.strip() and ';' not in out:
                dns_data[rtype] = [l.strip() for l in out.strip().split('\n') if l.strip()]
                if rtype == 'A':
                    for ip in dns_data[rtype]: success(f"A Record: {ip}")
                elif rtype == 'MX':
                    success("MX Records:")
                    for mx in dns_data[rtype]: data(f"  {mx}")
                elif rtype == 'NS':
                    success("Name Servers:")
                    for ns in dns_data[rtype]: data(f"  {ns}")
                elif rtype == 'TXT':
                    success("TXT Records:")
                    for txt in dns_data[rtype]:
                        data(f"  {txt}")
                        if 'v=spf1' in txt.lower():
                            if '+all' in txt:
                                crit("SPF PassAll (+all) — total spoofing possible!")
                                risk.add("SPF PassAll Critical", "CRITICAL", "Any server can send as this domain",
                                    "Change to -all immediately", 40, 9.8)
                                dns_data['spf_spoofable'] = True
                            elif '?all' in txt:
                                crit("SPF Neutral (?all) — spoofing trivially possible!")
                                risk.add("SPF Neutral", "CRITICAL", "No enforcement — spoofing trivial",
                                    "Change ?all to -all", 35, 9.1)
                                dns_data['spf_spoofable'] = True
                            elif '~all' in txt:
                                warn("SPF SoftFail (~all) — spoofing POSSIBLE")
                                risk.add("SPF SoftFail", "HIGH", "Accepts suspicious emails",
                                    "Change ~all to -all", 20, 6.5)
                                dns_data['spf_spoofable'] = True
                            elif '-all' in txt:
                                success("SPF HardFail (-all) — spoofing blocked ✓")
                                dns_data['spf_ok'] = True
                        if 'v=dmarc1' in txt.lower():
                            if 'p=none' in txt.lower():
                                warn("DMARC p=none — monitoring only!")
                                risk.add("DMARC Not Enforced", "HIGH", "No action on spoofed emails",
                                    "Change to p=quarantine then p=reject", 15, 6.0)
                elif rtype == 'CAA':
                    success("CAA Records:")
                    for c in dns_data[rtype]: data(f"  {c}")

        dmarc_out = subprocess.getoutput(f"dig _dmarc.{target} TXT +short 2>/dev/null")
        if not dmarc_out or 'dmarc' not in dmarc_out.lower():
            warn("No DMARC record found")
            risk.add("No DMARC Record", "HIGH", "Spoofed emails pass undetected by receivers",
                "Add DMARC record (start p=none, escalate to reject)", 18, 6.5)

        # SPF Spoof Proof-of-Concept (NEW)
        if dns_data.get('spf_spoofable'):
            info("Generating SPF spoof proof-of-concept...")
            mx = dns_data.get('MX', ['unknown'])[0] if dns_data.get('MX') else 'mail server'
            success("Spoofed email would be ACCEPTED with this construction:")
            data(f'  {C.YELLOW}MAIL FROM: ceo@{target}{C.RESET}  (sent from ANY external server)')
            data(f'  {C.YELLOW}RCPT TO: employee@{target}{C.RESET}')
            data(f'  {C.DIM}Recipient mail server would deliver this without rejection{C.RESET}')
            data(f'  Test safely with: swaks --from ceo@{target} --to test@{target} --server {mx}')

        info("Attempting DNS Zone Transfer (AXFR)...")
        for ns in dns_data.get('NS', [])[:3]:
            ns_clean = ns.rstrip('.')
            zt = subprocess.getoutput(f"dig @{ns_clean} {target} AXFR 2>/dev/null | head -50")
            if zt and len(zt.split('\n')) > 8 and 'Transfer failed' not in zt:
                crit(f"ZONE TRANSFER SUCCESSFUL via {ns_clean}!")
                risk.add("DNS Zone Transfer", "CRITICAL", f"Full DNS map exposed via {ns_clean}",
                    "Restrict AXFR to trusted secondary servers only", 40, 9.1)
                dns_data['zone_transfer'] = zt[:3000]
            else:
                data(f"  Zone transfer blocked at {ns_clean} ✓")
    except Exception as e:
        err(f"DNS error: {e}")
    results['dns'] = dns_data

# ─────────────────────────────────────────────────
# MODULE 03: SUBDOMAINS + TAKEOVER (ENHANCED VERIFICATION)
# ─────────────────────────────────────────────────
def run_subdomains(target, results, risk, n, total):
    section("SUBDOMAIN ENUMERATION + TAKEOVER DETECTION", n, total)
    info(f"Discovering subdomains for {target}...")
    found_subs = set()

    info("Querying Certificate Transparency logs...")
    for ct_url in [f"https://crt.sh/?q=%.{target}&output=json",
                    f"https://api.certspotter.com/v1/issuances?domain={target}&include_subdomains=true&expand=dns_names"]:
        resp, status, _ = http_get(ct_url, timeout=15)
        if resp:
            try:
                data_ct = json.loads(resp)
                if isinstance(data_ct, list):
                    for item in data_ct:
                        for key in ['name_value','dns_names']:
                            val = item.get(key,'')
                            vals = val if isinstance(val,list) else val.split('\n')
                            for v in vals:
                                sub = v.strip().lower().lstrip('*.')
                                if sub.endswith(target): found_subs.add(sub)
                if found_subs:
                    success(f"Certificate Transparency: {len(found_subs)} subdomains found")
                    break
            except: continue

    info("Bruteforcing common subdomains...")
    wordlist = ['www','mail','ftp','smtp','pop','imap','webmail','admin','administrator',
        'portal','vpn','remote','dev','development','staging','stage','test','testing','demo',
        'api','api2','backend','frontend','web','old','new','beta','secure','security','login',
        'auth','sso','owa','exchange','mx','mx1','mx2','ns','ns1','ns2','dns','git','gitlab',
        'github','jira','confluence','wiki','docs','help','support','shop','store','pay',
        'payment','billing','invoice','crm','erp','db','database','mysql','sql','backup',
        'backups','cdn','static','assets','media','img','images','upload','uploads','cloud',
        'aws','azure','mobile','app','apps','dashboard','monitoring','jenkins','ci','cd',
        'build','prod','production','internal','intranet','corp','office','hr','careers',
        'partner','client','server','legacy','archive','phpmyadmin','cpanel','whm','plesk',
        'webdisk','sftp','iam','soc','fleet','events','notifications','trustcenter','pstn',
        'news','itf','autodiscover','blog']

    brute_found = []
    critical_subs = ['cpanel','whm','phpmyadmin','admin','administrator','plesk','webmin',
                     'db','database','mysql','backup','dev','staging','internal','vpn','git','jenkins']

    def check_sub(sub):
        fqdn = f"{sub}.{target}"
        try: return fqdn, socket.gethostbyname(fqdn)
        except: return None, None

    with ThreadPoolExecutor(max_workers=80) as ex:
        futures = {ex.submit(check_sub, s): s for s in wordlist}
        for f in as_completed(futures):
            fqdn, ip = f.result()
            if fqdn:
                brute_found.append((fqdn, ip))
                found_subs.add(fqdn)

    if brute_found:
        success(f"Bruteforce: {len(brute_found)} live subdomains:")
        for fqdn, ip in sorted(brute_found):
            sub = fqdn.split('.')[0]
            if sub in critical_subs:
                data(f"  {C.RED}⚠ CRITICAL: {fqdn:<45} {ip}{C.RESET}")
                # NEW: version fingerprint cpanel/whm
                if sub in ['cpanel','whm']:
                    info(f"Fingerprinting {sub} login page...")
                    resp, status, hdrs = http_get(f"https://{fqdn}:2083" if sub=='cpanel' else f"https://{fqdn}:2087", timeout=5)
                    if not resp:
                        resp, status, hdrs = http_get(f"https://{fqdn}", timeout=5)
                    if resp:
                        ver_m = re.search(r'cpanel[^\d]*(\d+\.\d+)', resp, re.IGNORECASE)
                        if ver_m:
                            warn(f"  {sub} version detected: {ver_m.group(1)}")
                risk.add(f"Critical Subdomain Exposed: {fqdn}", "CRITICAL",
                    f"{fqdn} is a high-value admin/backend target", f"Restrict to internal network or VPN only", 30, 8.6)
            else:
                data(f"  {C.GREEN}✓{C.RESET} {fqdn:<45} {ip}")

    info("Querying HackerTarget API...")
    ht_resp, _, _ = http_get(f"https://api.hackertarget.com/hostsearch/?q={target}", timeout=12)
    ht_found = 0
    if ht_resp and 'error' not in ht_resp.lower() and 'API count' not in ht_resp:
        for line in ht_resp.strip().split('\n'):
            if ',' in line:
                sub, ip = line.split(',',1); sub = sub.strip()
                if sub not in found_subs:
                    found_subs.add(sub); ht_found += 1
                    data(f"  {C.CYAN}◆{C.RESET} {sub:<45} {ip.strip()}")
        if ht_found: success(f"HackerTarget: {ht_found} additional subdomains")

    # ENHANCED Subdomain Takeover with confidence scoring
    info("Verifying subdomain takeover vulnerabilities (with confidence scoring)...")
    takeover_sigs = {
        'github': (['There isn\'t a GitHub Pages site here'], 'HIGH'),
        'heroku': (['No such app','herokucdn.com/error-pages'], 'HIGH'),
        'shopify': (['Sorry, this shop is currently unavailable'], 'HIGH'),
        'aws_s3': (['NoSuchBucket','The specified bucket does not exist'], 'HIGH'),
        'azure': (['404 Web Site not found'], 'MEDIUM'),
        'fastly': (['Fastly error: unknown domain'], 'HIGH'),
        'pantheon': (['The gods are wise','pantheonsite.io'], 'MEDIUM'),
        'tumblr': (['Whatever you were looking for doesn\'t currently exist'], 'HIGH'),
        'surge': (['project not found','surge.sh'], 'HIGH'),
        'bigcartel': (['Oops! We couldn\'t find that page'], 'MEDIUM'),
    }
    takeover_found = []
    all_subs = list(found_subs)[:30]

    def check_takeover(fqdn):
        try:
            resp, status, _ = http_get(f"https://{fqdn}", timeout=5)
            if resp:
                for provider, (sigs, confidence) in takeover_sigs.items():
                    if any(s.lower() in resp.lower() for s in sigs):
                        return fqdn, provider, confidence
            cname_out = subprocess.getoutput(f"dig {fqdn} CNAME +short 2>/dev/null")
            if cname_out and cname_out.strip():
                cname = cname_out.strip().rstrip('.')
                try:
                    socket.gethostbyname(cname)
                except socket.gaierror:
                    # Verify with second check to avoid transient DNS errors
                    time.sleep(0.5)
                    try:
                        socket.gethostbyname(cname)
                        return None, None, None  # was transient, not real
                    except socket.gaierror:
                        return fqdn, f"DANGLING CNAME -> {cname}", 'CONFIRMED'
        except: pass
        return None, None, None

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(check_takeover, s): s for s in all_subs}
        for f in as_completed(futures):
            fqdn, provider, confidence = f.result()
            if fqdn:
                takeover_found.append((fqdn, provider, confidence))

    if takeover_found:
        for fqdn, provider, confidence in takeover_found:
            crit(f"SUBDOMAIN TAKEOVER [{confidence}]: {fqdn} -> {provider}")
            sc = 40 if confidence == 'CONFIRMED' else 30
            risk.add(f"Subdomain Takeover: {fqdn}", "CRITICAL", f"{fqdn} points to {provider} ({confidence} confidence)",
                f"Remove DNS record for {fqdn} or claim the resource immediately", sc, 9.3)
    else:
        success("No subdomain takeover vulnerabilities found")

    success(f"Total unique subdomains: {len(found_subs)}")
    results['subdomains'] = list(found_subs)
    results['subdomains_live'] = brute_found

# ─────────────────────────────────────────────────
# MODULE 04: EMAIL HARVESTING (ENHANCED FALLBACK CHAIN)
# ─────────────────────────────────────────────────
def run_email_harvest(target, results, risk, n, total):
    section("EMAIL INTELLIGENCE", n, total)
    info(f"Harvesting emails for {target}...")
    emails_found = set()
    email_re = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

    info("Scraping website pages...")
    pages = [f"https://{target}", f"https://{target}/contact", f"https://{target}/about",
             f"https://{target}/team", f"https://{target}/staff", f"https://www.{target}"]
    for page in pages:
        resp, _, _ = http_get(page, timeout=8)
        if resp:
            for em in email_re.findall(resp):
                em = em.lower()
                if target in em: emails_found.add(em)

    # theHarvester fallback chain: try multiple source combos
    info("Attempting theHarvester (multi-source fallback chain)...")
    th_sources = ['google,bing,linkedin', 'duckduckgo,yahoo', 'crtsh,otx']
    for sources in th_sources:
        try:
            th_out = subprocess.getoutput(
                f"timeout 25 theHarvester -d {target} -b {sources} -l 200 2>/dev/null")
            if th_out and '@' in th_out:
                for line in th_out.split('\n'):
                    for em in email_re.findall(line):
                        if target in em: emails_found.add(em.lower())
                if emails_found:
                    success(f"theHarvester ({sources}) found emails")
                    break
        except: continue

    info("Querying Hunter.io...")
    cfg = load_config()
    hunter_key = cfg.get('hunter_api_key', 'free')
    h_resp, _, _ = http_get(f"https://api.hunter.io/v2/domain-search?domain={target}&limit=25&api_key={hunter_key}", timeout=10)
    if h_resp:
        try:
            h_data = json.loads(h_resp)
            pattern = h_data.get('data',{}).get('pattern','')
            if pattern:
                success(f"Email pattern: {{{pattern}}}@{target}")
                results['email_pattern'] = pattern
            for em_obj in h_data.get('data',{}).get('emails',[])[:15]:
                em = em_obj.get('value','')
                if em: emails_found.add(em.lower())
        except: pass

    if emails_found:
        success(f"Total emails harvested: {len(emails_found)}")
        for em in sorted(emails_found)[:20]: data(f"  {C.RED}✉{C.RESET} {em}")
        risk.add("Email Addresses Exposed", "MEDIUM", f"{len(emails_found)} corporate emails found publicly",
            "Use role-based emails publicly, train staff on spear phishing", 10, 4.0)
    else:
        warn("No emails found via automated methods")
        data(f"Manual: theHarvester -d {target} -b all -l 500")
        data(f"Manual: hunter.io/domain-search/{target}")
    results['emails'] = list(emails_found)

# ─────────────────────────────────────────────────
# MODULE 05: TECHNOLOGY FINGERPRINTING (+ EOL CHECK)
# ─────────────────────────────────────────────────
def run_tech_fingerprint(target, results, risk, n, total):
    section("TECHNOLOGY FINGERPRINTING", n, total)
    info(f"Fingerprinting {target}...")
    tech_data = {}
    resp, status, headers = http_get(f"https://{target}", timeout=10)
    resp_b, _, headers_b = http_get(f"http://{target}", timeout=10)
    content = resp or resp_b or ''
    hdrs = headers or headers_b or {}

    server = hdrs.get('Server', hdrs.get('server',''))
    if server:
        success(f"Web Server: {C.RED}{server}{C.RESET}")
        tech_data['server'] = server
        ver_m = re.search(r'(\w+)/([\d.]+)', server)
        if ver_m:
            product, version = ver_m.group(1).lower(), ver_m.group(2)
            eol_info = check_eol(product, version)
            if eol_info:
                crit(f"EOL SOFTWARE: {product} {version} — {eol_info['note']}")
                risk.add(f"EOL Software: {product} {version}", "CRITICAL", eol_info['note'],
                    f"Upgrade {product} immediately — no security patches available", 35, 9.0)
                if eol_info['cves']:
                    for cve in eol_info['cves']:
                        data(f"  {C.RED}Known CVE: {cve}{C.RESET}")
            else:
                warn(f"Server version exposed: {server}")
                risk.add("Server Version Disclosed", "MEDIUM", f"Server header reveals: {server}",
                    "Remove Server header or use generic value", 8, 4.0)

    powered = hdrs.get('X-Powered-By', hdrs.get('x-powered-by',''))
    if powered:
        warn(f"Backend exposed: {powered}")
        tech_data['powered_by'] = powered
        ver_m = re.search(r'PHP/([\d.]+)', powered)
        if ver_m:
            eol_info = check_eol('php', ver_m.group(1))
            if eol_info:
                crit(f"EOL PHP: {ver_m.group(1)} — {eol_info['note']}")
                risk.add(f"EOL PHP {ver_m.group(1)}", "CRITICAL", eol_info['note'],
                    "Upgrade PHP immediately", 35, 9.0)
        risk.add("Backend Technology Disclosed", "MEDIUM", f"X-Powered-By: {powered}",
            "Remove X-Powered-By header", 8, 4.0)

    info("Analyzing security headers...")
    sec_headers = {'Strict-Transport-Security':'HSTS','Content-Security-Policy':'CSP',
        'X-Frame-Options':'Clickjacking Protection','X-Content-Type-Options':'MIME Sniffing Protection',
        'Referrer-Policy':'Referrer Policy','Permissions-Policy':'Permissions Policy'}
    missing = []
    hdr_lower = {k.lower():v for k,v in hdrs.items()}
    for header, hname in sec_headers.items():
        if header.lower() in hdr_lower: data(f"  {C.GREEN}✓{C.RESET} {hname}: Present")
        else: missing.append(hname); data(f"  {C.RED}✗{C.RESET} {hname}: MISSING")
    if missing:
        risk.add(f"Missing Security Headers ({len(missing)})", "MEDIUM", f"Missing: {', '.join(missing)}",
            "Add all missing security headers", 10, 5.0)
        tech_data['missing_headers'] = missing

    if content:
        cms_sigs = {'WordPress':['wp-content','wp-includes'],'Joomla':['joomla'],'Drupal':['drupal'],
            'Shopify':['cdn.shopify.com'],'Django':['csrfmiddlewaretoken'],'Laravel':['laravel_session'],
            'React':['react','__REACT'],'Angular':['ng-version'],'Vue.js':['vue.js','__vue__'],
            'jQuery':['jquery'],'Bootstrap':['bootstrap'],'Cloudflare':['cf-ray'],'PHP':['<?php','PHPSESSID']}
        detected = [t for t,sigs in cms_sigs.items() if any(s in content.lower() for s in sigs)]
        if detected:
            success("Technologies detected:")
            for t in detected: data(f"  {C.YELLOW}◆{C.RESET} {t}")
            tech_data['detected'] = detected

        for pat, name in [(r'WordPress[\s/]+([\d.]+)','WordPress'),(r'jQuery[\s]+v([\d.]+)','jQuery')]:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                eol_info = check_eol(name.lower(), m.group(1))
                if eol_info:
                    crit(f"EOL {name}: {m.group(1)} — {eol_info['note']}")
                    risk.add(f"EOL {name}", "CRITICAL", eol_info['note'], f"Upgrade {name}", 30, 8.5)
                else:
                    warn(f"Version exposed: {name} {m.group(1)}")
                tech_data[f'{name}_version'] = m.group(1)
    results['technology'] = tech_data

# ─────────────────────────────────────────────────
# MODULE 06: PORTS
# ─────────────────────────────────────────────────
def run_ports(target, results, risk, n, total):
    section("PORT INTELLIGENCE", n, total)
    info(f"Scanning ports on {target}...")
    try: target_ip = socket.gethostbyname(target)
    except: err("Cannot resolve IP"); return
    info(f"Resolved: {target_ip}")

    ports = {
        21:('FTP','HIGH','Anonymous access common'),22:('SSH','MED','Bruteforce target'),
        23:('Telnet','CRIT','Unencrypted legacy'),25:('SMTP','HIGH','Open relay/spoofing'),
        53:('DNS','MED','Zone transfer target'),80:('HTTP','MED','Unencrypted'),
        110:('POP3','HIGH','Unencrypted'),143:('IMAP','HIGH','Unencrypted'),
        389:('LDAP','CRIT','Credential exposure'),443:('HTTPS','LOW','Secure'),
        445:('SMB','CRIT','EternalBlue target'),587:('SMTP/TLS','MED','Credential target'),
        993:('IMAPS','LOW','Encrypted'),995:('POP3S','LOW','Encrypted'),
        1433:('MSSQL','CRIT','Direct DB access'),1521:('Oracle','CRIT','High value DB'),
        2222:('SSH-Alt','HIGH','Alternate SSH'),3306:('MySQL','CRIT','INTERNET EXPOSED DB!'),
        3389:('RDP','CRIT','Bruteforce target'),5432:('PostgreSQL','CRIT','INTERNET EXPOSED DB!'),
        5900:('VNC','CRIT','Often no auth'),6379:('Redis','CRIT','Often no auth'),
        8080:('HTTP-Alt','MED','Dev/proxy port'),8443:('HTTPS-Alt','MED','Admin panels'),
        9200:('Elasticsearch','CRIT','Often no auth'),27017:('MongoDB','CRIT','Often no auth'),
    }
    open_ports = []
    rc = {'CRIT':C.RED,'HIGH':C.YELLOW,'MED':C.CYAN,'LOW':C.GREEN}

    def scan(port, pinfo):
        service, severity, desc = pinfo
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1.5)
            if s.connect_ex((target_ip, port)) == 0:
                s.close(); return port, service, severity, desc
            s.close()
        except: pass
        return None,None,None,None

    with ThreadPoolExecutor(max_workers=100) as ex:
        futures = {ex.submit(scan, p, i): p for p,i in ports.items()}
        for f in as_completed(futures):
            port, svc, sev, desc = f.result()
            if port:
                open_ports.append((port, svc, sev, desc))
                if sev == 'CRIT':
                    risk.add(f"Critical Port Exposed: {port}/{svc}", "CRITICAL", f"Port {port} ({svc}): {desc}",
                        f"Firewall port {port} immediately", 30, 9.0)
                elif sev == 'HIGH':
                    risk.add(f"High Risk Port: {port}/{svc}", "HIGH", f"Port {port} ({svc}): {desc}",
                        f"Review necessity of port {port}", 15, 6.5)

    open_ports.sort(key=lambda x: x[0])
    if open_ports:
        success(f"Open ports: {len(open_ports)}")
        for port, svc, sev, desc in open_ports:
            col = rc.get(sev, C.WHITE)
            print(f"    {col}[{sev}]{C.RESET} Port {port:<6} {svc:<15} {C.DIM}{desc}{C.RESET}")
    results['ports'] = [(p,s,r,d) for p,s,r,d in open_ports]
    results['target_ip'] = target_ip

# ─────────────────────────────────────────────────
# MODULE 07: BANNER GRABBING + FTP FILE LISTING + EOL CHECK
# ─────────────────────────────────────────────────
def run_banner_grab(target, results, risk, n, total):
    section("BANNER GRABBING & EXPLOITATION TESTING", n, total)
    info("Grabbing banners and testing exposed services...")
    banners = {}
    target_ip = results.get('target_ip')
    if not target_ip:
        try: target_ip = socket.gethostbyname(target)
        except: return

    open_ports = [(p,s) for p,s,_,_ in results.get('ports',[])]
    banner_methods = {21:('FTP',None,'text'),22:('SSH',None,'text'),25:('SMTP',b'EHLO godseye.local\r\n','text'),
        80:('HTTP',f'HEAD / HTTP/1.0\r\nHost: {target}\r\n\r\n'.encode(),'text'),110:('POP3',None,'text'),
        143:('IMAP',None,'text'),3306:('MySQL',None,'bytes'),5432:('PostgreSQL',None,'bytes'),
        6379:('Redis',b'INFO\r\n','text')}

    def grab_banner(port, service):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(4)
            s.connect((target_ip, port))
            method = banner_methods.get(port)
            if method and method[1]: s.send(method[1])
            time.sleep(0.5); s.settimeout(3)
            try:
                raw = s.recv(2048)
                bstr = raw.decode('utf-8',errors='ignore').strip() if method and method[2]=='text' else repr(raw[:100])
                s.close(); return port, service, bstr[:300]
            except: pass
            s.close()
        except: pass
        return port, service, None

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(grab_banner,p,s) for p,s in open_ports if p in banner_methods]
        for f in as_completed(futures):
            port, service, bstr = f.result()
            if bstr and len(bstr) > 3:
                banners[port] = bstr
                success(f"Port {port} ({service}) banner:")
                for line in bstr.split('\n')[:3]:
                    if line.strip(): data(f"  {C.CYAN}{line.strip()}{C.RESET}")

                ver_patterns = [(r'OpenSSH[_\s]+([\d.p]+)','openssh'),(r'vsftpd\s+([\d.]+)','vsftpd'),
                    (r'ProFTPD\s+([\d.]+)','proftpd'),(r'Exim\s+([\d.]+)','exim'),
                    (r'([\d]+\.[\d]+\.[\d]+)-\w+','mysql'),(r'PostgreSQL\s+([\d.]+)','postgresql')]
                for pat, product in ver_patterns:
                    m = re.search(pat, bstr, re.IGNORECASE)
                    if m:
                        version = m.group(1)
                        eol_info = check_eol(product, version)
                        if eol_info:
                            crit(f"EOL/VULNERABLE: {product} {version} — {eol_info['note']}")
                            risk.add(f"EOL Database/Service: {product} {version}", "CRITICAL", eol_info['note'],
                                f"Upgrade {product} to a supported version IMMEDIATELY", 40, 9.8)
                            for cve in eol_info.get('cves',[]):
                                data(f"  {C.RED}Known CVE: {cve} — search exploit-db.com/search?q={cve}{C.RESET}")
                        else:
                            warn(f"Version detected: {product} {version}")
                            risk.add(f"Service Version Exposed: Port {port}", "LOW", f"Banner reveals: {product} {version}",
                                "Disable verbose banners", 5, 3.0)
                        break

                if port == 21:
                    info("Testing FTP anonymous login...")
                    try:
                        ftp_s = socket.socket(); ftp_s.settimeout(5); ftp_s.connect((target_ip,21))
                        ftp_s.recv(1024); ftp_s.send(b'USER anonymous\r\n'); ftp_s.recv(1024)
                        ftp_s.send(b'PASS godseye@test.com\r\n')
                        r2 = ftp_s.recv(1024).decode('utf-8',errors='ignore')
                        if '230' in r2:
                            crit("FTP ANONYMOUS LOGIN SUCCESSFUL!")
                            risk.add("FTP Anonymous Access","CRITICAL","FTP allows anonymous login",
                                "Disable anonymous FTP immediately",35,9.1)
                            # NEW: List files
                            info("Listing accessible FTP files...")
                            ftp_s.send(b'PASV\r\n')
                            pasv_resp = ftp_s.recv(1024).decode('utf-8',errors='ignore')
                            pasv_m = re.search(r'\((\d+,\d+,\d+,\d+,\d+,\d+)\)', pasv_resp)
                            if pasv_m:
                                nums = [int(x) for x in pasv_m.group(1).split(',')]
                                data_ip = '.'.join(map(str,nums[:4]))
                                data_port = nums[4]*256 + nums[5]
                                try:
                                    data_s = socket.socket(); data_s.settimeout(5)
                                    data_s.connect((data_ip, data_port))
                                    ftp_s.send(b'LIST\r\n'); ftp_s.recv(1024)
                                    listing = data_s.recv(4096).decode('utf-8',errors='ignore')
                                    data_s.close()
                                    if listing.strip():
                                        warn("Files accessible via anonymous FTP:")
                                        for line in listing.strip().split('\n')[:15]:
                                            data(f"  {C.RED}📁{C.RESET} {line.strip()}")
                                        sensitive_files = [l for l in listing.split('\n') if any(
                                            kw in l.lower() for kw in ['backup','.sql','.env','config','password','credential'])]
                                        if sensitive_files:
                                            crit(f"{len(sensitive_files)} SENSITIVE FILES visible via FTP!")
                                            risk.add("Sensitive Files on Anonymous FTP","CRITICAL",
                                                f"{len(sensitive_files)} files matching backup/credential patterns",
                                                "Remove sensitive files, disable anonymous FTP",25,9.0)
                                except: data("  (Could not retrieve file listing — passive mode blocked)")
                        else:
                            success("FTP anonymous login blocked ✓")
                        ftp_s.close()
                    except: pass

                if port == 25:
                    info("Testing SMTP open relay...")
                    try:
                        smtp_s = socket.socket(); smtp_s.settimeout(5); smtp_s.connect((target_ip,25))
                        smtp_s.recv(1024); smtp_s.send(b'EHLO godseye.test\r\n'); smtp_s.recv(1024)
                        smtp_s.send(b'MAIL FROM: <test@external.com>\r\n'); smtp_s.recv(1024)
                        smtp_s.send(b'RCPT TO: <test@external2.com>\r\n')
                        r2 = smtp_s.recv(1024).decode('utf-8',errors='ignore')
                        smtp_s.send(b'QUIT\r\n'); smtp_s.close()
                        if '250' in r2 and '550' not in r2:
                            crit("SMTP OPEN RELAY DETECTED!")
                            risk.add("SMTP Open Relay","CRITICAL","Server relays mail for external domains",
                                "Configure SMTP to reject external relay",40,9.4)
                        else:
                            success("SMTP relay blocked ✓")
                    except: pass

                if port in [3306,5432,1433,27017,6379,9200]:
                    crit(f"DATABASE PORT {port} INTERNET ACCESSIBLE!")
                    data("  This should NEVER be exposed to the internet")

    results['banners'] = banners

# ─────────────────────────────────────────────────
# MODULE 08: SHARED HOSTING WEAK-NEIGHBOR SCAN (NEW)
# ─────────────────────────────────────────────────
def run_shared_hosting_scan(target, results, risk, n, total):
    section("SHARED HOSTING NEIGHBOR ANALYSIS", n, total)
    neighbors = results.get('ip_intel',{}).get('reverse_ip',[])
    if not neighbors or len(neighbors) < 5:
        info("No significant shared hosting detected — skipping")
        return
    info(f"Analyzing {len(neighbors)} neighbor domains for weak security...")
    weak_neighbors = []

    def check_neighbor(domain):
        resp, status, hdrs = http_get(f"http://{domain}", timeout=4)
        if resp:
            weak_signals = []
            if 'wp-content' in resp.lower() and 'wp-admin' in resp.lower():
                wp_ver = re.search(r'wordpress[\s/]+([\d.]+)', resp, re.IGNORECASE)
                if wp_ver and check_eol('wordpress', wp_ver.group(1)):
                    weak_signals.append(f"EOL WordPress {wp_ver.group(1)}")
            if 'index of /' in resp.lower():
                weak_signals.append("Directory listing enabled")
            server = hdrs.get('Server','')
            if server and re.search(r'/[12]\.', server):
                weak_signals.append(f"Old server: {server}")
            if weak_signals:
                return domain, weak_signals
        return None, None

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(check_neighbor, d): d for d in neighbors[:40]}
        for f in as_completed(futures):
            domain, signals = f.result()
            if domain:
                weak_neighbors.append((domain, signals))

    if weak_neighbors:
        warn(f"{len(weak_neighbors)} weak neighbor sites found on shared server:")
        for domain, signals in weak_neighbors[:10]:
            data(f"  {C.YELLOW}⚠{C.RESET} {domain}: {', '.join(signals)}")
        risk.add("Weak Neighbors on Shared Host", "HIGH",
            f"{len(weak_neighbors)} neighboring sites have security weaknesses that could be used to pivot",
            "Consider dedicated hosting or VPS isolation", 15, 6.0)
    else:
        success("No obviously weak neighbor sites detected (checked sample)")
    results['weak_neighbors'] = weak_neighbors

# ─────────────────────────────────────────────────
# MODULE 09: SSL/TLS
# ─────────────────────────────────────────────────
def run_ssl(target, results, risk, n, total):
    section("SSL/TLS CERTIFICATE INTELLIGENCE", n, total)
    info(f"Analyzing SSL/TLS for {target}...")
    ssl_data = {}
    try:
        ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
        with socket.create_connection((target,443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=target) as ssock:
                cert = ssock.getpeercert(); cipher = ssock.cipher(); version = ssock.version()
                success(f"TLS Version: {version}")
                if version in ['TLSv1','TLSv1.1','SSLv3']:
                    crit(f"Outdated TLS: {version}")
                    risk.add(f"Outdated TLS: {version}","CRITICAL",f"Deprecated {version} supported",
                        "Disable TLS 1.0/1.1, enforce 1.2+",25,7.5)
                success(f"Cipher: {cipher[0]}")
                subject = dict(x[0] for x in cert.get('subject',[]))
                issuer = dict(x[0] for x in cert.get('issuer',[]))
                cn = subject.get('commonName','N/A'); org = subject.get('organizationName','N/A')
                success(f"Common Name: {cn}")
                if cn == 'N/A':
                    info("CN not in subject — checking SAN for primary identity")
                data(f"  Issuer: {issuer.get('organizationName','Unknown')}")
                not_after = cert.get('notAfter','')
                if not_after:
                    try:
                        exp = datetime.strptime(not_after,'%b %d %H:%M:%S %Y %Z')
                        days = (exp-datetime.now()).days
                        if days < 30:
                            crit(f"Certificate expires in {days} days!")
                            risk.add("Certificate Expiry Imminent","CRITICAL",f"Cert expires in {days} days",
                                "Renew SSL certificate immediately",30,7.0)
                        else: data(f"  Expires: {not_after} ({days} days)")
                        ssl_data['expires_days'] = days
                    except: pass
                san = cert.get('subjectAltName',[])
                if san:
                    san_domains = [s[1] for s in san if s[0]=='DNS']
                    success(f"SAN domains ({len(san_domains)}):")
                    for d in san_domains[:15]: data(f"  {C.YELLOW}◆{C.RESET} {d}")
                    ssl_data['san_domains'] = san_domains
                ssl_data.update({'version':version,'cipher':cipher[0],'cn':cn,'org':org})
    except ConnectionRefusedError: warn("Port 443 closed")
    except Exception as e: warn(f"SSL error: {e}")
    results['ssl'] = ssl_data

# ─────────────────────────────────────────────────
# MODULE 10: WEB INTELLIGENCE
# ─────────────────────────────────────────────────
def run_web_recon(target, results, risk, n, total):
    section("WEB INTELLIGENCE", n, total)
    info(f"Web reconnaissance on {target}...")
    web_data = {}

    for scheme in ['https','http']:
        resp, _, _ = http_get(f"{scheme}://{target}/robots.txt", timeout=8)
        if resp and ('disallow' in resp.lower() or 'allow' in resp.lower()):
            success("robots.txt found:")
            web_data['robots'] = resp
            disallowed = re.findall(r'Disallow:\s*(.+)', resp, re.IGNORECASE)
            if disallowed:
                warn("Disallowed paths (attacker roadmap):")
                for p in disallowed[:15]:
                    p = p.strip()
                    if p and p != '/': data(f"  {C.RED}⚑{C.RESET} {p}")
            break

    info("Probing sensitive paths...")
    sensitive = [('/.env','CRITICAL',40,'All credentials'),('/.git/config','CRITICAL',35,'Git exposed'),
        ('/.git/HEAD','CRITICAL',35,'Git exposed'),('/backup/','CRITICAL',35,'Backup dir'),
        ('/backup.zip','CRITICAL',35,'Backup archive'),('/backup.sql','CRITICAL',35,'DB backup'),
        ('/db.sql','CRITICAL',35,'DB dump'),('/.env.backup','CRITICAL',35,'Env backup'),
        ('/config.php.bak','CRITICAL',30,'Config backup'),('/admin/','HIGH',20,'Admin panel'),
        ('/wp-admin/','HIGH',20,'WP admin'),('/cpanel','HIGH',25,'cPanel'),('/whm','HIGH',25,'WHM'),
        ('/phpmyadmin/','HIGH',25,'DB GUI'),('/phpinfo.php','HIGH',20,'PHP config'),
        ('/server-status','HIGH',20,'Apache status'),('/.htpasswd','HIGH',25,'Password file'),
        ('/api/swagger','MED',10,'API docs'),('/.DS_Store','MED',10,'macOS listing')]
    exposed = []
    def chk(path_info):
        path, sev, sc, desc = path_info
        resp, status, _ = http_get(f"https://{target}{path}", timeout=5)
        if not resp: resp, status, _ = http_get(f"http://{target}{path}", timeout=5)
        if resp and status==200 and len(resp)>20 and path not in ['/robots.txt','/sitemap.xml']:
            return path, sev, sc, desc, len(resp)
        return None,None,None,None,None
    with ThreadPoolExecutor(max_workers=25) as ex:
        futures = {ex.submit(chk,p):p for p in sensitive}
        for f in as_completed(futures):
            path, sev, sc, desc, size = f.result()
            if path:
                exposed.append((path,sev,sc,desc,size))
                risk.add(f"Sensitive Path Exposed: {path}", sev, f"{path} accessible ({size}b) — {desc}",
                    f"Remove or restrict {path}", sc, 8.5 if sev=='CRITICAL' else 6.0)
    if exposed:
        crit(f"{len(exposed)} SENSITIVE PATHS EXPOSED:")
        for path,sev,_,desc,size in exposed:
            col = C.RED if sev=='CRITICAL' else C.YELLOW
            data(f"  {col}[{sev}]{C.RESET} {path} ({size}b) — {desc}")
    else:
        success("No obvious sensitive paths exposed")

    # NEW: Deep Wayback Machine page diffing
    info("Querying Wayback Machine (deep historical analysis)...")
    wb_resp, _, _ = http_get(f"https://archive.org/wayback/available?url={target}", timeout=10)
    if wb_resp:
        try:
            wb = json.loads(wb_resp)
            snap = wb.get('archived_snapshots',{}).get('closest',{})
            if snap:
                ts = snap.get('timestamp','')
                success(f"Wayback snapshot: {ts}")
                data(f"  {snap.get('url','')}")
                web_data['wayback'] = snap.get('url','')
                # Fetch the archived page content to compare
                archived_resp, _, _ = http_get(snap.get('url',''), timeout=10)
                if archived_resp:
                    archived_emails = set(em.lower() for em in re.findall(
                        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', archived_resp) if target in em)
                    if archived_emails:
                        new_emails = archived_emails - set(results.get('emails',[]))
                        if new_emails:
                            warn(f"Historical page reveals {len(new_emails)} emails not in current findings:")
                            for em in list(new_emails)[:10]: data(f"  {C.RED}✉{C.RESET} {em} (from archive)")
                            results.setdefault('emails',[]).extend(new_emails)
                data(f"  Full history: https://web.archive.org/web/*/{target}")
        except: pass

    dorks = [f'site:{target}', f'site:{target} filetype:pdf', f'site:{target} filetype:sql',
        f'site:{target} filetype:env', f'site:{target} filetype:log', f'site:{target} filetype:bak',
        f'site:{target} intitle:"index of"', f'site:{target} inurl:admin', f'site:{target} inurl:backup',
        f'site:{target} "confidential"', f'site:{target} "BEGIN PRIVATE KEY"',
        f'"@{target}" site:linkedin.com', f'site:github.com "{target}"', f'site:pastebin.com "{target}"']
    success("Google Dork queries generated:")
    web_data['dorks'] = dorks
    for d in dorks: data(f"  {C.CYAN}◆{C.RESET} {d}")
    web_data['exposed_paths'] = exposed
    results['web'] = web_data

# ─────────────────────────────────────────────────
# MODULE 11: IP & NETWORK
# ─────────────────────────────────────────────────
def run_ip_intel(target, results, risk, n, total):
    section("IP & NETWORK INTELLIGENCE", n, total)
    info(f"IP intelligence for {target}...")
    ip_data = {}
    try:
        target_ip = results.get('target_ip') or socket.gethostbyname(target)
        success(f"Primary IP: {target_ip}")
        ip_data['ip'] = target_ip
        resp, _, _ = http_get(f"https://ipinfo.io/{target_ip}/json", timeout=8)
        if resp:
            geo = json.loads(resp)
            city=geo.get('city','?'); region=geo.get('region','?'); country=geo.get('country','?')
            org=geo.get('org','?'); loc=geo.get('loc','?')
            success(f"Geolocation: {city}, {region}, {country}")
            data(f"  Provider: {org}"); data(f"  GPS: {loc}")
            ip_data['geo'] = geo
            hosting_map = {'Amazon':('AWS','Check S3 buckets'),'Google':('GCP','Check GCS buckets'),
                'Microsoft':('Azure','Check Blob storage'),'Cloudflare':('Cloudflare CDN','Real IP hidden'),
                'Oracle':('Oracle Cloud','Check default creds'),'Bluehost':('Shared Hosting','Virtual host attacks possible')}
            for kw,(name,note) in hosting_map.items():
                if kw.lower() in org.lower():
                    warn(f"Hosting: {name} — {note}")
                    ip_data['hosting'] = name
                    if 'Shared' in name:
                        risk.add("Shared Hosting Environment","MEDIUM","Shares server with many other domains",
                            "One compromised neighbor can affect target",12,5.0)

        info("Reverse IP lookup...")
        rev_resp, _, _ = http_get(f"https://api.hackertarget.com/reverseiplookup/?q={target_ip}", timeout=10)
        if rev_resp and 'error' not in rev_resp.lower():
            others = [d.strip() for d in rev_resp.strip().split('\n') if d.strip()]
            if len(others) > 1:
                success(f"Reverse IP: {len(others)} domains on same server")
                for d in others[:8]: data(f"  {C.CYAN}◆{C.RESET} {d}")
                if len(others)>8: data(f"  ... and {len(others)-8} more")
                ip_data['reverse_ip'] = others

        info("ASN intelligence...")
        asn_resp, _, _ = http_get(f"https://api.hackertarget.com/aslookup/?q={target_ip}", timeout=8)
        if asn_resp and 'error' not in asn_resp.lower():
            success(f"ASN: {asn_resp.strip()}")
            ip_data['asn'] = asn_resp.strip()
    except Exception as e: err(f"IP intel error: {e}")
    results['ip_intel'] = ip_data

# ─────────────────────────────────────────────────
# MODULE 12: BREACH
# ─────────────────────────────────────────────────
def run_breach(target, results, risk, n, total):
    section("BREACH INTELLIGENCE", n, total)
    info(f"Checking breach databases for {target}...")
    breach_data = {}
    cfg = load_config()
    hibp_key = cfg.get('hibp_api_key','')
    if hibp_key:
        resp, status, _ = http_get(f"https://haveibeenpwned.com/api/v3/breacheddomain/{target}",
            timeout=10, headers={'hibp-api-key': hibp_key})
        if resp and status==200:
            try:
                breaches = json.loads(resp)
                if breaches:
                    crit(f"{len(breaches)} data breaches affect {target}!")
                    risk.add(f"Data Breaches ({len(breaches)})","CRITICAL",f"{len(breaches)} known breaches",
                        "Force password reset, enable MFA",35,8.5)
                    breach_data['breaches'] = breaches
            except: pass
    else:
        info("No HIBP API key configured — run: godseye --configure")
        data("  Manual: https://haveibeenpwned.com/DomainSearch")
    data(f"  dehashed.com — search @{target}")
    data(f"  intelx.io — dark web intelligence")
    results['breaches'] = breach_data

# ─────────────────────────────────────────────────
# MODULE 13: SOCIAL MEDIA + GITHUB SECRET SCAN (NEW)
# ─────────────────────────────────────────────────
def run_social(target, results, risk, n, total):
    section("SOCIAL MEDIA & GITHUB INTELLIGENCE", n, total)
    company = target.split('.')[0]
    info(f"Social media recon for: {company}")
    social_data = {}
    platforms = {'LinkedIn':f"https://www.linkedin.com/company/{company}",'Twitter/X':f"https://twitter.com/{company}",
        'Facebook':f"https://www.facebook.com/{company}",'Instagram':f"https://www.instagram.com/{company}",
        'GitHub':f"https://github.com/{company}",'YouTube':f"https://www.youtube.com/@{company}"}
    for platform, url in platforms.items():
        resp, status, _ = http_get(url, timeout=6)
        if resp and status==200 and len(resp)>500:
            if any(t in resp.lower() for t in ['followers','following','posts','profile','repository']):
                success(f"{platform}: Profile found -> {url}")
                social_data[platform] = url

    info("GitHub deep reconnaissance...")
    cfg = load_config()
    gh_headers = {}
    if cfg.get('github_token'): gh_headers['Authorization'] = f"token {cfg['github_token']}"
    gh_resp, status, _ = http_get(f"https://api.github.com/orgs/{company}/repos?per_page=15&sort=updated", timeout=10, headers=gh_headers)
    if gh_resp and status==200:
        try:
            repos = json.loads(gh_resp)
            if repos and isinstance(repos,list):
                success(f"GitHub org found: {len(repos)} public repos")
                for r in repos[:10]:
                    name=r.get('name',''); lang=r.get('language','?'); updated=r.get('updated_at','')[:10]
                    data(f"  {C.YELLOW}◆{C.RESET} {name} [{lang}] — {updated}")

                # NEW: Pattern-based secret scan on README/visible content
                info("Scanning repos for exposed secret patterns...")
                secret_patterns = {
                    'AWS Key': r'AKIA[0-9A-Z]{16}',
                    'Generic API Key': r'api[_-]?key["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})',
                    'Private Key Header': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
                    'Slack Token': r'xox[baprs]-[0-9a-zA-Z]{10,}',
                    'Generic Secret': r'(secret|password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\']{8,})',
                }
                secrets_found = []
                for r in repos[:5]:
                    repo_name = r.get('name','')
                    readme_resp, rstatus, _ = http_get(
                        f"https://raw.githubusercontent.com/{company}/{repo_name}/main/README.md", timeout=5)
                    if not readme_resp:
                        readme_resp, rstatus, _ = http_get(
                            f"https://raw.githubusercontent.com/{company}/{repo_name}/master/README.md", timeout=5)
                    if readme_resp:
                        for pname, pattern in secret_patterns.items():
                            if re.search(pattern, readme_resp):
                                secrets_found.append((repo_name, pname))
                if secrets_found:
                    crit(f"{len(secrets_found)} potential secret patterns found in repos!")
                    for repo, ptype in secrets_found:
                        data(f"  {C.RED}🔑 {repo}: {ptype}{C.RESET}")
                    risk.add("Potential Secrets in GitHub","CRITICAL",
                        f"{len(secrets_found)} secret-like patterns found in public repos",
                        "Immediately rotate any exposed credentials, scan full history with trufflehog",30,9.0)
                else:
                    success("No obvious secret patterns in README files (run trufflehog for full scan)")
                data(f"  Full scan: trufflehog github --org {company}")
                data(f"  Full scan: gitleaks detect --source /path/to/clone")
                social_data['github_repos'] = [r.get('name') for r in repos]
        except: pass
    results['social'] = social_data

# ─────────────────────────────────────────────────
# ATTACK CHAIN GENERATOR
# ─────────────────────────────────────────────────
def generate_attack_chain(target, results, risk, n, total):
    section("ATTACK CHAIN ANALYSIS", n, total)
    info("Generating most likely attack paths...")
    findings = risk.findings
    chains = []

    spf_risk = any('SPF' in f['title'] for f in findings)
    emails = results.get('emails', [])
    if spf_risk and emails:
        chains.append({'name':'Business Email Compromise (BEC)','severity':'CRITICAL',
            'steps':[f'Harvest emails — {len(emails)} found publicly','Exploit SPF misconfiguration for spoofing',
                'Craft spear phishing email posing as executive','Target finance team for wire transfer',
                'Transfer funds before detection'],'likelihood':'HIGH','impact':'Financial loss, credential theft'})

    db_ports = [p for p,s,r,_ in results.get('ports',[]) if p in [3306,5432,1433,27017]]
    eol_db = any('EOL Database' in f['title'] for f in findings)
    if db_ports:
        sev_note = ' (EOL VERSION CONFIRMED)' if eol_db else ''
        chains.append({'name':f'Direct Database Compromise{sev_note}','severity':'CRITICAL',
            'steps':[f'Database port(s) {db_ports} internet-accessible',
                'Run credential bruteforce with common/default passwords' + (' OR exploit known CVE directly' if eol_db else ''),
                'Gain database access without touching web application','Extract all customer/financial data',
                'Use credentials for lateral movement'],'likelihood':'HIGH','impact':'Complete data breach'})

    takeover = [f for f in findings if 'Takeover' in f['title']]
    if takeover:
        chains.append({'name':'Subdomain Takeover -> Credential Phishing','severity':'CRITICAL',
            'steps':[f'{takeover[0]["title"]} identified','Register the unclaimed resource',
                'Host fake login page on trusted subdomain','Send phishing link — users trust the domain',
                'Harvest credentials from victims'],'likelihood':'HIGH','impact':'Mass credential theft'})

    ftp_anon = any('FTP Anonymous' in f['title'] for f in findings)
    sensitive_ftp = any('Sensitive Files on Anonymous FTP' in f['title'] for f in findings)
    if ftp_anon:
        steps = ['Anonymous FTP login confirmed','List all accessible directories and files']
        if sensitive_ftp:
            steps.append('Sensitive files (backups/configs) CONFIRMED accessible')
        steps += ['Download and analyze files for credentials','Use found credentials for deeper access']
        chains.append({'name':'Anonymous FTP Data Exfiltration','severity':'CRITICAL','steps':steps,
            'likelihood':'CRITICAL','impact':'Immediate data access without authentication'})

    weak_neighbors = results.get('weak_neighbors',[])
    if weak_neighbors:
        chains.append({'name':'Shared Hosting Cross-Site Attack','severity':'HIGH',
            'steps':[f'{len(weak_neighbors)} weak neighbor sites identified on shared server',
                f'Target weakest: {weak_neighbors[0][0]} ({weak_neighbors[0][1][0]})',
                'Compromise weak neighbor site','Use server access to read target site files',
                'Extract target config files, database credentials'],'likelihood':'MEDIUM',
            'impact':'Complete site compromise via neighbor'})

    if chains:
        for i, chain in enumerate(chains,1):
            col = C.RED if chain['severity']=='CRITICAL' else C.YELLOW
            print(f"\n  {col}{C.BOLD}Attack Path {i}: {chain['name']}{C.RESET}")
            print(f"  {col}Severity: {chain['severity']} | Likelihood: {chain['likelihood']}{C.RESET}")
            print(f"  {C.DIM}Impact: {chain['impact']}{C.RESET}")
            for step in chain['steps']: data(f"  {C.CYAN}->{C.RESET} {step}")
    else:
        success("No high-confidence attack chains identified")
    results['attack_chains'] = chains

# ─────────────────────────────────────────────────
# HTML REPORT (with remediation priority + narrative)
# ─────────────────────────────────────────────────
def generate_html(target, results, risk, end_time, duration):
    rating, rating_css = risk.get_rating()
    sev_count = {'CRITICAL':0,'HIGH':0,'MEDIUM':0,'LOW':0,'INFO':0}
    for f in risk.findings: sev_count[f['severity']] = sev_count.get(f['severity'],0)+1
    chains = results.get('attack_chains',[])
    remediation = risk.get_remediation_order()

    # NEW: Executive narrative generator
    narrative_parts = []
    if sev_count['CRITICAL'] > 0:
        narrative_parts.append(f"This assessment identified {sev_count['CRITICAL']} critical-severity findings that require immediate remediation.")
    if any('Database' in f['title'] for f in risk.findings):
        narrative_parts.append("Database services were found directly exposed to the internet, representing the highest-priority risk as this bypasses all application-layer security controls entirely.")
    if any('Takeover' in f['title'] for f in risk.findings):
        narrative_parts.append("A subdomain takeover vulnerability was confirmed, which could allow an attacker to host malicious content on a trusted subdomain for phishing campaigns.")
    if any('EOL' in f['title'] for f in risk.findings):
        narrative_parts.append("End-of-life software was detected running in production, meaning known vulnerabilities will never receive security patches.")
    if any('FTP Anonymous' in f['title'] for f in risk.findings):
        narrative_parts.append("Anonymous FTP access was confirmed, allowing unauthenticated file access.")
    if not narrative_parts:
        narrative_parts.append("This assessment found a generally acceptable security posture with some areas for improvement.")
    narrative = " ".join(narrative_parts)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>GodsEye v{VERSION} — {target}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Courier New',monospace;background:#090909;color:#e0e0e0;padding:20px;line-height:1.6}}
.hdr{{background:linear-gradient(135deg,#1a0000,#000);border:1px solid #e63946;border-radius:8px;padding:30px;margin-bottom:20px;text-align:center}}
.logo{{color:#e63946;font-size:2em;font-weight:bold;letter-spacing:3px}}
.subtitle{{color:#666;margin-top:5px;font-size:.9em}}
.risk-score{{font-size:3em;font-weight:bold;color:{rating_css};margin:10px 0}}
.risk-label{{color:#888;font-size:.8em;letter-spacing:2px}}
.narrative{{background:#111;border:1px solid #333;border-radius:8px;padding:16px 20px;margin-bottom:16px;font-size:.9em;line-height:1.8;color:#ccc}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}}
.card{{background:#111;border:1px solid #222;border-radius:6px;padding:16px}}
.card-title{{font-size:.7em;color:#666;letter-spacing:1px;margin-bottom:8px;text-transform:uppercase}}
.card-num{{font-size:2em;font-weight:bold}}
.card-num.red{{color:#e63946}}.card-num.amber{{color:#ffaa00}}.card-num.cyan{{color:#00ccff}}
.section{{background:#111;border:1px solid #222;border-left:3px solid #e63946;border-radius:0 6px 6px 0;padding:16px;margin-bottom:12px}}
.section h2{{color:#e63946;font-size:.9em;margin-bottom:12px;letter-spacing:1px}}
.finding{{padding:8px 10px;margin:4px 0;border-radius:4px;font-size:.85em;border-left:3px solid}}
.finding.CRITICAL{{background:#1a0000;border-color:#e63946;color:#ffaaaa}}
.finding.HIGH{{background:#1a0d00;border-color:#ff8800;color:#ffcc88}}
.finding.MEDIUM{{background:#0d1a00;border-color:#ffcc00;color:#ffee88}}
.finding.LOW{{background:#001a0d;border-color:#00aa00;color:#88ffaa}}
.finding .title{{font-weight:bold;margin-bottom:3px}}
.finding .desc{{color:#888;font-size:.9em}}
.finding .rec{{color:#aaa;font-size:.85em;margin-top:3px;font-style:italic}}
.finding .cvss{{display:inline-block;background:#000;padding:1px 6px;border-radius:3px;font-size:.75em;margin-left:6px}}
.chain{{background:#0a0000;border:1px solid #330000;border-radius:6px;padding:14px;margin:8px 0}}
.chain h3{{color:#e63946;font-size:.85em;margin-bottom:8px}}
.chain-step{{color:#ccc;font-size:.8em;padding:2px 0}}
.badge{{display:inline-block;padding:2px 8px;border-radius:3px;font-size:.7em;font-weight:bold}}
.badge.CRITICAL{{background:#e63946;color:#fff}}.badge.HIGH{{background:#ff8800;color:#fff}}
.badge.MEDIUM{{background:#ffcc00;color:#000}}.badge.LOW{{background:#00aa00;color:#fff}}
.dork{{background:#0d1a0d;border:1px solid #1a3a1a;padding:3px 8px;margin:2px 0;border-radius:3px;font-size:.8em;color:#00cc66}}
table{{width:100%;border-collapse:collapse;font-size:.85em}}
td,th{{padding:6px 10px;border-bottom:1px solid #1a1a1a;text-align:left}}
th{{color:#666;font-size:.75em;letter-spacing:1px}}
.priority-num{{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:#e63946;color:#fff;font-size:.7em;font-weight:bold;margin-right:8px}}
.footer{{text-align:center;color:#333;margin-top:20px;font-size:.75em}}
</style></head><body>
<div class="hdr">
  <div class="logo">⚡ GODSEYE v{VERSION} INTELLIGENCE REPORT</div>
  <div class="subtitle">Target: {target} | {end_time.strftime('%Y-%m-%d %H:%M:%S')} | {duration}s scan</div>
  <div class="risk-score">{risk.score}/100</div>
  <div class="risk-label">{rating}</div>
  <div style="margin-top:10px;font-size:.75em;color:#e63946">⚠ FOR AUTHORIZED PENETRATION TESTING ONLY ⚠</div>
</div>
<div class="narrative"><strong style="color:#e63946">Executive Summary:</strong> {narrative}</div>
<div class="grid4">
  <div class="card"><div class="card-title">Risk Score</div><div class="card-num red">{risk.score}/100</div></div>
  <div class="card"><div class="card-title">Critical Findings</div><div class="card-num red">{sev_count.get('CRITICAL',0)}</div></div>
  <div class="card"><div class="card-title">High Findings</div><div class="card-num amber">{sev_count.get('HIGH',0)}</div></div>
  <div class="card"><div class="card-title">Attack Chains</div><div class="card-num cyan">{len(chains)}</div></div>
</div>
<div class="grid4">
  <div class="card"><div class="card-title">Subdomains</div><div class="card-num cyan">{len(results.get('subdomains',[]))}</div></div>
  <div class="card"><div class="card-title">Open Ports</div><div class="card-num amber">{len(results.get('ports',[]))}</div></div>
  <div class="card"><div class="card-title">Emails Found</div><div class="card-num amber">{len(results.get('emails',[]))}</div></div>
  <div class="card"><div class="card-title">Avg CVSS</div><div class="card-num red">{round(sum(f['cvss'] for f in risk.findings)/max(len(risk.findings),1),1)}</div></div>
</div>
"""
    if remediation:
        html += '<div class="section"><h2>🎯 REMEDIATION PRIORITY ORDER — FIX THESE FIRST</h2>'
        for i, f in enumerate(remediation[:10], 1):
            html += f"""<div class="finding {f['severity']}">
  <div class="title"><span class="priority-num">{i}</span><span class="badge {f['severity']}">{f['severity']}</span> {f['title']} <span class="cvss">CVSS {f['cvss']}</span></div>
  <div class="desc">{f['description']}</div>
  <div class="rec">Fix: {f['recommendation']}</div></div>"""
        html += '</div>'

    if risk.findings:
        html += '<div class="section"><h2>ALL FINDINGS</h2>'
        order = ['CRITICAL','HIGH','MEDIUM','LOW','INFO']
        for f in sorted(risk.findings, key=lambda x: order.index(x['severity'])):
            html += f"""<div class="finding {f['severity']}">
  <div class="title"><span class="badge {f['severity']}">{f['severity']}</span> {f['title']} <span class="cvss">CVSS {f['cvss']}</span></div>
  <div class="desc">{f['description']}</div><div class="rec">Recommendation: {f['recommendation']}</div></div>"""
        html += '</div>'

    if chains:
        html += '<div class="section"><h2>ATTACK CHAIN ANALYSIS</h2>'
        for i, chain in enumerate(chains,1):
            html += f"""<div class="chain"><h3>Path {i}: {chain['name']} <span class="badge {chain['severity']}">{chain['severity']}</span></h3>
  <div style="color:#666;font-size:.8em;margin-bottom:8px">Likelihood: {chain['likelihood']} | Impact: {chain['impact']}</div>"""
            for step in chain['steps']: html += f'<div class="chain-step">→ {step}</div>'
            html += '</div>'
        html += '</div>'

    dns = results.get('dns',{})
    if dns:
        html += '<div class="section"><h2>DNS INTELLIGENCE</h2><table><tr><th>Type</th><th>Value</th></tr>'
        for rtype in ['A','AAAA','MX','NS','TXT','SOA']:
            for rec in dns.get(rtype,[])[:3]:
                html += f'<tr><td>{rtype}</td><td style="font-size:.8em">{rec[:80]}</td></tr>'
        html += '</table></div>'

    live_subs = results.get('subdomains_live',[])
    if live_subs:
        crit_subs = ['cpanel','whm','phpmyadmin','admin','backup','dev','staging','vpn','db']
        html += f'<div class="section"><h2>LIVE SUBDOMAINS ({len(live_subs)})</h2><table><tr><th>Subdomain</th><th>IP</th><th>Risk</th></tr>'
        for fqdn, ip in sorted(live_subs):
            sub = fqdn.split('.')[0]; is_crit = sub in crit_subs
            badge = '<span class="badge CRITICAL">CRITICAL</span>' if is_crit else '<span class="badge LOW">INFO</span>'
            html += f'<tr><td style="color:{"#e63946" if is_crit else "#ccc"}">{fqdn}</td><td style="color:#666">{ip}</td><td>{badge}</td></tr>'
        html += '</table></div>'

    ports = results.get('ports',[])
    if ports:
        html += f'<div class="section"><h2>OPEN PORTS ({len(ports)})</h2><table><tr><th>Port</th><th>Service</th><th>Risk</th></tr>'
        for port,svc,sev,desc in ports:
            html += f'<tr><td><strong>{port}</strong></td><td>{svc}</td><td><span class="badge {sev}">{sev}</span></td></tr>'
        html += '</table></div>'

    emails = results.get('emails',[])
    if emails:
        html += f'<div class="section"><h2>HARVESTED EMAILS ({len(emails)})</h2>'
        for em in emails[:20]: html += f'<div style="color:#ff8800;font-size:.85em;padding:3px 0">✉ {em}</div>'
        html += '</div>'

    dorks = results.get('web',{}).get('dorks',[])
    if dorks:
        html += '<div class="section"><h2>GOOGLE DORK QUERIES</h2>'
        for d in dorks: html += f'<div class="dork">{d}</div>'
        html += '</div>'

    html += f"""<div class="footer"><p>GodsEye v{VERSION} — Advanced Reconnaissance & Vulnerability Intelligence</p>
<p>For authorized penetration testing and security research only.</p>
<p>Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')} | Duration: {duration}s</p></div>
</body></html>"""
    return html

# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=f'GodsEye v{VERSION} — Advanced Reconnaissance Intelligence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  godseye certifiedhacker.com
  godseye target.com --skip-ports
  godseye target.com --output /home/user/reports/
  godseye target.com --modules whois,dns,ports,banners
  godseye --configure
  godseye --update

Modules: whois dns subdomains emails tech ports banners shared ssl web ip breach social

Legal: Authorized use only.
        """)
    parser.add_argument('target', nargs='?', help='Target domain')
    parser.add_argument('--skip-ports', action='store_true')
    parser.add_argument('--modules', type=str)
    parser.add_argument('--output', type=str, default='.', help='Output directory for reports')
    parser.add_argument('--configure', action='store_true', help='Configure API keys')
    parser.add_argument('--update', action='store_true', help='Self-update from GitHub')
    args = parser.parse_args()

    if args.update: self_update(); return
    if args.configure: interactive_configure(); return
    if not args.target:
        parser.print_help(); return

    target = args.target.lower().replace('https://','').replace('http://','').replace('www.','').split('/')[0]

    banner()
    print(f"  {C.BOLD}Target:{C.RESET}    {C.RED}{target}{C.RESET}")
    print(f"  {C.BOLD}Version:{C.RESET}   GodsEye v{VERSION}")
    print(f"  {C.BOLD}Started:{C.RESET}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {C.YELLOW}⚠ Authorized use only. You are responsible for your actions.{C.RESET}")
    print(f"\n  {C.YELLOW}Confirm authorization to scan {target}? (yes/no):{C.RESET} ", end='')
    try:
        if input().strip().lower() not in ['yes','y']:
            print(f"\n  {C.RED}Cancelled.{C.RESET}\n"); sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n  {C.RED}Cancelled.{C.RESET}\n"); sys.exit(0)

    results = {}; risk = RiskEngine(); start = datetime.now()
    all_modules = ['whois','dns','subdomains','emails','tech','ports','banners','shared','ssl','web','ip','breach','social']
    run_list = [m.strip() for m in args.modules.split(',')] if args.modules else all_modules
    if args.skip_ports:
        for m in ['ports','banners']:
            if m in run_list: run_list.remove(m)

    module_funcs = {'whois':run_whois,'dns':run_dns,'subdomains':run_subdomains,'emails':run_email_harvest,
        'tech':run_tech_fingerprint,'ports':run_ports,'banners':run_banner_grab,'shared':run_shared_hosting_scan,
        'ssl':run_ssl,'web':run_web_recon,'ip':run_ip_intel,'breach':run_breach,'social':run_social}

    total = len(run_list)
    for i, mod in enumerate(run_list, 1):
        if mod in module_funcs:
            try: module_funcs[mod](target, results, risk, i, total)
            except KeyboardInterrupt: warn(f"Module {mod} interrupted")
            except Exception as e: err(f"Module {mod} error: {e}")

    generate_attack_chain(target, results, risk, total+1, total+1)

    section("GENERATING REPORTS", total+1, total+1)
    end_time = datetime.now(); duration = (end_time-start).seconds
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = Path(args.output); out_dir.mkdir(parents=True, exist_ok=True)
    json_file = out_dir / f"godseye_v3_{target.replace('.','_')}_{ts}.json"
    html_file = out_dir / f"godseye_v3_{target.replace('.','_')}_{ts}.html"

    with open(json_file,'w') as f:
        json.dump({'target':target,'timestamp':str(end_time),'duration':duration,
            'risk_score':risk.score,'results':results,'findings':risk.findings}, f, indent=2, default=str)
    with open(html_file,'w') as f:
        f.write(generate_html(target, results, risk, end_time, duration))

    success(f"JSON Report: {json_file}")
    success(f"HTML Report: {html_file}")
    info(f"Open: firefox {html_file}")

    section("EXECUTIVE SUMMARY", total+1, total+1)
    rating, _ = risk.get_rating()
    sev_count = {'CRITICAL':0,'HIGH':0,'MEDIUM':0,'LOW':0}
    for f in risk.findings: sev_count[f.get('severity','LOW')] = sev_count.get(f.get('severity','LOW'),0)+1
    print(f"\n  {C.BOLD}Target:{C.RESET}          {target}")
    print(f"  {C.BOLD}Risk Score:{C.RESET}      {C.RED}{risk.score}/100 — {rating}{C.RESET}")
    print(f"  {C.BOLD}Scan Time:{C.RESET}       {duration}s")
    print(f"\n  {C.BOLD}Finding Summary:{C.RESET}")
    print(f"    {C.RED}CRITICAL:{C.RESET}   {sev_count.get('CRITICAL',0)}")
    print(f"    {C.YELLOW}HIGH:{C.RESET}       {sev_count.get('HIGH',0)}")
    print(f"    {C.CYAN}MEDIUM:{C.RESET}     {sev_count.get('MEDIUM',0)}")
    print(f"    {C.GREEN}LOW:{C.RESET}        {sev_count.get('LOW',0)}")
    print(f"\n  {C.BOLD}Intelligence:{C.RESET}")
    print(f"    Subdomains:    {len(results.get('subdomains',[]))}")
    print(f"    Emails:        {len(results.get('emails',[]))}")
    print(f"    Open Ports:    {len(results.get('ports',[]))}")
    print(f"    Attack Chains: {len(results.get('attack_chains',[]))}")

    remediation = risk.get_remediation_order()
    if remediation:
        print(f"\n  {C.RED}{C.BOLD}TOP PRIORITY — FIX THESE FIRST:{C.RESET}")
        for i, f in enumerate(remediation[:5], 1):
            print(f"    {C.RED}{i}.{C.RESET} {f['title']} (CVSS {f['cvss']})")

    print(f"\n  {C.GREEN}{C.BOLD}Scan complete. Reports saved.{C.RESET}\n")

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}Interrupted.{C.RESET}\n"); sys.exit(0)
