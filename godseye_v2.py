#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║                        GODSEYE v2.0                              ║
║          Advanced Reconnaissance & Vulnerability Intel           ║
║       "See Everything. Miss Nothing. Strike First."              ║
╚══════════════════════════════════════════════════════════════════╝

NEW IN v2.0:
  → Banner grabbing on every open port
  → Anonymous FTP login test
  → CVE correlation engine (NVD lookup)
  → Subdomain takeover detection
  → SMTP open relay test
  → SPF ?all detected as CRITICAL
  → Attack chain generator
  → Risk scoring engine (0-100)
  → Shared hosting attack surface
  → Enhanced email harvesting
  → crt.sh with multiple fallbacks
  → Database exposure alerts
  → Full attack narrative in report

Usage:
  python3 godseye_v2.py certifiedhacker.com
  python3 godseye_v2.py target.com --skip-ports
  python3 godseye_v2.py target.com --modules whois,dns,ports,banners
  python3 godseye_v2.py target.com --stealth    (slower, less noise)

Legal: Authorized use only. You are responsible for your actions.
"""

import sys, os, json, socket, ssl, time, re, argparse, threading
import ipaddress, subprocess, hashlib
from datetime import datetime
from urllib import request, parse, error
from concurrent.futures import ThreadPoolExecutor, as_completed

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
{C.RESET}{C.CYAN}  Advanced Reconnaissance & Vulnerability Intelligence v2.0{C.RESET}
{C.DIM}  "See Everything. Miss Nothing. Strike First."{C.RESET}
{C.YELLOW}  ⚠  Authorized penetration testing only  ⚠{C.RESET}
""")

def info(m):    print(f"  {C.CYAN}[*]{C.RESET} {m}")
def success(m): print(f"  {C.GREEN}[+]{C.RESET} {m}")
def warn(m):    print(f"  {C.YELLOW}[!]{C.RESET} {m}")
def err(m):     print(f"  {C.RED}[-]{C.RESET} {m}")
def data(m):    print(f"      {C.WHITE}{m}{C.RESET}")
def crit(m):    print(f"  {C.RED}{C.BOLD}[CRITICAL]{C.RESET} {C.RED}{m}{C.RESET}")
def section(t):
    print(f"\n{C.BOLD}{C.BLUE}{'═'*62}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}  {t}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}{'═'*62}{C.RESET}")

# ─────────────────────────────────────────────────
# RISK ENGINE
# ─────────────────────────────────────────────────
class RiskEngine:
    """Tracks all findings and computes weighted risk score"""
    def __init__(self):
        self.findings = []
        self.score = 0

    def add(self, title, severity, description, recommendation, score):
        """severity: CRITICAL=40, HIGH=20, MEDIUM=10, LOW=5, INFO=1"""
        self.findings.append({
            'title': title, 'severity': severity,
            'description': description,
            'recommendation': recommendation,
            'score': score
        })
        self.score = min(100, self.score + score)
        color = {
            'CRITICAL': C.RED, 'HIGH': C.YELLOW,
            'MEDIUM': C.CYAN, 'LOW': C.GREEN, 'INFO': C.DIM
        }.get(severity, C.WHITE)
        print(f"  {color}[{severity}]{C.RESET} {title}")

    def get_rating(self):
        if self.score >= 80: return "CRITICAL RISK", C.RED
        if self.score >= 60: return "HIGH RISK", C.RED
        if self.score >= 40: return "MEDIUM RISK", C.YELLOW
        if self.score >= 20: return "LOW RISK", C.GREEN
        return "MINIMAL RISK", C.GREEN

# ─────────────────────────────────────────────────
# HTTP HELPER
# ─────────────────────────────────────────────────
def http_get(url, timeout=8, headers=None, allow_redirects=True):
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
# MODULE 01: WHOIS (ENHANCED)
# ─────────────────────────────────────────────────
def run_whois(target, results, risk):
    section("MODULE 01 — WHOIS INTELLIGENCE")
    info(f"Running WHOIS on {target}...")
    whois_data = {}

    try:
        out = subprocess.getoutput(f"whois {target} 2>/dev/null")
        if out and len(out) > 50:
            success("WHOIS data retrieved")
            patterns = {
                'Registrar':        r'Registrar:\s*(.+)',
                'Created':          r'Creation Date:\s*(.+)',
                'Expires':          r'Registry Expiry Date:\s*(.+)',
                'Updated':          r'Updated Date:\s*(.+)',
                'Name Servers':     r'Name Server:\s*(.+)',
                'Registrant Org':   r'Registrant Organization:\s*(.+)',
                'Registrant Email': r'Registrant Email:\s*(.+)',
                'Admin Email':      r'Admin Email:\s*(.+)',
                'Status':           r'Domain Status:\s*(.+)',
                'DNSSEC':           r'DNSSEC:\s*(.+)',
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
                                risk.add("Domain Expiry Critical", "CRITICAL",
                                    f"Domain expires in {days} days",
                                    "Renew domain immediately and enable auto-renewal", 35)
                            elif days < 90:
                                warn(f"Domain expires in {days} days — hijack risk!")
                                risk.add("Domain Expiry Warning", "HIGH",
                                    f"Domain expires in {days} days",
                                    "Renew domain and enable auto-renewal", 15)
                        except: pass
                    elif field == 'Registrant Email':
                        em = unique[0]
                        data(f"{C.RED}Registrant Email:{C.RESET} {em}")
                        if 'private' in em.lower() or 'proxy' in em.lower() or 'protection' in em.lower():
                            success("WHOIS privacy enabled — email hidden")
                        else:
                            warn("Real registrant email exposed — social engineering risk")
                            risk.add("WHOIS Email Exposed", "MEDIUM",
                                "Real registrant email publicly visible",
                                "Enable WHOIS privacy protection with registrar", 8)
                    elif field == 'Name Servers':
                        for ns in unique[:4]:
                            data(f"Name Server: {ns}")
                        if any(target.replace('www.','') in ns.lower() for ns in unique):
                            warn("Self-hosted nameservers — zone transfer may be possible!")
                            whois_data['self_hosted_ns'] = True
                            risk.add("Self-Hosted Nameservers", "MEDIUM",
                                "Company manages own DNS — zone transfer misconfiguration risk",
                                "Restrict AXFR to trusted IPs only", 10)
                        else:
                            data(f"Third-party DNS provider (safer)")
                    elif field == 'DNSSEC':
                        if 'unsigned' in unique[0].lower():
                            warn("DNSSEC unsigned — DNS spoofing/cache poisoning possible")
                            risk.add("DNSSEC Disabled", "MEDIUM",
                                "DNSSEC not implemented — DNS cache poisoning possible",
                                "Enable DNSSEC on domain", 8)
                    else:
                        data(f"{field}: {', '.join(unique[:2])}")
    except Exception as e:
        err(f"WHOIS error: {e}")

    results['whois'] = whois_data

# ─────────────────────────────────────────────────
# MODULE 02: DNS (ENHANCED WITH FULL SPF ANALYSIS)
# ─────────────────────────────────────────────────
def run_dns(target, results, risk):
    section("MODULE 02 — DNS INTELLIGENCE")
    info(f"Extracting all DNS records for {target}...")
    dns_data = {}

    try:
        record_types = ['A','AAAA','MX','NS','TXT','SOA','CNAME','SRV','CAA']
        for rtype in record_types:
            out = subprocess.getoutput(f"dig {target} {rtype} +short 2>/dev/null")
            if out and out.strip() and ';' not in out:
                dns_data[rtype] = [l.strip() for l in out.strip().split('\n') if l.strip()]
                if rtype == 'A':
                    for ip in dns_data[rtype]:
                        success(f"A Record: {ip}")
                elif rtype == 'MX':
                    success("MX Records (mail infrastructure):")
                    for mx in dns_data[rtype]: data(f"  Mail Server: {mx}")
                elif rtype == 'NS':
                    success("Name Servers:")
                    for ns in dns_data[rtype]: data(f"  {ns}")
                elif rtype == 'TXT':
                    success("TXT Records:")
                    for txt in dns_data[rtype]:
                        data(f"  {txt}")
                        # Full SPF analysis
                        if 'v=spf1' in txt.lower():
                            if '+all' in txt:
                                crit("SPF PassAll (+all) — ANYONE can send as this domain!")
                                risk.add("SPF PassAll Critical", "CRITICAL",
                                    "SPF record uses +all — any server can send email as this domain",
                                    "Change to -all immediately", 40)
                            elif '?all' in txt:
                                crit("SPF Neutral (?all) — no enforcement, spoofing trivially possible!")
                                risk.add("SPF Neutral", "CRITICAL",
                                    "SPF ?all means no enforcement — email spoofing is trivial",
                                    "Change ?all to -all to enforce SPF", 35)
                            elif '~all' in txt:
                                warn("SPF SoftFail (~all) — email spoofing POSSIBLE")
                                risk.add("SPF SoftFail", "HIGH",
                                    "SPF ~all accepts suspicious emails — spoofing likely succeeds",
                                    "Change ~all to -all", 20)
                            elif '-all' in txt:
                                success("SPF HardFail (-all) — email spoofing blocked ✓")
                                dns_data['spf_ok'] = True
                        if 'v=dmarc1' in txt.lower():
                            if 'p=reject' in txt.lower():
                                success("DMARC p=reject — strong email protection ✓")
                            elif 'p=quarantine' in txt.lower():
                                warn("DMARC p=quarantine — partial protection")
                            elif 'p=none' in txt.lower():
                                warn("DMARC p=none — monitoring only, no enforcement!")
                                risk.add("DMARC Not Enforced", "HIGH",
                                    "DMARC p=none means no action taken on spoofed emails",
                                    "Change to p=quarantine then p=reject", 15)
                        if 'v=dkim' in txt.lower():
                            success("DKIM record found ✓")
                elif rtype == 'CAA':
                    success(f"CAA Records (cert authority restrictions):")
                    for caa in dns_data[rtype]: data(f"  {caa}")

        # Check for missing DMARC
        dmarc_out = subprocess.getoutput(f"dig _dmarc.{target} TXT +short 2>/dev/null")
        if not dmarc_out or 'dmarc' not in dmarc_out.lower():
            warn("No DMARC record found — email spoofing undetected by receivers")
            risk.add("No DMARC Record", "HIGH",
                "Missing DMARC record — spoofed emails pass undetected",
                "Add DMARC record starting with p=none then escalate", 18)

        # Zone transfer
        info("Attempting DNS Zone Transfer (AXFR)...")
        for ns in dns_data.get('NS', [])[:3]:
            ns_clean = ns.rstrip('.')
            zt = subprocess.getoutput(f"dig @{ns_clean} {target} AXFR 2>/dev/null | head -50")
            if zt and len(zt.split('\n')) > 8 and 'Transfer failed' not in zt:
                crit(f"ZONE TRANSFER SUCCESSFUL via {ns_clean}!")
                risk.add("DNS Zone Transfer", "CRITICAL",
                    f"Full DNS map exposed via {ns_clean}",
                    "Restrict AXFR to trusted secondary servers only", 40)
                dns_data['zone_transfer'] = zt[:3000]
                for line in zt.split('\n')[:20]:
                    if line.strip(): data(f"  {line}")
            else:
                data(f"  Zone transfer blocked at {ns_clean} ✓")

    except Exception as e:
        err(f"DNS error: {e}")
        try:
            ip = socket.gethostbyname(target)
            dns_data['A'] = [ip]
            success(f"A Record (fallback): {ip}")
        except: pass

    results['dns'] = dns_data

# ─────────────────────────────────────────────────
# MODULE 03: SUBDOMAINS (ENHANCED + TAKEOVER CHECK)
# ─────────────────────────────────────────────────
def run_subdomains(target, results, risk):
    section("MODULE 03 — SUBDOMAIN ENUMERATION + TAKEOVER DETECTION")
    info(f"Discovering subdomains for {target}...")
    found_subs = set()

    # crt.sh with multiple fallbacks
    info("Querying Certificate Transparency logs...")
    ct_sources = [
        f"https://crt.sh/?q=%.{target}&output=json",
        f"https://api.certspotter.com/v1/issuances?domain={target}&include_subdomains=true&expand=dns_names",
    ]
    for ct_url in ct_sources:
        resp, status, _ = http_get(ct_url, timeout=15)
        if resp:
            try:
                data_ct = json.loads(resp)
                if isinstance(data_ct, list):
                    for item in data_ct:
                        for key in ['name_value', 'dns_names']:
                            val = item.get(key, '')
                            if isinstance(val, list):
                                for v in val:
                                    sub = v.strip().lower().lstrip('*.')
                                    if sub.endswith(target): found_subs.add(sub)
                            elif isinstance(val, str):
                                for sub in val.split('\n'):
                                    sub = sub.strip().lower().lstrip('*.')
                                    if sub.endswith(target): found_subs.add(sub)
                if found_subs:
                    success(f"Certificate Transparency: {len(found_subs)} subdomains found")
                    break
            except: continue

    # Wordlist bruteforce
    info("Bruteforcing common subdomains...")
    wordlist = [
        'www','mail','ftp','smtp','pop','imap','webmail','admin','administrator',
        'portal','vpn','remote','dev','development','staging','stage','test',
        'testing','demo','api','api2','backend','frontend','web','old','new',
        'beta','secure','security','login','auth','sso','owa','exchange','mx',
        'mx1','mx2','ns','ns1','ns2','dns','git','gitlab','github','jira',
        'confluence','wiki','docs','help','support','shop','store','pay',
        'payment','billing','invoice','crm','erp','db','database','mysql',
        'sql','backup','backups','cdn','static','assets','media','img',
        'images','upload','uploads','cloud','aws','azure','mobile','app',
        'apps','dashboard','monitoring','nagios','zabbix','kibana','grafana',
        'jenkins','ci','cd','build','prod','production','internal','intranet',
        'extranet','corp','corporate','office','hr','careers','recruitment',
        'partner','partners','client','clients','server','server2','legacy',
        'archive','phpmyadmin','cpanel','whm','plesk','webdisk','sftp',
        'iam','soc','fleet','events','notifications','trustcenter','pstn',
        'news','itf','autodiscover','ciphershield','blog'
    ]

    brute_found = []
    critical_subs = ['cpanel','whm','phpmyadmin','admin','administrator',
                     'plesk','webmin','db','database','mysql','backup',
                     'dev','staging','internal','vpn','git','jenkins']

    def check_sub(sub):
        fqdn = f"{sub}.{target}"
        try:
            ip = socket.gethostbyname(fqdn)
            return fqdn, ip
        except: return None, None

    with ThreadPoolExecutor(max_workers=80) as ex:
        futures = {ex.submit(check_sub, s): s for s in wordlist}
        for f in as_completed(futures):
            fqdn, ip = f.result()
            if fqdn:
                brute_found.append((fqdn, ip))
                found_subs.add(fqdn)

    if brute_found:
        success(f"Bruteforce: {len(brute_found)} live subdomains found:")
        for fqdn, ip in sorted(brute_found):
            sub = fqdn.split('.')[0]
            if sub in critical_subs:
                data(f"  {C.RED}⚠ CRITICAL: {fqdn:<45} {ip}{C.RESET}")
                risk.add(f"Critical Subdomain Exposed: {fqdn}", "CRITICAL",
                    f"{fqdn} is a high-value admin/backend target",
                    f"Restrict {fqdn} to internal network or VPN only", 30)
            else:
                data(f"  {C.GREEN}✓{C.RESET} {fqdn:<45} {ip}")

    # HackerTarget API
    info("Querying HackerTarget API...")
    ht_resp, _, _ = http_get(f"https://api.hackertarget.com/hostsearch/?q={target}", timeout=12)
    ht_found = 0
    if ht_resp and 'error' not in ht_resp.lower() and 'API count' not in ht_resp:
        for line in ht_resp.strip().split('\n'):
            if ',' in line:
                sub, ip = line.split(',',1)
                sub = sub.strip()
                if sub not in found_subs:
                    found_subs.add(sub)
                    ht_found += 1
                    data(f"  {C.CYAN}◆{C.RESET} {sub:<45} {ip.strip()}")
        if ht_found: success(f"HackerTarget: {ht_found} additional subdomains")

    # Subdomain Takeover Detection
    info("Checking for subdomain takeover vulnerabilities...")
    takeover_signatures = {
        'github': ['There isn\'t a GitHub Pages site here', 'For root URLs'],
        'heroku': ['No such app', 'herokucdn.com/error-pages'],
        'shopify': ['Sorry, this shop is currently unavailable'],
        'aws_s3': ['NoSuchBucket', 'The specified bucket does not exist'],
        'azure': ['404 Web Site not found', 'azure.com'],
        'fastly': ['Fastly error: unknown domain'],
        'pantheon': ['The gods are wise', 'pantheonsite.io'],
        'sendgrid': ['The provided authorization grant is invalid'],
        'tumblr': ['Whatever you were looking for doesn\'t currently exist'],
        'wordpress': ['Do you want to register'],
        'helpjuice': ['We could not find what you\'re looking for'],
        'helpscout': ['No settings were found for this company'],
        'cargo': ['If you\'re moving your domain away from Cargo'],
        'statuspage': ['You are being redirected'],
        'surge': ['project not found', 'surge.sh'],
        'bigcartel': ['Oops! We couldn\'t find that page'],
        'acquia': ['The site you are looking for could not be found'],
    }

    takeover_found = []
    all_subs = list(found_subs)[:30]

    def check_takeover(fqdn):
        try:
            resp, status, _ = http_get(f"https://{fqdn}", timeout=5)
            if resp:
                for provider, signatures in takeover_signatures.items():
                    if any(sig.lower() in resp.lower() for sig in signatures):
                        return fqdn, provider
            # Check CNAME for dangling
            cname_out = subprocess.getoutput(f"dig {fqdn} CNAME +short 2>/dev/null")
            if cname_out and cname_out.strip():
                cname = cname_out.strip().rstrip('.')
                # Try resolving the CNAME target
                try:
                    socket.gethostbyname(cname)
                except socket.gaierror:
                    return fqdn, f"DANGLING CNAME → {cname}"
        except: pass
        return None, None

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(check_takeover, s): s for s in all_subs}
        for f in as_completed(futures):
            fqdn, provider = f.result()
            if fqdn:
                takeover_found.append((fqdn, provider))

    if takeover_found:
        for fqdn, provider in takeover_found:
            crit(f"SUBDOMAIN TAKEOVER POSSIBLE: {fqdn} → {provider}")
            risk.add(f"Subdomain Takeover: {fqdn}", "CRITICAL",
                f"{fqdn} points to {provider} which is unclaimed",
                f"Remove DNS record for {fqdn} or claim the resource", 40)
    else:
        success("No obvious subdomain takeover vulnerabilities found")

    success(f"Total unique subdomains: {len(found_subs)}")
    results['subdomains'] = list(found_subs)
    results['subdomains_live'] = brute_found

# ─────────────────────────────────────────────────
# MODULE 04: EMAIL HARVESTING (ENHANCED)
# ─────────────────────────────────────────────────
def run_email_harvest(target, results, risk):
    section("MODULE 04 — EMAIL INTELLIGENCE")
    info(f"Harvesting emails for {target}...")
    emails_found = set()
    email_re = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

    # Web scraping with multiple pages
    info("Scraping website pages for email addresses...")
    pages = [
        f"https://{target}", f"https://{target}/contact",
        f"https://{target}/about", f"https://{target}/team",
        f"https://{target}/staff", f"https://{target}/people",
        f"https://{target}/contact-us", f"https://www.{target}",
    ]
    for page in pages:
        resp, _, _ = http_get(page, timeout=8)
        if resp:
            for em in email_re.findall(resp):
                em = em.lower()
                if not any(skip in em for skip in ['example.','test@','noreply','no-reply',
                    'support@','info@','admin@'] if not em.endswith(f'@{target}')):
                    if target.split('.')[0] in em or em.endswith(f'@{target}'):
                        emails_found.add(em)

    # theHarvester integration
    info("Attempting theHarvester integration...")
    try:
        th_out = subprocess.getoutput(
            f"theHarvester -d {target} -b google,bing,linkedin -l 200 2>/dev/null | grep '@'")
        if th_out:
            for line in th_out.split('\n'):
                matches = email_re.findall(line)
                for em in matches:
                    if target in em: emails_found.add(em.lower())
            if emails_found:
                success(f"theHarvester found emails")
    except: pass

    # Hunter.io
    info("Querying Hunter.io...")
    h_resp, _, _ = http_get(
        f"https://api.hunter.io/v2/domain-search?domain={target}&limit=25", timeout=10)
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
        for em in sorted(emails_found)[:20]:
            data(f"  {C.RED}✉{C.RESET} {em}")
        risk.add("Email Addresses Exposed", "MEDIUM",
            f"{len(emails_found)} corporate emails found in public sources",
            "Use role-based emails publicly, train staff on spear phishing", 10)
    else:
        warn("No emails found — try: theHarvester -d {target} -b all")

    results['emails'] = list(emails_found)

# ─────────────────────────────────────────────────
# MODULE 05: TECHNOLOGY FINGERPRINTING
# ─────────────────────────────────────────────────
def run_tech_fingerprint(target, results, risk):
    section("MODULE 05 — TECHNOLOGY FINGERPRINTING")
    info(f"Fingerprinting {target}...")
    tech_data = {}

    resp, status, headers = http_get(f"https://{target}", timeout=10)
    resp_b, _, headers_b = http_get(f"http://{target}", timeout=10)
    content = resp or resp_b or ''
    hdrs = headers or headers_b or {}

    # Server
    server = hdrs.get('Server', hdrs.get('server',''))
    if server:
        success(f"Web Server: {C.RED}{server}{C.RESET}")
        tech_data['server'] = server
        ver_m = re.search(r'([\d]+\.[\d]+\.[\d]+)', server)
        if ver_m:
            warn(f"Server version exposed: {server}")
            risk.add("Server Version Disclosed", "MEDIUM",
                f"Server header reveals: {server}",
                "Remove Server header or use generic value", 8)

    # X-Powered-By
    powered = hdrs.get('X-Powered-By', hdrs.get('x-powered-by',''))
    if powered:
        warn(f"Backend exposed: {powered}")
        tech_data['powered_by'] = powered
        risk.add("Backend Technology Disclosed", "MEDIUM",
            f"X-Powered-By: {powered}",
            "Remove X-Powered-By header", 8)

    # Security Headers
    info("Analyzing security headers...")
    sec_headers = {
        'Strict-Transport-Security': 'HSTS',
        'Content-Security-Policy': 'CSP',
        'X-Frame-Options': 'Clickjacking Protection',
        'X-Content-Type-Options': 'MIME Sniffing Protection',
        'Referrer-Policy': 'Referrer Policy',
        'Permissions-Policy': 'Permissions Policy',
    }
    missing = []
    hdr_lower = {k.lower():v for k,v in hdrs.items()}
    for header, name in sec_headers.items():
        if header.lower() in hdr_lower:
            data(f"  {C.GREEN}✓{C.RESET} {name}: Present")
        else:
            missing.append(name)
            data(f"  {C.RED}✗{C.RESET} {name}: MISSING")
    if missing:
        risk.add(f"Missing Security Headers ({len(missing)})", "MEDIUM",
            f"Missing: {', '.join(missing)}",
            "Add all missing security headers to web server config", 10)
        tech_data['missing_headers'] = missing

    # CMS Detection
    if content:
        cms_sigs = {
            'WordPress':  ['wp-content','wp-includes','wordpress'],
            'Joomla':     ['joomla','/components/com_'],
            'Drupal':     ['drupal','sites/default/files'],
            'Shopify':    ['cdn.shopify.com','myshopify'],
            'Django':     ['csrfmiddlewaretoken','django'],
            'Laravel':    ['laravel_session','laravel'],
            'React':      ['react','__REACT','react-dom'],
            'Angular':    ['ng-version','angular'],
            'Vue.js':     ['vue.js','__vue__','nuxt'],
            'jQuery':     ['jquery'],
            'Bootstrap':  ['bootstrap'],
            'Cloudflare': ['__cfduid','cf-ray','cloudflare'],
            'PHP':        ['<?php','PHPSESSID','.php'],
            'ASP.NET':    ['__VIEWSTATE','asp.net','aspx'],
        }
        detected = []
        cl = content.lower()
        for tech, sigs in cms_sigs.items():
            if any(s in cl for s in sigs):
                detected.append(tech)
        if detected:
            success("Technologies detected:")
            for t in detected: data(f"  {C.YELLOW}◆{C.RESET} {t}")
            tech_data['detected'] = detected

        # Version extraction
        ver_patterns = [
            (r'WordPress[\s/]+([\d.]+)', 'WordPress'),
            (r'jQuery[\s]+v([\d.]+)', 'jQuery'),
            (r'Bootstrap[\s]+v([\d.]+)', 'Bootstrap'),
            (r'Angular[\s]+([\d.]+)', 'Angular'),
        ]
        for pat, name in ver_patterns:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                warn(f"Version exposed: {name} {m.group(1)} — check CVEs!")
                tech_data[f'{name}_version'] = m.group(1)
                risk.add(f"{name} Version Exposed", "LOW",
                    f"{name} version {m.group(1)} visible in source",
                    f"Update {name} and hide version info", 5)

    results['technology'] = tech_data

# ─────────────────────────────────────────────────
# MODULE 06: PORT SCAN (ENHANCED)
# ─────────────────────────────────────────────────
def run_ports(target, results, risk):
    section("MODULE 06 — PORT INTELLIGENCE")
    info(f"Scanning ports on {target}...")
    warn("For comprehensive scan: nmap -sV -sC -A -p- {target}")

    try:
        target_ip = socket.gethostbyname(target)
        info(f"Resolved: {target_ip}")
    except:
        err("Cannot resolve IP"); return

    ports = {
        21:   ('FTP',      'HIGH', 'File transfer — anonymous access common'),
        22:   ('SSH',      'MED',  'Secure Shell — bruteforce target'),
        23:   ('Telnet',   'CRIT', 'Unencrypted remote — legacy risk'),
        25:   ('SMTP',     'HIGH', 'Mail server — open relay / spoofing'),
        53:   ('DNS',      'MED',  'DNS — zone transfer target'),
        80:   ('HTTP',     'MED',  'Unencrypted web'),
        110:  ('POP3',     'HIGH', 'Email retrieval — unencrypted'),
        143:  ('IMAP',     'HIGH', 'Email — unencrypted'),
        389:  ('LDAP',     'CRIT', 'Directory service — credential exposure'),
        443:  ('HTTPS',    'LOW',  'Secure web'),
        445:  ('SMB',      'CRIT', 'Windows sharing — EternalBlue target'),
        587:  ('SMTP/TLS', 'MED',  'Mail submission — credential target'),
        993:  ('IMAPS',    'LOW',  'Encrypted IMAP'),
        995:  ('POP3S',    'LOW',  'Encrypted POP3'),
        1433: ('MSSQL',    'CRIT', 'SQL Server — direct DB access'),
        1521: ('Oracle',   'CRIT', 'Oracle DB — high value target'),
        2222: ('SSH-Alt',  'HIGH', 'Alternate SSH'),
        3306: ('MySQL',    'CRIT', 'MySQL — direct DB access — INTERNET EXPOSED!'),
        3389: ('RDP',      'CRIT', 'Remote Desktop — bruteforce target'),
        5432: ('PostgreSQL','CRIT','PostgreSQL — direct DB access — INTERNET EXPOSED!'),
        5900: ('VNC',      'CRIT', 'Remote desktop — often no auth'),
        6379: ('Redis',    'CRIT', 'Cache DB — often no auth'),
        8080: ('HTTP-Alt', 'MED',  'Dev/proxy web port'),
        8443: ('HTTPS-Alt','MED',  'Alternate HTTPS — admin panels'),
        9200: ('Elasticsearch','CRIT','Search DB — often no auth'),
        27017:('MongoDB',  'CRIT', 'MongoDB — often no auth'),
    }

    open_ports = []
    rc = {'CRIT':C.RED,'HIGH':C.YELLOW,'MED':C.CYAN,'LOW':C.GREEN}

    def scan(port, pinfo):
        service, severity, desc = pinfo
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            if s.connect_ex((target_ip, port)) == 0:
                s.close()
                return port, service, severity, desc
            s.close()
        except: pass
        return None, None, None, None

    with ThreadPoolExecutor(max_workers=100) as ex:
        futures = {ex.submit(scan, p, i): p for p,i in ports.items()}
        for f in as_completed(futures):
            port, svc, sev, desc = f.result()
            if port:
                open_ports.append((port, svc, sev, desc))
                if sev == 'CRIT':
                    risk.add(f"Critical Port Exposed: {port}/{svc}", "CRITICAL",
                        f"Port {port} ({svc}) internet-accessible: {desc}",
                        f"Firewall port {port} — restrict to trusted IPs only", 30)
                elif sev == 'HIGH':
                    risk.add(f"High Risk Port: {port}/{svc}", "HIGH",
                        f"Port {port} ({svc}): {desc}",
                        f"Review necessity of port {port} being internet-accessible", 15)

    open_ports.sort(key=lambda x: x[0])
    if open_ports:
        success(f"Open ports: {len(open_ports)}")
        for port, svc, sev, desc in open_ports:
            col = rc.get(sev, C.WHITE)
            print(f"    {col}[{sev}]{C.RESET} Port {port:<6} {svc:<15} {C.DIM}{desc}{C.RESET}")
    results['ports'] = [(p,s,r,d) for p,s,r,d in open_ports]

# ─────────────────────────────────────────────────
# MODULE 07: BANNER GRABBING (NEW IN v2.0)
# ─────────────────────────────────────────────────
def run_banner_grab(target, results, risk):
    section("MODULE 07 — BANNER GRABBING & VERSION DETECTION")
    info("Grabbing service banners from all open ports...")
    banners = {}

    try:
        target_ip = socket.gethostbyname(target)
    except: return

    open_ports = [(p,s) for p,s,_,_ in results.get('ports',[])]

    banner_methods = {
        21:  ('FTP',   None, 'text'),
        22:  ('SSH',   None, 'text'),
        25:  ('SMTP',  b'EHLO godseye.local\r\n', 'text'),
        80:  ('HTTP',  f'HEAD / HTTP/1.0\r\nHost: {target}\r\n\r\n'.encode(), 'text'),
        110: ('POP3',  None, 'text'),
        143: ('IMAP',  None, 'text'),
        3306:('MySQL', None, 'bytes'),
        5432:('PostgreSQL', None, 'bytes'),
        6379:('Redis', b'INFO\r\n', 'text'),
    }

    def grab_banner(port, service):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target_ip, port))
            method = banner_methods.get(port)
            if method:
                _, send_data, encoding = method
                if send_data: s.send(send_data)
            time.sleep(0.5)
            s.settimeout(3)
            try:
                banner_raw = s.recv(2048)
                if encoding == 'text':
                    banner_str = banner_raw.decode('utf-8', errors='ignore').strip()
                else:
                    banner_str = repr(banner_raw[:100])
                s.close()
                return port, service, banner_str[:300]
            except: pass
            s.close()
        except: pass
        return port, service, None

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(grab_banner, p, s) for p,s in open_ports
                   if p in banner_methods]
        for f in as_completed(futures):
            port, service, banner_str = f.result()
            if banner_str and len(banner_str) > 3:
                banners[port] = banner_str
                success(f"Port {port} ({service}) banner:")
                # Show first 2 lines
                for line in banner_str.split('\n')[:3]:
                    if line.strip():
                        data(f"  {C.CYAN}{line.strip()}{C.RESET}")

                # Extract version from banner
                ver_patterns = [
                    r'OpenSSH[_\s]+([\d.p]+)',
                    r'SSH-([\d.]+)',
                    r'vsftpd\s+([\d.]+)',
                    r'ProFTPD\s+([\d.]+)',
                    r'Postfix\s+ESMTP',
                    r'Microsoft ESMTP',
                    r'Exim\s+([\d.]+)',
                    r'nginx/([\d.]+)',
                    r'Apache/([\d.]+)',
                    r'MySQL.*?([\d.]+)',
                ]
                for pat in ver_patterns:
                    m = re.search(pat, banner_str, re.IGNORECASE)
                    if m:
                        version_str = m.group(0).strip()
                        warn(f"Version detected: {version_str} → Search CVEs at nvd.nist.gov")
                        risk.add(f"Service Version Exposed: Port {port}", "LOW",
                            f"Banner reveals: {version_str}",
                            "Disable verbose banners in service config", 5)
                        break

                # FTP Anonymous check
                if port == 21:
                    info("Testing FTP anonymous login...")
                    try:
                        ftp_s = socket.socket()
                        ftp_s.settimeout(5)
                        ftp_s.connect((target_ip, 21))
                        ftp_s.recv(1024)
                        ftp_s.send(b'USER anonymous\r\n')
                        r1 = ftp_s.recv(1024).decode('utf-8', errors='ignore')
                        ftp_s.send(b'PASS godseye@test.com\r\n')
                        r2 = ftp_s.recv(1024).decode('utf-8', errors='ignore')
                        ftp_s.close()
                        if '230' in r2:
                            crit("FTP ANONYMOUS LOGIN SUCCESSFUL!")
                            risk.add("FTP Anonymous Access", "CRITICAL",
                                "FTP server allows anonymous login — files accessible without credentials",
                                "Disable anonymous FTP access immediately", 35)
                        else:
                            success("FTP anonymous login blocked ✓")
                    except: pass

                # SMTP Open Relay check
                if port == 25:
                    info("Testing SMTP open relay...")
                    try:
                        smtp_s = socket.socket()
                        smtp_s.settimeout(5)
                        smtp_s.connect((target_ip, 25))
                        smtp_s.recv(1024)
                        smtp_s.send(b'EHLO godseye.test\r\n')
                        smtp_s.recv(1024)
                        smtp_s.send(b'MAIL FROM: <test@external.com>\r\n')
                        r1 = smtp_s.recv(1024).decode('utf-8', errors='ignore')
                        smtp_s.send(b'RCPT TO: <test@external2.com>\r\n')
                        r2 = smtp_s.recv(1024).decode('utf-8', errors='ignore')
                        smtp_s.send(b'QUIT\r\n')
                        smtp_s.close()
                        if '250' in r2 and '550' not in r2 and '554' not in r2:
                            crit("SMTP OPEN RELAY DETECTED — server will relay external mail!")
                            risk.add("SMTP Open Relay", "CRITICAL",
                                "SMTP server relays mail for external domains — spam abuse possible",
                                "Configure SMTP to reject relay attempts for external domains", 40)
                        else:
                            success("SMTP relay blocked ✓")
                    except: pass

                # Database exposure alert
                if port in [3306, 5432, 1433, 27017, 6379, 9200]:
                    crit(f"DATABASE PORT {port} INTERNET ACCESSIBLE!")
                    data("  This should NEVER be exposed to the internet")
                    data("  Immediate firewall action required")

    results['banners'] = banners

# ─────────────────────────────────────────────────
# MODULE 08: CVE CORRELATION (NEW IN v2.0)
# ─────────────────────────────────────────────────
def run_cve_lookup(target, results, risk):
    section("MODULE 08 — CVE CORRELATION ENGINE")
    info("Correlating detected versions against known CVEs...")

    tech = results.get('technology', {})
    banners = results.get('banners', {})
    versions_to_check = []

    # Extract versions from tech fingerprint
    server = tech.get('server', '')
    if server:
        m = re.search(r'nginx/([\d.]+)', server)
        if m: versions_to_check.append(('nginx', m.group(1)))
        m = re.search(r'Apache/([\d.]+)', server, re.IGNORECASE)
        if m: versions_to_check.append(('apache httpd', m.group(1)))

    # Extract from banners
    for port, banner in banners.items():
        patterns = [
            (r'OpenSSH[_\s]+([\d.p]+)', 'openssh'),
            (r'vsftpd\s+([\d.]+)', 'vsftpd'),
            (r'ProFTPD\s+([\d.]+)', 'proftpd'),
            (r'Exim\s+([\d.]+)', 'exim'),
            (r'MySQL\s+([\d.]+)', 'mysql'),
            (r'PostgreSQL\s+([\d.]+)', 'postgresql'),
        ]
        for pat, product in patterns:
            m = re.search(pat, banner, re.IGNORECASE)
            if m: versions_to_check.append((product, m.group(1)))

    if not versions_to_check:
        warn("No specific versions detected for CVE lookup")
        data("Run: nmap -sV target.com for detailed version detection")
        return

    cve_results = {}
    for product, version in versions_to_check:
        info(f"Looking up CVEs for {product} {version}...")
        # NVD API v2
        keyword = f"{product} {version}"
        nvd_url = (f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                   f"?keywordSearch={parse.quote(keyword)}&resultsPerPage=5")
        resp, status, _ = http_get(nvd_url, timeout=12)
        if resp:
            try:
                nvd_data = json.loads(resp)
                vulns = nvd_data.get('vulnerabilities', [])
                if vulns:
                    success(f"CVEs found for {product} {version}:")
                    cve_results[f"{product}_{version}"] = []
                    for v in vulns[:5]:
                        cve_item = v.get('cve', {})
                        cve_id = cve_item.get('id', 'Unknown')
                        desc = cve_item.get('descriptions', [{}])[0].get('value', '')[:120]
                        metrics = cve_item.get('metrics', {})
                        score = 'N/A'
                        severity = 'UNKNOWN'
                        for key in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                            if key in metrics and metrics[key]:
                                score = metrics[key][0].get('cvssData',{}).get('baseScore', 'N/A')
                                severity = metrics[key][0].get('cvssData',{}).get('baseSeverity', 'N/A')
                                break
                        col = C.RED if severity in ['CRITICAL','HIGH'] else C.YELLOW
                        data(f"  {col}[{cve_id}]{C.RESET} CVSS: {score} ({severity})")
                        data(f"    {C.DIM}{desc[:100]}...{C.RESET}")
                        cve_results[f"{product}_{version}"].append({
                            'id': cve_id, 'score': score,
                            'severity': severity, 'desc': desc
                        })
                        if severity in ['CRITICAL', 'HIGH']:
                            risk.add(f"CVE: {cve_id} ({product} {version})",
                                severity,
                                f"CVSS {score}: {desc[:80]}",
                                f"Update {product} to latest stable version", 
                                25 if severity == 'CRITICAL' else 15)
                else:
                    data(f"  No recent CVEs found for {product} {version} in NVD")
            except Exception as e:
                warn(f"NVD parse error: {e}")
        else:
            warn(f"NVD unreachable — check manually: https://nvd.nist.gov/vuln/search?query={product}")
            data(f"  Also check: https://www.exploit-db.com/search?q={product}")

    results['cves'] = cve_results

# ─────────────────────────────────────────────────
# MODULE 09: SSL/TLS ANALYSIS
# ─────────────────────────────────────────────────
def run_ssl(target, results, risk):
    section("MODULE 09 — SSL/TLS CERTIFICATE INTELLIGENCE")
    info(f"Analyzing SSL/TLS for {target}...")
    ssl_data = {}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((target, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=target) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()
                success(f"TLS Version: {version}")
                if version in ['TLSv1','TLSv1.1','SSLv3']:
                    crit(f"Outdated TLS: {version} — VULNERABLE!")
                    risk.add(f"Outdated TLS: {version}", "CRITICAL",
                        f"Server supports deprecated {version}",
                        "Disable TLS 1.0 and 1.1, enforce TLS 1.2+", 25)
                success(f"Cipher: {cipher[0]}")
                if 'RC4' in str(cipher) or 'DES' in str(cipher) or 'NULL' in str(cipher):
                    crit(f"Weak cipher suite: {cipher[0]}")
                    risk.add("Weak Cipher Suite", "HIGH",
                        f"Weak cipher in use: {cipher[0]}",
                        "Configure modern cipher suites only", 20)
                subject = dict(x[0] for x in cert.get('subject',[]))
                issuer = dict(x[0] for x in cert.get('issuer',[]))
                cn = subject.get('commonName','N/A')
                org = subject.get('organizationName','N/A')
                success(f"Common Name: {cn}")
                success(f"Organization: {org}")
                data(f"  Issuer: {issuer.get('organizationName','Unknown')}")
                not_after = cert.get('notAfter','')
                if not_after:
                    try:
                        exp = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                        days = (exp - datetime.now()).days
                        if days < 30:
                            crit(f"Certificate expires in {days} days!")
                            risk.add("Certificate Expiry Imminent", "CRITICAL",
                                f"SSL cert expires in {days} days",
                                "Renew SSL certificate immediately", 30)
                        else:
                            data(f"  Expires: {not_after} ({days} days)")
                        ssl_data['expires_days'] = days
                    except: pass
                san = cert.get('subjectAltName',[])
                if san:
                    san_domains = [s[1] for s in san if s[0]=='DNS']
                    success(f"SAN domains ({len(san_domains)}) — additional subdomains:")
                    for d in san_domains[:15]: data(f"  {C.YELLOW}◆{C.RESET} {d}")
                    ssl_data['san_domains'] = san_domains
                ssl_data.update({'version':version,'cipher':cipher[0],
                                 'cn':cn,'org':org})
    except ConnectionRefusedError: warn("Port 443 closed")
    except Exception as e: warn(f"SSL error: {e}")
    results['ssl'] = ssl_data

# ─────────────────────────────────────────────────
# MODULE 10: WEB INTELLIGENCE
# ─────────────────────────────────────────────────
def run_web_recon(target, results, risk):
    section("MODULE 10 — WEB INTELLIGENCE")
    info(f"Web reconnaissance on {target}...")
    web_data = {}

    # robots.txt
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
                    if p and p != '/':
                        data(f"  {C.RED}⚑{C.RESET} {p}")
            break

    # Sensitive paths
    info("Probing sensitive paths...")
    sensitive = [
        ('/.env',             'CRITICAL', 40, 'Environment file — all credentials'),
        ('/.git/config',      'CRITICAL', 35, 'Git repository exposed'),
        ('/.git/HEAD',        'CRITICAL', 35, 'Git repository exposed'),
        ('/backup/',          'CRITICAL', 35, 'Backup directory'),
        ('/backup.zip',       'CRITICAL', 35, 'Backup archive'),
        ('/backup.sql',       'CRITICAL', 35, 'Database backup'),
        ('/db.sql',           'CRITICAL', 35, 'Database dump'),
        ('/database.sql',     'CRITICAL', 35, 'Database dump'),
        ('/.env.backup',      'CRITICAL', 35, 'Env backup — credentials'),
        ('/.env.old',         'CRITICAL', 35, 'Old env file — credentials'),
        ('/config.php.bak',   'CRITICAL', 30, 'Config backup'),
        ('/wp-config.php.bak','CRITICAL', 30, 'WordPress config backup'),
        ('/admin/',           'HIGH',     20, 'Admin panel'),
        ('/administrator/',   'HIGH',     20, 'Admin panel'),
        ('/wp-admin/',        'HIGH',     20, 'WordPress admin'),
        ('/cpanel',           'HIGH',     25, 'cPanel control panel'),
        ('/whm',              'HIGH',     25, 'WHM server management'),
        ('/phpmyadmin/',      'HIGH',     25, 'phpMyAdmin — database GUI'),
        ('/phpinfo.php',      'HIGH',     20, 'PHP configuration exposed'),
        ('/server-status',    'HIGH',     20, 'Apache server status'),
        ('/server-info',      'HIGH',     15, 'Apache server info'),
        ('/.htpasswd',        'HIGH',     25, 'Password file'),
        ('/web.config',       'HIGH',     20, 'IIS configuration'),
        ('/elmah.axd',        'HIGH',     20, 'ASP.NET error log'),
        ('/trace.axd',        'HIGH',     20, 'ASP.NET trace'),
        ('/api/v1/',          'MED',      10, 'API endpoint'),
        ('/api/swagger',      'MED',      10, 'API documentation'),
        ('/swagger.json',     'MED',      10, 'API schema'),
        ('/graphql',          'MED',      10, 'GraphQL endpoint'),
        ('/.DS_Store',        'MED',      10, 'macOS directory listing'),
        ('/crossdomain.xml',  'LOW',       5, 'Flash crossdomain policy'),
    ]

    exposed = []
    def chk(path_info):
        path, sev, sc, desc = path_info
        resp, status, _ = http_get(f"https://{target}{path}", timeout=5)
        if not resp:
            resp, status, _ = http_get(f"http://{target}{path}", timeout=5)
        if resp and status == 200 and len(resp) > 20:
            if path not in ['/robots.txt','/sitemap.xml']:
                return path, sev, sc, desc, len(resp)
        return None,None,None,None,None

    with ThreadPoolExecutor(max_workers=25) as ex:
        futures = {ex.submit(chk, p): p for p in sensitive}
        for f in as_completed(futures):
            path, sev, sc, desc, size = f.result()
            if path:
                exposed.append((path, sev, sc, desc, size))
                risk.add(f"Sensitive Path Exposed: {path}", sev,
                    f"{path} is publicly accessible ({size} bytes) — {desc}",
                    f"Remove or restrict access to {path}", sc)

    if exposed:
        crit(f"{len(exposed)} SENSITIVE PATHS EXPOSED:")
        for path, sev, _, desc, size in exposed:
            col = C.RED if sev == 'CRITICAL' else C.YELLOW
            data(f"  {col}[{sev}]{C.RESET} {path} ({size}b) — {desc}")
    else:
        success("No obvious sensitive paths exposed")

    # Wayback Machine
    info("Querying Wayback Machine...")
    wb_resp, _, _ = http_get(f"https://archive.org/wayback/available?url={target}", timeout=10)
    if wb_resp:
        try:
            wb = json.loads(wb_resp)
            snap = wb.get('archived_snapshots',{}).get('closest',{})
            if snap:
                ts = snap.get('timestamp','')
                success(f"Wayback snapshot: {ts}")
                data(f"  {snap.get('url','')}")
                data(f"  Full history: https://web.archive.org/web/*/{target}")
                web_data['wayback'] = snap.get('url','')
        except: pass

    # Dorks
    dorks = [
        f'site:{target}',
        f'site:{target} filetype:pdf',
        f'site:{target} filetype:xls OR filetype:xlsx',
        f'site:{target} filetype:sql',
        f'site:{target} filetype:env',
        f'site:{target} filetype:log',
        f'site:{target} filetype:bak',
        f'site:{target} filetype:config',
        f'site:{target} intitle:"index of"',
        f'site:{target} inurl:admin',
        f'site:{target} inurl:backup',
        f'site:{target} inurl:api',
        f'site:{target} "confidential"',
        f'site:{target} "internal use only"',
        f'site:{target} "password"',
        f'site:{target} "BEGIN PRIVATE KEY"',
        f'"@{target}" site:linkedin.com',
        f'site:github.com "{target}"',
        f'site:pastebin.com "{target}"',
        f'site:trello.com "{target}"',
    ]
    success("Google Dork queries generated:")
    web_data['dorks'] = dorks
    for d in dorks: data(f"  {C.CYAN}◆{C.RESET} {d}")
    web_data['exposed_paths'] = exposed
    results['web'] = web_data

# ─────────────────────────────────────────────────
# MODULE 11: IP & NETWORK
# ─────────────────────────────────────────────────
def run_ip_intel(target, results, risk):
    section("MODULE 11 — IP & NETWORK INTELLIGENCE")
    info(f"IP intelligence for {target}...")
    ip_data = {}
    try:
        target_ip = socket.gethostbyname(target)
        success(f"Primary IP: {target_ip}")
        ip_data['ip'] = target_ip
        resp, _, _ = http_get(f"https://ipinfo.io/{target_ip}/json", timeout=8)
        if resp:
            geo = json.loads(resp)
            city = geo.get('city','?'); region = geo.get('region','?')
            country = geo.get('country','?'); org = geo.get('org','?')
            loc = geo.get('loc','?')
            success(f"Geolocation: {city}, {region}, {country}")
            data(f"  Provider: {org}")
            data(f"  GPS: {loc}")
            ip_data['geo'] = geo
            hosting_map = {
                'Amazon':      ('AWS', 'Check for misconfigured S3 buckets, exposed APIs'),
                'Google':      ('GCP', 'Check for exposed GCS buckets'),
                'Microsoft':   ('Azure', 'Check Azure Blob storage misconfigurations'),
                'Cloudflare':  ('Cloudflare CDN', 'Real IP hidden — check historical DNS'),
                'DigitalOcean':('DigitalOcean', 'Check for default firewall rules'),
                'Oracle':      ('Oracle Cloud', 'Check for default credentials'),
                'Bluehost':    ('Shared Hosting', 'Shared hosting — virtual host attacks possible'),
            }
            for kw, (name, note) in hosting_map.items():
                if kw.lower() in org.lower():
                    warn(f"Hosting: {name} — {note}")
                    ip_data['hosting'] = name
                    if 'Shared' in name or 'Bluehost' in name:
                        risk.add("Shared Hosting Environment", "MEDIUM",
                            "Target shares server with hundreds of other domains",
                            "One compromised neighbor site can affect target", 12)

        # Reverse IP — shared hosting analysis
        info("Reverse IP lookup — shared hosting analysis...")
        rev_resp, _, _ = http_get(
            f"https://api.hackertarget.com/reverseiplookup/?q={target_ip}", timeout=10)
        if rev_resp and 'error' not in rev_resp.lower():
            others = [d.strip() for d in rev_resp.strip().split('\n') if d.strip()]
            if len(others) > 1:
                success(f"Reverse IP: {len(others)} domains on same server:")
                for d in others[:8]: data(f"  {C.CYAN}◆{C.RESET} {d}")
                if len(others) > 8: data(f"  ... and {len(others)-8} more")
                ip_data['reverse_ip'] = others
                if len(others) > 50:
                    warn("Mass shared hosting — cross-site attack surface is large")

        # ASN lookup
        info("ASN intelligence...")
        asn_resp, _, _ = http_get(
            f"https://api.hackertarget.com/aslookup/?q={target_ip}", timeout=8)
        if asn_resp and 'error' not in asn_resp.lower():
            success(f"ASN Info: {asn_resp.strip()}")
            ip_data['asn'] = asn_resp.strip()

    except Exception as e:
        err(f"IP intel error: {e}")
    results['ip_intel'] = ip_data

# ─────────────────────────────────────────────────
# MODULE 12: BREACH INTELLIGENCE
# ─────────────────────────────────────────────────
def run_breach(target, results, risk):
    section("MODULE 12 — BREACH INTELLIGENCE")
    info(f"Checking breach databases for {target}...")
    breach_data = {}
    resp, status, _ = http_get(
        f"https://haveibeenpwned.com/api/v3/breacheddomain/{target}",
        timeout=10, headers={'hibp-api-key': 'free'})
    if resp and status == 200:
        try:
            breaches = json.loads(resp)
            if breaches:
                crit(f"{len(breaches)} data breaches affect {target}!")
                for b in breaches[:10]: data(f"  {C.RED}☠{C.RESET} {b}")
                risk.add(f"Data Breaches Found ({len(breaches)})", "CRITICAL",
                    f"{len(breaches)} known breaches affect this domain",
                    "Force password reset, enable MFA, audit access logs", 35)
                breach_data['breaches'] = breaches
        except: pass
    else:
        info("HIBP requires API key for domain search")
        data("  Manual check: https://haveibeenpwned.com/DomainSearch")
    data(f"  dehashed.com — search @{target}")
    data(f"  intelx.io — dark web intelligence")
    data(f"  breachdirectory.org — free credential lookup")
    results['breaches'] = breach_data

# ─────────────────────────────────────────────────
# MODULE 13: SOCIAL MEDIA
# ─────────────────────────────────────────────────
def run_social(target, results, risk):
    section("MODULE 13 — SOCIAL MEDIA INTELLIGENCE")
    company = target.split('.')[0]
    info(f"Social media recon for: {company}")
    social_data = {}
    platforms = {
        'LinkedIn':  f"https://www.linkedin.com/company/{company}",
        'Twitter/X': f"https://twitter.com/{company}",
        'Facebook':  f"https://www.facebook.com/{company}",
        'Instagram': f"https://www.instagram.com/{company}",
        'GitHub':    f"https://github.com/{company}",
        'YouTube':   f"https://www.youtube.com/@{company}",
    }
    for platform, url in platforms.items():
        resp, status, _ = http_get(url, timeout=6)
        if resp and status == 200 and len(resp) > 500:
            if any(t in resp.lower() for t in ['followers','following','posts','profile','about','repository']):
                success(f"{platform}: Profile found → {url}")
                social_data[platform] = url

    # GitHub org scan
    info("GitHub deep reconnaissance...")
    gh_resp, status, _ = http_get(
        f"https://api.github.com/orgs/{company}/repos?per_page=15&sort=updated", timeout=10)
    if gh_resp and status == 200:
        try:
            repos = json.loads(gh_resp)
            if repos and isinstance(repos, list):
                success(f"GitHub org found: {len(repos)} public repos")
                for r in repos[:10]:
                    name = r.get('name','')
                    lang = r.get('language','?')
                    updated = r.get('updated_at','')[:10]
                    data(f"  {C.YELLOW}◆{C.RESET} {name} [{lang}] — {updated}")
                warn("Check repos for leaked secrets:")
                data(f"  trufflehog github --org {company}")
                data(f"  gitleaks detect --source /path/to/clone")
                social_data['github_repos'] = [r.get('name') for r in repos]
        except: pass
    results['social'] = social_data

# ─────────────────────────────────────────────────
# ATTACK CHAIN GENERATOR (NEW IN v2.0)
# ─────────────────────────────────────────────────
def generate_attack_chain(target, results, risk):
    section("ATTACK CHAIN ANALYSIS")
    info("Generating most likely attack paths from findings...")

    findings = risk.findings
    chains = []

    # Chain 1: Email Spoofing → Phishing
    spf_risk = any('SPF' in f['title'] for f in findings)
    emails = results.get('emails', [])
    if spf_risk and emails:
        chains.append({
            'name': 'Business Email Compromise (BEC)',
            'severity': 'CRITICAL',
            'steps': [
                f'Step 1: Harvest emails — {len(emails)} emails found publicly',
                'Step 2: Exploit SPF misconfiguration — spoofing is possible',
                'Step 3: Craft spear phishing email posing as executive',
                'Step 4: Target finance team for wire transfer',
                'Step 5: Transfer funds before detection',
            ],
            'likelihood': 'HIGH',
            'impact': 'Financial loss, credential theft'
        })

    # Chain 2: Database Direct Access
    db_ports = [p for p,s,r,_ in results.get('ports',[]) if p in [3306,5432,1433,27017]]
    if db_ports:
        chains.append({
            'name': 'Direct Database Compromise',
            'severity': 'CRITICAL',
            'steps': [
                f'Step 1: Database port(s) {db_ports} found internet-accessible',
                'Step 2: Run credential bruteforce with common/default passwords',
                'Step 3: Gain database access without touching web application',
                'Step 4: Extract all customer data, credentials, financial records',
                'Step 5: Use credentials for lateral movement',
            ],
            'likelihood': 'HIGH',
            'impact': 'Complete data breach, regulatory consequences'
        })

    # Chain 3: Subdomain Takeover
    takeover = [f for f in findings if 'Takeover' in f['title']]
    if takeover:
        chains.append({
            'name': 'Subdomain Takeover → Credential Phishing',
            'severity': 'CRITICAL',
            'steps': [
                f'Step 1: {takeover[0]["title"]} identified',
                'Step 2: Register the unclaimed resource (free in most cases)',
                'Step 3: Host fake login page on trusted subdomain',
                'Step 4: Send phishing link — users trust the domain',
                'Step 5: Harvest credentials from victims',
            ],
            'likelihood': 'HIGH',
            'impact': 'Mass credential theft from trusted domain'
        })

    # Chain 4: Shared Hosting Attack
    if results.get('ip_intel',{}).get('reverse_ip') and \
       len(results.get('ip_intel',{}).get('reverse_ip',[])) > 10:
        chains.append({
            'name': 'Shared Hosting Cross-Site Attack',
            'severity': 'HIGH',
            'steps': [
                f'Step 1: {len(results["ip_intel"]["reverse_ip"])} domains share same server IP',
                'Step 2: Identify weakest neighboring domain',
                'Step 3: Compromise weak neighbor site (SQLi, file upload, etc.)',
                'Step 4: Use server access to read target site files',
                'Step 5: Extract target config files, database credentials',
            ],
            'likelihood': 'MEDIUM',
            'impact': 'Complete site compromise via neighbor'
        })

    # Chain 5: FTP Anonymous
    ftp_anon = any('FTP Anonymous' in f['title'] for f in findings)
    if ftp_anon:
        chains.append({
            'name': 'Anonymous FTP Data Exfiltration',
            'severity': 'CRITICAL',
            'steps': [
                'Step 1: Anonymous FTP login confirmed — no credentials needed',
                'Step 2: List all accessible directories and files',
                'Step 3: Download sensitive files (backups, configs, data)',
                'Step 4: Analyze files for credentials and internal paths',
                'Step 5: Use found credentials for deeper access',
            ],
            'likelihood': 'CRITICAL',
            'impact': 'Immediate data access without any authentication'
        })

    if chains:
        for i, chain in enumerate(chains, 1):
            col = C.RED if chain['severity'] == 'CRITICAL' else C.YELLOW
            print(f"\n  {col}{C.BOLD}Attack Path {i}: {chain['name']}{C.RESET}")
            print(f"  {col}Severity: {chain['severity']} | Likelihood: {chain['likelihood']}{C.RESET}")
            print(f"  {C.DIM}Impact: {chain['impact']}{C.RESET}")
            for step in chain['steps']:
                data(f"  {C.CYAN}→{C.RESET} {step}")
    else:
        success("No high-confidence attack chains identified from current data")
        data("Run nmap -sV for deeper service detection to improve analysis")

    results['attack_chains'] = chains

# ─────────────────────────────────────────────────
# HTML REPORT GENERATOR v2.0
# ─────────────────────────────────────────────────
def generate_html(target, results, risk, end_time, duration):
    rating, rating_color_name = risk.get_rating()
    rating_css = {
        'CRITICAL RISK': '#e63946', 'HIGH RISK': '#ff8800',
        'MEDIUM RISK': '#ffcc00', 'LOW RISK': '#00aa00',
        'MINIMAL RISK': '#00cc00'
    }.get(rating, '#888')

    sev_count = {'CRITICAL':0,'HIGH':0,'MEDIUM':0,'LOW':0,'INFO':0}
    for f in risk.findings:
        sev_count[f['severity']] = sev_count.get(f['severity'],0) + 1

    chains = results.get('attack_chains',[])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GodsEye v2.0 — {target}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Courier New',monospace;background:#090909;color:#e0e0e0;padding:20px;line-height:1.6}}
.hdr{{background:linear-gradient(135deg,#1a0000,#000);border:1px solid #e63946;border-radius:8px;padding:30px;margin-bottom:20px;text-align:center}}
.logo{{color:#e63946;font-size:2em;font-weight:bold;letter-spacing:3px}}
.subtitle{{color:#666;margin-top:5px;font-size:.9em}}
.risk-score{{font-size:3em;font-weight:bold;color:{rating_css};margin:10px 0}}
.risk-label{{color:#888;font-size:.8em;letter-spacing:2px}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}}
.card{{background:#111;border:1px solid #222;border-radius:6px;padding:16px}}
.card-title{{font-size:.7em;color:#666;letter-spacing:1px;margin-bottom:8px;text-transform:uppercase}}
.card-num{{font-size:2em;font-weight:bold}}
.card-num.red{{color:#e63946}}.card-num.amber{{color:#ffaa00}}
.card-num.green{{color:#00ff88}}.card-num.cyan{{color:#00ccff}}
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
.chain{{background:#0a0000;border:1px solid #330000;border-radius:6px;padding:14px;margin:8px 0}}
.chain h3{{color:#e63946;font-size:.85em;margin-bottom:8px}}
.chain-step{{color:#ccc;font-size:.8em;padding:2px 0}}
.badge{{display:inline-block;padding:2px 8px;border-radius:3px;font-size:.7em;font-weight:bold}}
.badge.CRITICAL{{background:#e63946;color:#fff}}
.badge.HIGH{{background:#ff8800;color:#fff}}
.badge.MEDIUM{{background:#ffcc00;color:#000}}
.badge.LOW{{background:#00aa00;color:#fff}}
.dork{{background:#0d1a0d;border:1px solid #1a3a1a;padding:3px 8px;margin:2px 0;border-radius:3px;font-size:.8em;color:#00cc66}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:.7em;margin:1px}}
.tag.red{{background:#330000;color:#e63946}}
.tag.amber{{background:#331a00;color:#ffaa00}}
.tag.green{{background:#003300;color:#00ff88}}
.tag.cyan{{background:#003344;color:#00ccff}}
table{{width:100%;border-collapse:collapse;font-size:.85em}}
td,th{{padding:6px 10px;border-bottom:1px solid #1a1a1a;text-align:left}}
th{{color:#666;font-size:.75em;letter-spacing:1px}}
.footer{{text-align:center;color:#333;margin-top:20px;font-size:.75em}}
</style>
</head>
<body>

<div class="hdr">
  <div class="logo">⚡ GODSEYE v2.0 INTELLIGENCE REPORT</div>
  <div class="subtitle">Target: {target} | {end_time.strftime('%Y-%m-%d %H:%M:%S')} | {duration}s scan</div>
  <div class="risk-score">{risk.score}/100</div>
  <div class="risk-label">{rating}</div>
  <div style="margin-top:10px;font-size:.75em;color:#e63946">⚠ FOR AUTHORIZED PENETRATION TESTING ONLY ⚠</div>
</div>

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
  <div class="card"><div class="card-title">CVEs Found</div><div class="card-num red">{sum(len(v) for v in results.get('cves',{}).values())}</div></div>
</div>
"""

    # All Findings sorted by severity
    if risk.findings:
        html += '<div class="section"><h2>ALL FINDINGS — SORTED BY SEVERITY</h2>'
        order = ['CRITICAL','HIGH','MEDIUM','LOW','INFO']
        sorted_findings = sorted(risk.findings, key=lambda x: order.index(x['severity']))
        for f in sorted_findings:
            html += f"""<div class="finding {f['severity']}">
  <div class="title"><span class="badge {f['severity']}">{f['severity']}</span> {f['title']}</div>
  <div class="desc">{f['description']}</div>
  <div class="rec">Recommendation: {f['recommendation']}</div>
</div>"""
        html += '</div>'

    # Attack Chains
    if chains:
        html += '<div class="section"><h2>ATTACK CHAIN ANALYSIS</h2>'
        for i, chain in enumerate(chains,1):
            html += f"""<div class="chain">
  <h3>Path {i}: {chain['name']} <span class="badge {chain['severity']}">{chain['severity']}</span></h3>
  <div style="color:#666;font-size:.8em;margin-bottom:8px">Likelihood: {chain['likelihood']} | Impact: {chain['impact']}</div>"""
            for step in chain['steps']:
                html += f'<div class="chain-step">→ {step}</div>'
            html += '</div>'
        html += '</div>'

    # DNS
    dns = results.get('dns',{})
    if dns:
        html += '<div class="section"><h2>DNS INTELLIGENCE</h2><table>'
        html += '<tr><th>Record Type</th><th>Value</th><th>Risk Note</th></tr>'
        risk_notes = {
            'MX':'Mail server — email attack target',
            'TXT':'Contains SPF/DKIM/DMARC config',
            'NS':'Nameservers — zone transfer target',
            'A':'Primary IP — main attack surface',
        }
        for rtype in ['A','AAAA','MX','NS','TXT','SOA']:
            for rec in dns.get(rtype,[])[:3]:
                note = risk_notes.get(rtype,'')
                html += f'<tr><td><span class="tag cyan">{rtype}</span></td><td style="font-size:.8em">{rec[:80]}</td><td style="color:#666;font-size:.8em">{note}</td></tr>'
        html += '</table>'
        if dns.get('spf_ok'):
            html += '<div style="color:#00ff88;font-size:.8em;margin-top:8px">✓ SPF HardFail configured</div>'
        html += '</div>'

    # Subdomains
    live_subs = results.get('subdomains_live',[])
    if live_subs:
        crit_subs = ['cpanel','whm','phpmyadmin','admin','backup','dev','staging','vpn','db']
        html += f'<div class="section"><h2>LIVE SUBDOMAINS ({len(live_subs)})</h2><table>'
        html += '<tr><th>Subdomain</th><th>IP</th><th>Risk</th></tr>'
        for fqdn, ip in sorted(live_subs):
            sub = fqdn.split('.')[0]
            is_crit = sub in crit_subs
            badge = '<span class="badge CRITICAL">CRITICAL</span>' if is_crit else '<span class="badge LOW">INFO</span>'
            html += f'<tr><td style="color:{"#e63946" if is_crit else "#ccc"}">{fqdn}</td><td style="color:#666">{ip}</td><td>{badge}</td></tr>'
        html += '</table></div>'

    # Ports
    ports = results.get('ports',[])
    if ports:
        html += f'<div class="section"><h2>OPEN PORTS ({len(ports)})</h2><table>'
        html += '<tr><th>Port</th><th>Service</th><th>Risk</th><th>Note</th></tr>'
        for port, svc, sev, desc in ports:
            html += f'<tr><td><strong>{port}</strong></td><td>{svc}</td><td><span class="badge {sev}">{sev}</span></td><td style="color:#666;font-size:.8em">{desc}</td></tr>'
        html += '</table></div>'

    # CVEs
    cves = results.get('cves',{})
    if cves:
        html += '<div class="section"><h2>CVE CORRELATIONS</h2>'
        for product_ver, cve_list in cves.items():
            html += f'<div style="color:#ffaa00;margin-bottom:6px">{product_ver.replace("_"," ")}</div>'
            for cve in cve_list:
                sev = cve.get('severity','UNKNOWN')
                html += f'<div class="finding {sev if sev in ["CRITICAL","HIGH","MEDIUM","LOW"] else "LOW"}">'
                html += f'<div class="title">{cve["id"]} — CVSS {cve["score"]} ({sev})</div>'
                html += f'<div class="desc">{cve["desc"][:120]}</div></div>'
        html += '</div>'

    # Emails
    emails = results.get('emails',[])
    if emails:
        html += f'<div class="section"><h2>HARVESTED EMAILS ({len(emails)})</h2>'
        for em in emails[:20]:
            html += f'<div style="color:#ff8800;font-size:.85em;padding:3px 0">✉ {em}</div>'
        html += '</div>'

    # Google Dorks
    dorks = results.get('web',{}).get('dorks',[])
    if dorks:
        html += '<div class="section"><h2>GOOGLE DORK QUERIES</h2>'
        for d in dorks: html += f'<div class="dork">{d}</div>'
        html += '</div>'

    html += f"""
<div class="footer">
  <p>GodsEye v2.0 — Advanced Reconnaissance & Vulnerability Intelligence</p>
  <p>For authorized penetration testing and security research only.</p>
  <p>Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')} | Scan duration: {duration}s</p>
</div>
</body></html>"""
    return html

# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='GodsEye v2.0 — Advanced Reconnaissance & Vulnerability Intelligence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 godseye_v2.py certifiedhacker.com
  python3 godseye_v2.py target.com --skip-ports
  python3 godseye_v2.py target.com --modules whois,dns,subdomains,ports,banners,cve
  python3 godseye_v2.py target.com --stealth

Modules: whois dns subdomains emails tech ports banners cve ssl web ip breach social

Legal: Authorized use only. Unauthorized scanning is illegal.
        """
    )
    parser.add_argument('target', help='Target domain (e.g. certifiedhacker.com)')
    parser.add_argument('--skip-ports', action='store_true', help='Skip port scan')
    parser.add_argument('--modules', type=str, help='Specific modules only')
    parser.add_argument('--stealth', action='store_true', help='Slower scan, less noise')
    args = parser.parse_args()

    target = args.target.lower().replace('https://','').replace('http://','').replace('www.','').split('/')[0]

    banner()
    print(f"  {C.BOLD}Target:{C.RESET}    {C.RED}{target}{C.RESET}")
    print(f"  {C.BOLD}Version:{C.RESET}   GodsEye v2.0")
    print(f"  {C.BOLD}Started:{C.RESET}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {C.YELLOW}⚠ Authorized use only. You are responsible for your actions.{C.RESET}")
    print(f"\n  {C.YELLOW}Confirm authorization to scan {target}? (yes/no):{C.RESET} ", end='')
    try:
        if input().strip().lower() not in ['yes','y']:
            print(f"\n  {C.RED}Cancelled. Always get authorization first.{C.RESET}\n")
            sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n  {C.RED}Cancelled.{C.RESET}\n"); sys.exit(0)

    results = {}
    risk = RiskEngine()
    start = datetime.now()

    all_modules = ['whois','dns','subdomains','emails','tech','ports','banners','cve','ssl','web','ip','breach','social']
    if args.modules:
        run_list = [m.strip() for m in args.modules.split(',')]
    else:
        run_list = all_modules
    if args.skip_ports:
        for m in ['ports','banners']: 
            if m in run_list: run_list.remove(m)

    module_map = {
        'whois':     lambda: run_whois(target, results, risk),
        'dns':       lambda: run_dns(target, results, risk),
        'subdomains':lambda: run_subdomains(target, results, risk),
        'emails':    lambda: run_email_harvest(target, results, risk),
        'tech':      lambda: run_tech_fingerprint(target, results, risk),
        'ports':     lambda: run_ports(target, results, risk),
        'banners':   lambda: run_banner_grab(target, results, risk),
        'cve':       lambda: run_cve_lookup(target, results, risk),
        'ssl':       lambda: run_ssl(target, results, risk),
        'web':       lambda: run_web_recon(target, results, risk),
        'ip':        lambda: run_ip_intel(target, results, risk),
        'breach':    lambda: run_breach(target, results, risk),
        'social':    lambda: run_social(target, results, risk),
    }

    for mod in run_list:
        if mod in module_map:
            try: module_map[mod]()
            except KeyboardInterrupt: warn(f"Module {mod} interrupted")
            except Exception as e: err(f"Module {mod} error: {e}")
            if args.stealth: time.sleep(2)

    # Attack chain analysis
    generate_attack_chain(target, results, risk)

    # Generate reports
    section("GENERATING REPORTS")
    end_time = datetime.now()
    duration = (end_time - start).seconds
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = f"godseye_v2_{target.replace('.','_')}_{ts}.json"
    html_file = f"godseye_v2_{target.replace('.','_')}_{ts}.html"

    with open(json_file,'w') as f:
        json.dump({'target':target,'timestamp':str(end_time),
                   'duration':duration,'risk_score':risk.score,
                   'results':results,'findings':risk.findings}, f, indent=2, default=str)

    with open(html_file,'w') as f:
        f.write(generate_html(target, results, risk, end_time, duration))

    success(f"JSON Report: {json_file}")
    success(f"HTML Report: {html_file}")
    info(f"Open: firefox {html_file}")

    # Final summary
    section("EXECUTIVE SUMMARY")
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
    print(f"    CVEs Found:    {sum(len(v) for v in results.get('cves',{}).values())}")

    if risk.findings:
        print(f"\n  {C.RED}{C.BOLD}TOP CRITICAL FINDINGS:{C.RESET}")
        crits = [f for f in risk.findings if f['severity']=='CRITICAL'][:5]
        for f in crits: print(f"    {C.RED}✗{C.RESET} {f['title']}")

    print(f"\n  {C.GREEN}{C.BOLD}Scan complete. Reports saved.{C.RESET}\n")

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}Interrupted.{C.RESET}\n"); sys.exit(0)
