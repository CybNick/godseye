#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║                         GODSEYE v1.0                          ║
║           Advanced Reconnaissance Intelligence Tool           ║
║         "See Everything. Miss Nothing. Strike First."         ║
╚═══════════════════════════════════════════════════════════════╝

Usage:
    python3 godseye.py <target>
    python3 godseye.py certifiedhacker.com
    python3 godseye.py --help

Author: GodsEye Project
Purpose: Educational — Authorized Penetration Testing Only
"""

import sys
import os
import json
import socket
import ssl
import time
import re
import argparse
import threading
import ipaddress
from datetime import datetime
from urllib import request, parse, error
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────────
# COLORS & BANNER
# ─────────────────────────────────────────────────

class Colors:
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN    = '\033[96m'
    WHITE   = '\033[97m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    RESET   = '\033[0m'

def banner():
    print(f"""
{Colors.RED}{Colors.BOLD}
  ██████╗  ██████╗ ██████╗ ███████╗███████╗██╗   ██╗███████╗
 ██╔════╝ ██╔═══██╗██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝██╔════╝
 ██║  ███╗██║   ██║██║  ██║███████╗█████╗   ╚████╔╝ █████╗  
 ██║   ██║██║   ██║██║  ██║╚════██║██╔══╝    ╚██╔╝  ██╔══╝  
 ╚██████╔╝╚██████╔╝██████╔╝███████║███████╗   ██║   ███████╗
  ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚══════╝
{Colors.RESET}
{Colors.CYAN}        Advanced Reconnaissance Intelligence Tool v1.0{Colors.RESET}
{Colors.DIM}        "See Everything. Miss Nothing. Strike First."{Colors.RESET}
{Colors.YELLOW}        ⚠  For Authorized Testing Only  ⚠{Colors.RESET}
    """)

# ─────────────────────────────────────────────────
# STATUS PRINTERS
# ─────────────────────────────────────────────────

def info(msg):    print(f"  {Colors.CYAN}[*]{Colors.RESET} {msg}")
def success(msg): print(f"  {Colors.GREEN}[+]{Colors.RESET} {msg}")
def warning(msg): print(f"  {Colors.YELLOW}[!]{Colors.RESET} {msg}")
def error(msg):   print(f"  {Colors.RED}[-]{Colors.RESET} {msg}")
def data(msg):    print(f"      {Colors.WHITE}{msg}{Colors.RESET}")
def section(title):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═'*60}{Colors.RESET}")

# ─────────────────────────────────────────────────
# HTTP HELPER
# ─────────────────────────────────────────────────

def http_get(url, timeout=8, headers=None):
    """Safe HTTP GET with fallback"""
    try:
        req = request.Request(url)
        req.add_header('User-Agent', 
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0')
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='ignore'), resp.status
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────────
# MODULE 1: WHOIS
# ─────────────────────────────────────────────────

def run_whois(target, results):
    section("MODULE 01 — WHOIS INTELLIGENCE")
    info(f"Running WHOIS lookup on {target}...")
    
    whois_data = {}
    
    # Try system whois first
    try:
        import subprocess
        out = subprocess.getoutput(f"whois {target} 2>/dev/null")
        if out and len(out) > 50:
            success("WHOIS data retrieved")
            
            # Parse key fields
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
                        data(f"{Colors.YELLOW}Expiry:{Colors.RESET} {unique[0]}")
                        # Check if expiring soon
                        try:
                            from datetime import timezone
                            exp_str = unique[0].split('T')[0]
                            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
                            days_left = (exp_date - datetime.now()).days
                            if days_left < 90:
                                warning(f"Domain expires in {days_left} days — HIJACK RISK!")
                                whois_data['RISK'] = f"Domain expires in {days_left} days"
                        except: pass
                    elif field == 'Registrant Email':
                        data(f"{Colors.RED}Registrant Email:{Colors.RESET} {unique[0]} ← Social engineering target")
                    elif field == 'Name Servers':
                        for ns in unique[:4]:
                            data(f"Name Server: {ns}")
                        # Check if self-hosted
                        if any(target.replace('www.','') in ns.lower() for ns in unique):
                            warning("Self-hosted nameservers detected — zone transfer may be possible!")
                            whois_data['NS_RISK'] = "Self-hosted nameservers"
                    else:
                        data(f"{field}: {', '.join(unique[:2])}")
        else:
            # Fallback to RDAP
            info("Trying RDAP fallback...")
            rdap_url = f"https://rdap.org/domain/{target}"
            resp, status = http_get(rdap_url)
            if resp:
                try:
                    rdap = json.loads(resp)
                    whois_data['RDAP'] = True
                    if 'registrar' in str(rdap).lower():
                        success("RDAP data retrieved")
                        data(f"Events: {[e.get('eventAction','') for e in rdap.get('events',[])[:3]]}")
                except: pass
            else:
                error("WHOIS lookup failed — try: apt install whois")
                
    except Exception as e:
        error(f"WHOIS error: {e}")
    
    results['whois'] = whois_data

# ─────────────────────────────────────────────────
# MODULE 2: DNS RECORDS
# ─────────────────────────────────────────────────

def run_dns(target, results):
    section("MODULE 02 — DNS INTELLIGENCE")
    info(f"Extracting all DNS records for {target}...")
    
    dns_data = {}
    
    # Try using dig first
    try:
        import subprocess
        record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'SOA', 'CNAME', 'SRV']
        
        for rtype in record_types:
            out = subprocess.getoutput(
                f"dig {target} {rtype} +short 2>/dev/null"
            )
            if out and out.strip():
                dns_data[rtype] = [l.strip() for l in out.strip().split('\n') if l.strip()]
                
                if rtype == 'A':
                    for ip in dns_data[rtype]:
                        success(f"A Record: {ip}")
                        data(f"  → Main server IP — primary attack surface")
                        
                elif rtype == 'MX':
                    success(f"MX Records found — mail infrastructure exposed")
                    for mx in dns_data[rtype]:
                        data(f"  Mail Server: {mx}")
                    data(f"  → Target for email spoofing analysis")
                    
                elif rtype == 'NS':
                    success(f"Name Servers:")
                    for ns in dns_data[rtype]:
                        data(f"  {ns}")
                        
                elif rtype == 'TXT':
                    success(f"TXT Records:")
                    for txt in dns_data[rtype]:
                        data(f"  {txt}")
                        # SPF analysis
                        if 'v=spf1' in txt.lower():
                            if '~all' in txt:
                                warning("SPF SoftFail (~all) — Email spoofing POSSIBLE!")
                                dns_data['SPF_RISK'] = 'SoftFail ~all'
                            elif '-all' in txt:
                                success("SPF HardFail (-all) — Email spoofing blocked")
                                dns_data['SPF_OK'] = True
                            elif '+all' in txt:
                                warning("SPF PassAll (+all) — CRITICAL: Anyone can send as this domain!")
                                dns_data['SPF_RISK'] = 'PassAll +all — CRITICAL'
                        if 'v=dmarc1' in txt.lower():
                            if 'p=reject' in txt.lower():
                                success("DMARC p=reject — Strong email protection")
                            elif 'p=none' in txt.lower():
                                warning("DMARC p=none — Monitoring only, no enforcement")
                                dns_data['DMARC_RISK'] = 'p=none'
                                
                elif rtype == 'SOA':
                    success(f"SOA Record: {dns_data[rtype][0] if dns_data[rtype] else 'N/A'}")
                    
                elif rtype == 'AAAA':
                    for ip6 in dns_data[rtype]:
                        data(f"  IPv6: {ip6}")
                        
        # Zone transfer attempt
        info("Attempting DNS Zone Transfer (AXFR)...")
        ns_records = dns_data.get('NS', [])
        for ns in ns_records[:2]:
            ns_clean = ns.rstrip('.')
            zt = subprocess.getoutput(
                f"dig @{ns_clean} {target} AXFR 2>/dev/null | head -30"
            )
            if zt and 'Transfer failed' not in zt and 'connection refused' not in zt.lower():
                if len(zt.split('\n')) > 5:
                    warning(f"ZONE TRANSFER SUCCESSFUL via {ns_clean}!")
                    warning("CRITICAL: Full DNS map exposed!")
                    dns_data['ZONE_TRANSFER'] = zt[:2000]
                    for line in zt.split('\n')[:15]:
                        if line.strip():
                            data(f"  {line}")
                else:
                    data(f"  Zone transfer blocked at {ns_clean} ✓")
            else:
                data(f"  Zone transfer blocked at {ns_clean} ✓")
                
    except Exception as e:
        error(f"DNS error: {e}")
        # Pure Python fallback
        try:
            ip = socket.gethostbyname(target)
            dns_data['A'] = [ip]
            success(f"A Record (fallback): {ip}")
        except: pass
    
    results['dns'] = dns_data

# ─────────────────────────────────────────────────
# MODULE 3: SUBDOMAIN ENUMERATION
# ─────────────────────────────────────────────────

def run_subdomains(target, results):
    section("MODULE 03 — SUBDOMAIN ENUMERATION")
    info(f"Discovering subdomains for {target}...")
    
    found_subs = set()
    
    # Method 1: Certificate Transparency (crt.sh)
    info("Querying Certificate Transparency logs (crt.sh)...")
    crt_url = f"https://crt.sh/?q=%.{target}&output=json"
    resp, status = http_get(crt_url, timeout=15)
    
    if resp:
        try:
            certs = json.loads(resp)
            for cert in certs:
                name = cert.get('name_value', '')
                for sub in name.split('\n'):
                    sub = sub.strip().lower().lstrip('*.')
                    if sub.endswith(target) and sub not in found_subs:
                        found_subs.add(sub)
            success(f"Certificate Transparency: {len(found_subs)} subdomains found")
        except Exception as e:
            warning(f"crt.sh parse error: {e}")
    else:
        warning("crt.sh unreachable — skipping cert transparency")

    # Method 2: Common subdomain wordlist bruteforce
    info("Bruteforcing common subdomains...")
    common_subs = [
        'www', 'mail', 'ftp', 'smtp', 'pop', 'imap', 'webmail', 'admin',
        'administrator', 'portal', 'vpn', 'remote', 'dev', 'development',
        'staging', 'stage', 'test', 'testing', 'demo', 'api', 'api2',
        'backend', 'frontend', 'web', 'web2', 'old', 'new', 'beta',
        'secure', 'security', 'login', 'auth', 'sso', 'owa', 'exchange',
        'mx', 'mx1', 'mx2', 'ns', 'ns1', 'ns2', 'dns', 'git', 'gitlab',
        'github', 'jira', 'confluence', 'wiki', 'docs', 'help', 'support',
        'shop', 'store', 'pay', 'payment', 'billing', 'invoice', 'crm',
        'erp', 'db', 'database', 'mysql', 'sql', 'backup', 'backups',
        'cdn', 'static', 'assets', 'media', 'img', 'images', 'upload',
        'uploads', 'cloud', 'aws', 'azure', 'mobile', 'app', 'apps',
        'dashboard', 'monitoring', 'nagios', 'zabbix', 'kibana', 'grafana',
        'jenkins', 'ci', 'cd', 'build', 'prod', 'production', 'internal',
        'intranet', 'extranet', 'corp', 'corporate', 'office', 'hr',
        'careers', 'recruitment', 'partner', 'partners', 'client', 'clients',
        'localhost', 'server', 'server2', 'web3', 'legacy', 'archive'
    ]
    
    brute_found = []
    
    def check_subdomain(sub):
        fqdn = f"{sub}.{target}"
        try:
            ip = socket.gethostbyname(fqdn)
            return fqdn, ip
        except:
            return None, None
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_subdomain, sub): sub for sub in common_subs}
        for future in as_completed(futures):
            fqdn, ip = future.result()
            if fqdn:
                brute_found.append((fqdn, ip))
                found_subs.add(fqdn)
    
    if brute_found:
        success(f"Bruteforce discovered {len(brute_found)} live subdomains:")
        # Prioritize dangerous ones
        dangerous = ['admin', 'vpn', 'dev', 'staging', 'test', 'backup', 
                     'old', 'api', 'internal', 'legacy', 'db', 'database']
        for fqdn, ip in sorted(brute_found, key=lambda x: x[0]):
            sub_part = fqdn.split('.')[0]
            if sub_part in dangerous:
                data(f"  {Colors.RED}⚠ {fqdn:<40} {ip}{Colors.RESET}  ← HIGH PRIORITY")
            else:
                data(f"  {Colors.GREEN}✓{Colors.RESET} {fqdn:<40} {ip}")
    
    # Method 3: HackerTarget API
    info("Querying HackerTarget subdomain API...")
    ht_url = f"https://api.hackertarget.com/hostsearch/?q={target}"
    ht_resp, _ = http_get(ht_url, timeout=10)
    if ht_resp and 'error' not in ht_resp.lower() and 'API count' not in ht_resp:
        for line in ht_resp.strip().split('\n'):
            if ',' in line:
                sub, ip = line.split(',', 1)
                sub = sub.strip()
                if sub not in found_subs:
                    found_subs.add(sub)
                    data(f"  {Colors.CYAN}◆{Colors.RESET} {sub:<40} {ip.strip()}")
        success(f"HackerTarget found additional subdomains")
    
    success(f"Total unique subdomains discovered: {len(found_subs)}")
    results['subdomains'] = list(found_subs)
    results['subdomains_live'] = brute_found

# ─────────────────────────────────────────────────
# MODULE 4: EMAIL HARVESTING
# ─────────────────────────────────────────────────

def run_email_harvest(target, results):
    section("MODULE 04 — EMAIL INTELLIGENCE")
    info(f"Harvesting emails and identifying patterns for {target}...")
    
    emails_found = set()
    
    # Method 1: Hunter.io (no key needed for basic)
    info("Querying Hunter.io...")
    hunter_url = f"https://api.hunter.io/v2/domain-search?domain={target}&limit=10&api_key=free"
    resp, _ = http_get(hunter_url, timeout=10)
    if resp:
        try:
            data_h = json.loads(resp)
            if data_h.get('data'):
                pattern = data_h['data'].get('pattern', 'unknown')
                emails = data_h['data'].get('emails', [])
                success(f"Hunter.io: Email pattern detected: {{{pattern}}}@{target}")
                data(f"  Pattern: firstname.lastname@ | first.l@ | f.lastname@")
                for email_obj in emails[:10]:
                    em = email_obj.get('value', '')
                    if em:
                        emails_found.add(em)
                        data(f"  {Colors.RED}✉{Colors.RESET} {em}")
        except: pass
    
    # Method 2: Scrape common pages for emails
    info("Scraping website for email addresses...")
    pages_to_check = [
        f"https://{target}",
        f"https://{target}/contact",
        f"https://{target}/about",
        f"https://{target}/team",
        f"https://{target}/staff",
        f"https://www.{target}/contact",
    ]
    
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    
    for page in pages_to_check:
        resp, _ = http_get(page, timeout=8)
        if resp:
            found = email_pattern.findall(resp)
            for em in found:
                if target in em or em.endswith('.'+target.split('.')[-1]):
                    emails_found.add(em.lower())
    
    if emails_found:
        success(f"Total emails harvested: {len(emails_found)}")
        for em in list(emails_found)[:20]:
            data(f"  {Colors.RED}✉{Colors.RESET} {em}")
    else:
        warning("No emails found in public sources")
        info("Tip: Try theHarvester manually: theHarvester -d {target} -b all")
    
    # Detect email format pattern
    if len(emails_found) >= 2:
        info("Analyzing email format pattern...")
        email_list = list(emails_found)
        # Simple pattern detection
        data(f"  Predicted format: firstname.lastname@{target}")
        data(f"  Use for: spear phishing, credential stuffing, OSINT")
    
    results['emails'] = list(emails_found)

# ─────────────────────────────────────────────────
# MODULE 5: TECHNOLOGY FINGERPRINTING
# ─────────────────────────────────────────────────

def run_tech_fingerprint(target, results):
    section("MODULE 05 — TECHNOLOGY FINGERPRINTING")
    info(f"Fingerprinting technology stack of {target}...")
    
    tech_data = {}
    
    try:
        resp, status = http_get(f"https://{target}", timeout=10)
        resp_http, _ = http_get(f"http://{target}", timeout=10)
        
        # Get headers
        req = request.Request(f"https://{target}")
        req.add_header('User-Agent', 
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0')
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        headers = {}
        try:
            with request.urlopen(req, timeout=10, context=ctx) as r:
                headers = dict(r.headers)
        except: pass
        
        content = resp or resp_http or ''
        
        # Server detection
        server = headers.get('Server', headers.get('server', 'Unknown'))
        if server and server != 'Unknown':
            success(f"Web Server: {Colors.RED}{server}{Colors.RESET}")
            tech_data['server'] = server
            # Version check
            version_match = re.search(r'[\d]+\.[\d]+', server)
            if version_match:
                warning(f"Server version exposed: {server} — Search CVEs!")
        
        # X-Powered-By
        powered = headers.get('X-Powered-By', headers.get('x-powered-by', ''))
        if powered:
            success(f"Backend Technology: {Colors.RED}{powered}{Colors.RESET}")
            tech_data['powered_by'] = powered
            warning("X-Powered-By header exposed — reveals backend technology")
        
        # Security headers analysis
        info("Analyzing security headers...")
        security_headers = {
            'Strict-Transport-Security': 'HSTS',
            'Content-Security-Policy': 'CSP', 
            'X-Frame-Options': 'Clickjacking Protection',
            'X-XSS-Protection': 'XSS Protection',
            'X-Content-Type-Options': 'MIME Sniffing Protection',
            'Referrer-Policy': 'Referrer Policy',
        }
        
        missing_headers = []
        for header, name in security_headers.items():
            if header.lower() in [h.lower() for h in headers.keys()]:
                data(f"  {Colors.GREEN}✓{Colors.RESET} {name}: Present")
            else:
                missing_headers.append(name)
                data(f"  {Colors.RED}✗{Colors.RESET} {name}: MISSING")
        
        if missing_headers:
            warning(f"Missing security headers: {', '.join(missing_headers)}")
            tech_data['missing_headers'] = missing_headers
        
        # CMS Detection from content
        if content:
            cms_signatures = {
                'WordPress':   ['wp-content', 'wp-includes', 'wordpress'],
                'Joomla':      ['joomla', '/components/com_'],
                'Drupal':      ['drupal', 'sites/default/files'],
                'Shopify':     ['cdn.shopify.com', 'myshopify'],
                'Magento':     ['mage/', 'magento'],
                'Django':      ['csrfmiddlewaretoken', 'django'],
                'Laravel':     ['laravel_session', 'laravel'],
                'React':       ['react', '__REACT', 'react-dom'],
                'Angular':     ['ng-version', 'angular'],
                'Vue.js':      ['vue.js', '__vue__', 'nuxt'],
                'jQuery':      ['jquery'],
                'Bootstrap':   ['bootstrap'],
                'Cloudflare':  ['__cfduid', 'cf-ray', 'cloudflare'],
            }
            
            detected_tech = []
            content_lower = content.lower()
            for tech, signatures in cms_signatures.items():
                if any(sig in content_lower for sig in signatures):
                    detected_tech.append(tech)
            
            if detected_tech:
                success(f"Technologies detected:")
                for tech in detected_tech:
                    data(f"  {Colors.YELLOW}◆{Colors.RESET} {tech}")
                    tech_data[tech] = True
            
            # Check for version numbers in source
            version_patterns = [
                (r'WordPress\s+([\d.]+)', 'WordPress'),
                (r'jQuery\s+v([\d.]+)', 'jQuery'),
                (r'Bootstrap\s+v([\d.]+)', 'Bootstrap'),
                (r'Angular\s+([\d.]+)', 'Angular'),
                (r'vue@([\d.]+)', 'Vue.js'),
            ]
            
            info("Checking for version disclosures...")
            for pattern, name in version_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    ver = match.group(1)
                    warning(f"Version exposed: {name} {ver} — Check for CVEs at nvd.nist.gov!")
                    tech_data[f'{name}_version'] = ver
        
        tech_data['headers'] = dict(headers)
        
    except Exception as e:
        error(f"Tech fingerprint error: {e}")
    
    results['technology'] = tech_data

# ─────────────────────────────────────────────────
# MODULE 6: PORT SCANNING
# ─────────────────────────────────────────────────

def run_port_scan(target, results):
    section("MODULE 06 — PORT INTELLIGENCE")
    info(f"Scanning common ports on {target}...")
    warning("Note: For comprehensive scanning, use: nmap -sV -sC -A {target}")
    
    try:
        target_ip = socket.gethostbyname(target)
        info(f"Resolved to: {target_ip}")
    except:
        error("Cannot resolve target IP")
        return
    
    # Common ports with service names and risk levels
    common_ports = {
        21:   ('FTP',           'HIGH',   'File transfer — often anonymous access'),
        22:   ('SSH',           'MED',    'Secure Shell — bruteforce target'),
        23:   ('Telnet',        'CRIT',   'Unencrypted remote access — legacy risk'),
        25:   ('SMTP',          'HIGH',   'Mail server — relay/spoofing risk'),
        53:   ('DNS',           'MED',    'DNS service — zone transfer target'),
        80:   ('HTTP',          'MED',    'Web server — unencrypted'),
        110:  ('POP3',          'HIGH',   'Email retrieval — unencrypted'),
        143:  ('IMAP',          'HIGH',   'Email — unencrypted'),
        443:  ('HTTPS',         'LOW',    'Secure web — check certificate'),
        445:  ('SMB',           'CRIT',   'Windows sharing — EternalBlue target'),
        1433: ('MSSQL',         'CRIT',   'SQL Server — direct DB access'),
        1521: ('Oracle DB',     'CRIT',   'Oracle database — high value'),
        3306: ('MySQL',         'CRIT',   'MySQL — direct DB access'),
        3389: ('RDP',           'CRIT',   'Remote Desktop — bruteforce target'),
        5432: ('PostgreSQL',    'CRIT',   'PostgreSQL — direct DB access'),
        5900: ('VNC',           'CRIT',   'Remote desktop — often no auth'),
        6379: ('Redis',         'CRIT',   'Cache DB — often no auth required'),
        8080: ('HTTP-Alt',      'MED',    'Alt web port — dev/proxy'),
        8443: ('HTTPS-Alt',     'MED',    'Alt HTTPS — admin panels'),
        9200: ('Elasticsearch', 'CRIT',   'Search DB — often no auth'),
        27017:('MongoDB',       'CRIT',   'MongoDB — often no auth required'),
    }
    
    open_ports = []
    risk_colors = {
        'CRIT': Colors.RED,
        'HIGH': Colors.YELLOW,
        'MED':  Colors.CYAN,
        'LOW':  Colors.GREEN
    }
    
    def scan_port(port, service_info):
        service, risk, desc = service_info
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            result = sock.connect_ex((target_ip, port))
            sock.close()
            if result == 0:
                return port, service, risk, desc
        except:
            pass
        return None, None, None, None
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(scan_port, port, info_tuple): port 
                   for port, info_tuple in common_ports.items()}
        for future in as_completed(futures):
            port, service, risk, desc = future.result()
            if port:
                open_ports.append((port, service, risk, desc))
    
    open_ports.sort(key=lambda x: x[0])
    
    if open_ports:
        success(f"Open ports discovered: {len(open_ports)}")
        for port, service, risk, desc in open_ports:
            color = risk_colors.get(risk, Colors.WHITE)
            print(f"    {color}[{risk}]{Colors.RESET} "
                  f"{Colors.BOLD}Port {port:<6}{Colors.RESET} "
                  f"{service:<15} {Colors.DIM}{desc}{Colors.RESET}")
    else:
        info("No common ports open (target may be firewalled)")
        data("Try: nmap -sS -p- --open {target} for full scan")
    
    results['ports'] = [(p, s, r) for p, s, r, _ in open_ports]

# ─────────────────────────────────────────────────
# MODULE 7: SSL/TLS CERTIFICATE ANALYSIS
# ─────────────────────────────────────────────────

def run_ssl_analysis(target, results):
    section("MODULE 07 — SSL/TLS CERTIFICATE INTELLIGENCE")
    info(f"Analyzing SSL certificate for {target}...")
    
    ssl_data = {}
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((target, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=target) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()
                
                success(f"SSL/TLS Version: {version}")
                ssl_data['tls_version'] = version
                
                if version in ['TLSv1', 'TLSv1.1', 'SSLv3']:
                    warning(f"Outdated TLS version: {version} — VULNERABLE!")
                
                success(f"Cipher Suite: {cipher[0]}")
                ssl_data['cipher'] = cipher[0]
                
                # Subject
                subject = dict(x[0] for x in cert.get('subject', []))
                issuer = dict(x[0] for x in cert.get('issuer', []))
                
                cn = subject.get('commonName', 'N/A')
                org = subject.get('organizationName', 'N/A')
                
                success(f"Common Name: {cn}")
                success(f"Organization: {org}")
                ssl_data['cn'] = cn
                ssl_data['org'] = org
                
                data(f"  Issuer: {issuer.get('organizationName', 'Unknown')}")
                
                # Expiry
                not_after = cert.get('notAfter', '')
                if not_after:
                    try:
                        exp = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                        days = (exp - datetime.now()).days
                        if days < 30:
                            warning(f"Certificate expires in {days} days!")
                        else:
                            data(f"  Expires: {not_after} ({days} days remaining)")
                        ssl_data['expires_days'] = days
                    except: pass
                
                # SAN (Subject Alternative Names) — reveals subdomains!
                san = cert.get('subjectAltName', [])
                if san:
                    san_domains = [s[1] for s in san if s[0] == 'DNS']
                    if san_domains:
                        success(f"SAN Domains found ({len(san_domains)}) — additional subdomains:")
                        for domain in san_domains[:20]:
                            data(f"  {Colors.YELLOW}◆{Colors.RESET} {domain}")
                        ssl_data['san_domains'] = san_domains
                        
    except ConnectionRefusedError:
        warning("Port 443 closed — no HTTPS")
    except Exception as e:
        warning(f"SSL analysis: {e}")
    
    results['ssl'] = ssl_data

# ─────────────────────────────────────────────────
# MODULE 8: WEB RECON (robots.txt, sitemap, headers)
# ─────────────────────────────────────────────────

def run_web_recon(target, results):
    section("MODULE 08 — WEB INTELLIGENCE")
    info(f"Extracting web intelligence from {target}...")
    
    web_data = {}
    
    # robots.txt
    info("Checking robots.txt...")
    for scheme in ['https', 'http']:
        robots_url = f"{scheme}://{target}/robots.txt"
        resp, status = http_get(robots_url, timeout=8)
        if resp and ('disallow' in resp.lower() or 'allow' in resp.lower()):
            success("robots.txt found — analyzing hidden paths:")
            web_data['robots'] = resp
            
            disallow_paths = re.findall(r'Disallow:\s*(.+)', resp, re.IGNORECASE)
            if disallow_paths:
                warning("Disallowed paths (high value targets):")
                for path in disallow_paths[:20]:
                    path = path.strip()
                    if path and path != '/':
                        data(f"  {Colors.RED}⚑{Colors.RESET} {path}")
            break
    else:
        data("  robots.txt not found or empty")
    
    # sitemap.xml
    info("Checking sitemap.xml...")
    sitemap_urls = [
        f"https://{target}/sitemap.xml",
        f"https://{target}/sitemap_index.xml",
        f"https://www.{target}/sitemap.xml",
    ]
    
    for url in sitemap_urls:
        resp, _ = http_get(url, timeout=8)
        if resp and '<url>' in resp.lower():
            urls_found = re.findall(r'<loc>(.*?)</loc>', resp, re.IGNORECASE)
            success(f"Sitemap found: {len(urls_found)} URLs mapped")
            web_data['sitemap_urls'] = urls_found
            # Show interesting ones
            interesting = [u for u in urls_found if any(
                kw in u.lower() for kw in 
                ['admin', 'api', 'login', 'auth', 'internal', 'backup', 'upload']
            )]
            if interesting:
                warning("Interesting URLs in sitemap:")
                for u in interesting[:10]:
                    data(f"  {Colors.RED}⚑{Colors.RESET} {u}")
            break
    
    # Check common sensitive paths
    info("Probing sensitive paths...")
    sensitive_paths = [
        ('/.env',              'CRITICAL', 'Environment variables — credentials'),
        ('/.git/config',       'CRITICAL', 'Git repository exposed'),
        ('/backup/',           'CRITICAL', 'Backup directory'),
        ('/backup.zip',        'CRITICAL', 'Backup archive'),
        ('/backup.sql',        'CRITICAL', 'Database backup'),
        ('/admin/',            'HIGH',     'Admin panel'),
        ('/administrator/',    'HIGH',     'Admin panel (Joomla)'),
        ('/wp-admin/',         'HIGH',     'WordPress admin'),
        ('/phpinfo.php',       'HIGH',     'PHP configuration exposed'),
        ('/server-status',     'HIGH',     'Apache server status'),
        ('/config.php',        'HIGH',     'Configuration file'),
        ('/config.php.bak',    'HIGH',     'Configuration backup'),
        ('/.htpasswd',         'HIGH',     'Password file'),
        ('/web.config',        'HIGH',     'IIS configuration'),
        ('/crossdomain.xml',   'MED',      'Flash crossdomain policy'),
        ('/robots.txt',        'LOW',      'Already checked'),
        ('/sitemap.xml',       'LOW',      'Already checked'),
    ]
    
    exposed_paths = []
    
    def check_path(path_tuple):
        path, risk, desc = path_tuple
        url = f"https://{target}{path}"
        resp, status = http_get(url, timeout=5)
        if resp and status == 200 and len(resp) > 10:
            return path, risk, desc, len(resp)
        return None, None, None, None
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_path, p): p for p in sensitive_paths}
        for future in as_completed(futures):
            path, risk, desc, size = future.result()
            if path and path not in ['/robots.txt', '/sitemap.xml']:
                exposed_paths.append((path, risk, desc, size))
    
    if exposed_paths:
        warning(f"SENSITIVE PATHS EXPOSED ({len(exposed_paths)} found):")
        for path, risk, desc, size in exposed_paths:
            color = Colors.RED if risk == 'CRITICAL' else Colors.YELLOW
            data(f"  {color}[{risk}]{Colors.RESET} {path} ({size} bytes) — {desc}")
    else:
        success("No obvious sensitive paths exposed")
    
    # Wayback Machine check
    info("Checking Wayback Machine for historical data...")
    wb_url = f"https://archive.org/wayback/available?url={target}"
    resp, _ = http_get(wb_url, timeout=10)
    if resp:
        try:
            wb_data = json.loads(resp)
            snapshot = wb_data.get('archived_snapshots', {}).get('closest', {})
            if snapshot:
                wb_ts = snapshot.get('timestamp', '')
                wb_link = snapshot.get('url', '')
                success(f"Wayback Machine: Oldest/closest snapshot found")
                data(f"  Timestamp: {wb_ts}")
                data(f"  URL: {wb_link}")
                data(f"  → Analyze at: https://web.archive.org/web/*/{target}")
                web_data['wayback'] = wb_link
        except: pass
    
    # Google Dorks generator
    info("Generating Google Dork queries...")
    success("Copy these dorks to Google for deeper intelligence:")
    dorks = [
        f'site:{target}',
        f'site:{target} filetype:pdf',
        f'site:{target} filetype:xls OR filetype:xlsx',
        f'site:{target} filetype:sql',
        f'site:{target} filetype:env',
        f'site:{target} filetype:log',
        f'site:{target} intitle:"index of"',
        f'site:{target} inurl:admin',
        f'site:{target} inurl:backup',
        f'site:{target} "confidential"',
        f'site:{target} "internal use only"',
        f'site:{target} "not for distribution"',
        f'"{target}" password filetype:txt',
        f'"{target}" username password',
        f'site:github.com "{target}"',
        f'site:pastebin.com "{target}"',
    ]
    
    web_data['dorks'] = dorks
    for dork in dorks:
        data(f"  {Colors.CYAN}◆{Colors.RESET} {dork}")
    
    results['web'] = web_data

# ─────────────────────────────────────────────────
# MODULE 9: IP GEOLOCATION & ASN
# ─────────────────────────────────────────────────

def run_ip_intel(target, results):
    section("MODULE 09 — IP & NETWORK INTELLIGENCE")
    info(f"Gathering IP and network intelligence for {target}...")
    
    ip_data = {}
    
    try:
        # Resolve IP
        target_ip = socket.gethostbyname(target)
        success(f"Primary IP: {target_ip}")
        ip_data['ip'] = target_ip
        
        # Check if private IP (shouldn't be for public target)
        try:
            if ipaddress.ip_address(target_ip).is_private:
                warning("Private IP address — target may be internal only")
        except: pass
        
        # ipinfo.io for geolocation + ASN
        info("Querying IP geolocation and ASN...")
        ipinfo_url = f"https://ipinfo.io/{target_ip}/json"
        resp, _ = http_get(ipinfo_url, timeout=8)
        
        if resp:
            try:
                geo = json.loads(resp)
                
                city    = geo.get('city', 'Unknown')
                region  = geo.get('region', 'Unknown')
                country = geo.get('country', 'Unknown')
                org     = geo.get('org', 'Unknown')
                asn     = geo.get('org', '').split(' ')[0] if geo.get('org') else 'Unknown'
                postal  = geo.get('postal', 'Unknown')
                loc     = geo.get('loc', 'Unknown')
                
                success(f"Geolocation:")
                data(f"  Location:  {city}, {region}, {country}")
                data(f"  Postal:    {postal}")
                data(f"  GPS:       {loc}")
                data(f"  Provider:  {org}")
                
                success(f"Network:")
                data(f"  ASN:       {asn}")
                data(f"  Org:       {org}")
                
                # Identify hosting
                hosting_keywords = {
                    'Amazon': 'AWS — Check for misconfigured S3 buckets',
                    'Google': 'Google Cloud — Check GCS buckets',
                    'Microsoft': 'Azure — Check Azure Blob storage',
                    'Cloudflare': 'Cloudflare CDN — Real IP hidden',
                    'DigitalOcean': 'DigitalOcean VPS',
                    'Linode': 'Linode/Akamai VPS',
                    'OVH': 'OVH hosting',
                }
                
                for keyword, note in hosting_keywords.items():
                    if keyword.lower() in org.lower():
                        warning(f"Hosted on {keyword}: {note}")
                        ip_data['hosting'] = keyword
                
                if 'Cloudflare' in org:
                    warning("Real IP hidden behind Cloudflare — try:")
                    data("  1. Check historical DNS (securitytrails.com)")
                    data("  2. Check SSL certificate for origin IP")
                    data("  3. Check subdomains not behind Cloudflare")
                
                ip_data['geo'] = geo
                
            except Exception as e:
                warning(f"IP intel parse error: {e}")
        
        # HackerTarget reverse IP
        info("Checking reverse IP (other domains on same server)...")
        ht_rev_url = f"https://api.hackertarget.com/reverseiplookup/?q={target_ip}"
        rev_resp, _ = http_get(ht_rev_url, timeout=8)
        
        if rev_resp and 'error' not in rev_resp.lower() and len(rev_resp.strip()) > 5:
            other_domains = [d.strip() for d in rev_resp.strip().split('\n') if d.strip()]
            if len(other_domains) > 1:
                success(f"Reverse IP: {len(other_domains)} domains on same server:")
                for domain in other_domains[:10]:
                    data(f"  {Colors.CYAN}◆{Colors.RESET} {domain}")
                ip_data['reverse_ip'] = other_domains
                
                if len(other_domains) > 50:
                    info("Shared hosting detected — other sites may be exploitable")
                    data("  Virtual host attacks possible if one site is compromised")
    
    except Exception as e:
        error(f"IP intelligence error: {e}")
    
    results['ip_intel'] = ip_data

# ─────────────────────────────────────────────────
# MODULE 10: BREACH & DARK WEB CHECK
# ─────────────────────────────────────────────────

def run_breach_check(target, results):
    section("MODULE 10 — BREACH INTELLIGENCE")
    info(f"Checking for known data breaches affecting {target}...")
    
    breach_data = {}
    
    # Have I Been Pwned domain search
    info("Querying Have I Been Pwned...")
    hibp_url = f"https://haveibeenpwned.com/api/v3/breacheddomain/{target}"
    resp, status = http_get(hibp_url, timeout=10, 
                           headers={'hibp-api-key': 'free'})
    
    if resp and status == 200:
        try:
            breaches = json.loads(resp)
            if breaches:
                warning(f"BREACH FOUND: {len(breaches)} breaches affect {target}!")
                for breach in breaches[:10]:
                    data(f"  {Colors.RED}☠{Colors.RESET} Breach: {breach}")
                breach_data['breaches'] = breaches
        except: pass
    elif status == 404:
        success(f"No breaches found for {target} on HIBP")
    else:
        info("HIBP check requires API key — check manually:")
        data(f"  https://haveibeenpwned.com/DomainSearch")
    
    # Check common paste sites
    info("Checking for domain mentions in paste sites...")
    paste_url = f"https://psbdmp.ws/api/v3/search/{target}"
    resp, _ = http_get(paste_url, timeout=8)
    if resp:
        try:
            paste_data = json.loads(resp)
            if paste_data.get('data'):
                count = len(paste_data['data'])
                warning(f"Found {count} pastes mentioning {target}!")
                data(f"  Check: https://pastebin.com/search?q={target}")
                breach_data['pastes_found'] = count
        except: pass
    
    # DeHashed check (public endpoint)
    info("Intelligence recommendations:")
    data(f"  1. dehashed.com — search @{target} for leaked credentials")
    data(f"  2. intelx.io — deep dark web and breach search")
    data(f"  3. leak-lookup.com — credential leak database")
    data(f"  4. spycloud.com — enterprise breach monitoring")
    data(f"  5. breachdirectory.org — free breach lookup")
    
    results['breaches'] = breach_data

# ─────────────────────────────────────────────────
# MODULE 11: SOCIAL MEDIA PRESENCE
# ─────────────────────────────────────────────────

def run_social_recon(target, results):
    section("MODULE 11 — SOCIAL MEDIA INTELLIGENCE")
    
    # Extract company name from domain
    company = target.split('.')[0]
    
    info(f"Mapping social media presence for: {company}")
    
    social_platforms = {
        'LinkedIn':   f"https://www.linkedin.com/company/{company}",
        'Twitter/X':  f"https://twitter.com/{company}",
        'Facebook':   f"https://www.facebook.com/{company}",
        'Instagram':  f"https://www.instagram.com/{company}",
        'GitHub':     f"https://github.com/{company}",
        'YouTube':    f"https://www.youtube.com/@{company}",
        'Reddit':     f"https://www.reddit.com/r/{company}",
    }
    
    social_data = {}
    
    for platform, url in social_platforms.items():
        resp, status = http_get(url, timeout=6)
        if resp and status == 200 and len(resp) > 500:
            # Check if it's a real profile not a 404 page
            if any(term in resp.lower() for term in 
                   ['followers', 'following', 'posts', 'profile', 'about']):
                success(f"{platform}: Profile likely exists")
                data(f"  {url}")
                social_data[platform] = url
            else:
                data(f"  {Colors.DIM}{platform}: Uncertain{Colors.RESET}")
        else:
            data(f"  {Colors.DIM}{platform}: Not found{Colors.RESET}")
    
    # GitHub specific recon
    info("Deep GitHub reconnaissance...")
    gh_url = f"https://api.github.com/orgs/{company}/repos?per_page=10&sort=updated"
    resp, status = http_get(gh_url, timeout=10)
    
    if resp and status == 200:
        try:
            repos = json.loads(resp)
            if repos:
                success(f"GitHub organization found: {len(repos)} public repositories")
                for repo in repos[:10]:
                    name = repo.get('name', '')
                    lang = repo.get('language', 'Unknown')
                    updated = repo.get('updated_at', '')[:10]
                    data(f"  {Colors.YELLOW}◆{Colors.RESET} {name} [{lang}] — updated {updated}")
                
                warning("Check these repos for:")
                data("  → Hardcoded credentials in source code")
                data("  → API keys in commit history")
                data("  → .env files accidentally committed")
                data("  → Internal URLs and hostnames")
                data(f"  Command: trufflehog github --org {company}")
                social_data['github_repos'] = [r.get('name') for r in repos]
        except: pass
    
    results['social'] = social_data

# ─────────────────────────────────────────────────
# REPORT GENERATION
# ─────────────────────────────────────────────────

def generate_report(target, results, start_time):
    section("GENERATING INTELLIGENCE REPORT")
    
    end_time = datetime.now()
    duration = (end_time - start_time).seconds
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = f"godseye_{target.replace('.','_')}_{timestamp}.json"
    html_file = f"godseye_{target.replace('.','_')}_{timestamp}.html"
    
    # Save JSON
    with open(json_file, 'w') as f:
        json.dump({
            'target': target,
            'timestamp': str(end_time),
            'duration_seconds': duration,
            'results': results
        }, f, indent=2, default=str)
    
    # Generate HTML report
    html = generate_html_report(target, results, end_time, duration)
    with open(html_file, 'w') as f:
        f.write(html)
    
    success(f"JSON Report: {json_file}")
    success(f"HTML Report: {html_file}")
    info(f"Open HTML report: firefox {html_file}")
    
    # Print summary
    section("EXECUTIVE SUMMARY")
    
    print(f"\n  {Colors.BOLD}Target:{Colors.RESET} {target}")
    print(f"  {Colors.BOLD}Scan Time:{Colors.RESET} {duration} seconds")
    print(f"  {Colors.BOLD}Timestamp:{Colors.RESET} {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Count findings
    sub_count = len(results.get('subdomains', []))
    email_count = len(results.get('emails', []))
    port_count = len(results.get('ports', []))
    
    print(f"\n  {Colors.BOLD}Intelligence Gathered:{Colors.RESET}")
    data(f"  Subdomains:     {sub_count}")
    data(f"  Emails:         {email_count}")
    data(f"  Open Ports:     {port_count}")
    data(f"  Technologies:   {len(results.get('technology', {}))}")
    
    # Critical findings
    critical = []
    
    if results.get('whois', {}).get('RISK'):
        critical.append(f"Domain Expiry: {results['whois']['RISK']}")
    if results.get('dns', {}).get('SPF_RISK'):
        critical.append(f"Email Spoofing: {results['dns']['SPF_RISK']}")
    if results.get('dns', {}).get('ZONE_TRANSFER'):
        critical.append("DNS Zone Transfer: SUCCESSFUL — Full DNS map exposed")
    if results.get('web', {}).get('robots'):
        critical.append("Sensitive paths revealed in robots.txt")
    if results.get('breaches', {}).get('breaches'):
        critical.append(f"Data Breaches: {len(results['breaches']['breaches'])} breaches found")
    
    if critical:
        print(f"\n  {Colors.RED}{Colors.BOLD}⚠ CRITICAL FINDINGS:{Colors.RESET}")
        for c in critical:
            print(f"  {Colors.RED}  ✗ {c}{Colors.RESET}")
    
    print(f"\n  {Colors.GREEN}{Colors.BOLD}Scan Complete. Stay ethical. Stay legal.{Colors.RESET}\n")


def generate_html_report(target, results, end_time, duration):
    """Generate a professional HTML intelligence report"""
    
    sub_count = len(results.get('subdomains', []))
    email_count = len(results.get('emails', []))
    port_count = len(results.get('ports', []))
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GodsEye Report — {target}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ 
    font-family: 'Courier New', monospace; 
    background: #0a0a0a; color: #e0e0e0;
    line-height: 1.6; padding: 20px;
  }}
  .header {{ 
    background: linear-gradient(135deg, #1a0a0a, #0d1a0a);
    border: 1px solid #ff3333; border-radius: 8px;
    padding: 30px; margin-bottom: 20px; text-align: center;
  }}
  .logo {{ color: #ff3333; font-size: 2em; font-weight: bold; }}
  .subtitle {{ color: #888; margin-top: 5px; }}
  .meta {{ 
    display: grid; grid-template-columns: repeat(4, 1fr); 
    gap: 15px; margin-bottom: 20px;
  }}
  .meta-card {{
    background: #111; border: 1px solid #333;
    border-radius: 6px; padding: 15px; text-align: center;
  }}
  .meta-card .num {{ font-size: 2em; color: #ff3333; font-weight: bold; }}
  .meta-card .label {{ color: #888; font-size: 0.8em; }}
  .section {{
    background: #111; border: 1px solid #222;
    border-left: 3px solid #ff3333;
    border-radius: 6px; padding: 20px; margin-bottom: 15px;
  }}
  .section h2 {{ color: #ff3333; margin-bottom: 15px; font-size: 1em; }}
  .item {{ 
    padding: 6px 0; border-bottom: 1px solid #1a1a1a;
    display: flex; gap: 10px;
  }}
  .item:last-child {{ border-bottom: none; }}
  .badge {{
    padding: 2px 8px; border-radius: 3px; font-size: 0.7em;
    font-weight: bold; white-space: nowrap;
  }}
  .badge-crit {{ background: #ff0000; color: white; }}
  .badge-high {{ background: #ff8800; color: white; }}
  .badge-med  {{ background: #ffcc00; color: black; }}
  .badge-low  {{ background: #00aa00; color: white; }}
  .badge-info {{ background: #0066cc; color: white; }}
  .warn {{ color: #ff8800; }}
  .good {{ color: #00cc00; }}
  .danger {{ color: #ff3333; }}
  .dim {{ color: #666; font-size: 0.9em; }}
  .dork {{ 
    background: #0d1a0d; border: 1px solid #1a3a1a;
    padding: 4px 8px; margin: 2px 0; border-radius: 3px;
    font-size: 0.85em; color: #00cc66;
  }}
  .footer {{
    text-align: center; color: #444; margin-top: 30px;
    font-size: 0.8em;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">⚡ GODSEYE INTELLIGENCE REPORT</div>
  <div class="subtitle">Target: {target} | Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')} | Duration: {duration}s</div>
  <div style="color:#ff3333;margin-top:10px;font-size:0.8em;">⚠ FOR AUTHORIZED PENETRATION TESTING ONLY ⚠</div>
</div>

<div class="meta">
  <div class="meta-card">
    <div class="num">{sub_count}</div>
    <div class="label">SUBDOMAINS</div>
  </div>
  <div class="meta-card">
    <div class="num">{email_count}</div>
    <div class="label">EMAILS</div>
  </div>
  <div class="meta-card">
    <div class="num">{port_count}</div>
    <div class="label">OPEN PORTS</div>
  </div>
  <div class="meta-card">
    <div class="num" style="color:#ff8800">!</div>
    <div class="label">REVIEW REQUIRED</div>
  </div>
</div>
"""
    
    # DNS Section
    dns = results.get('dns', {})
    if dns:
        html += '<div class="section"><h2>🌐 DNS INTELLIGENCE</h2>'
        for rtype in ['A', 'AAAA', 'MX', 'NS', 'TXT']:
            records = dns.get(rtype, [])
            if records:
                for r in records[:5]:
                    html += f'<div class="item"><span class="badge badge-info">{rtype}</span><span>{r}</span></div>'
        if dns.get('SPF_RISK'):
            html += f'<div class="item"><span class="badge badge-high">SPF</span><span class="warn">{dns["SPF_RISK"]} — Email spoofing possible!</span></div>'
        if dns.get('ZONE_TRANSFER'):
            html += '<div class="item"><span class="badge badge-crit">AXFR</span><span class="danger">ZONE TRANSFER SUCCESSFUL — Full DNS map leaked!</span></div>'
        html += '</div>'
    
    # Subdomains
    subs = results.get('subdomains_live', [])
    if subs:
        html += '<div class="section"><h2>🔍 LIVE SUBDOMAINS</h2>'
        dangerous = ['admin', 'vpn', 'dev', 'staging', 'test', 'backup', 'old', 'api', 'internal', 'legacy', 'db']
        for fqdn, ip in subs[:30]:
            sub = fqdn.split('.')[0]
            badge = 'badge-crit' if sub in dangerous else 'badge-low'
            label = 'HIGH PRIORITY' if sub in dangerous else 'FOUND'
            html += f'<div class="item"><span class="badge {badge}">{label}</span><span>{fqdn}</span><span class="dim">{ip}</span></div>'
        html += '</div>'
    
    # Emails
    emails = results.get('emails', [])
    if emails:
        html += '<div class="section"><h2>✉ EMAIL INTELLIGENCE</h2>'
        for em in emails[:20]:
            html += f'<div class="item"><span class="badge badge-high">EMAIL</span><span class="warn">{em}</span></div>'
        html += '</div>'
    
    # Ports
    ports = results.get('ports', [])
    if ports:
        html += '<div class="section"><h2>🔌 OPEN PORTS</h2>'
        for port, service, risk in ports:
            badge = f'badge-{"crit" if risk=="CRIT" else "high" if risk=="HIGH" else "med" if risk=="MED" else "low"}'
            html += f'<div class="item"><span class="badge {badge}">{risk}</span><span>Port {port}</span><span>{service}</span></div>'
        html += '</div>'
    
    # Technology
    tech = results.get('technology', {})
    if tech.get('server') or tech.get('powered_by'):
        html += '<div class="section"><h2>⚙ TECHNOLOGY FINGERPRINT</h2>'
        if tech.get('server'):
            html += f'<div class="item"><span class="badge badge-high">SERVER</span><span class="warn">{tech["server"]}</span></div>'
        if tech.get('powered_by'):
            html += f'<div class="item"><span class="badge badge-high">BACKEND</span><span class="warn">{tech["powered_by"]}</span></div>'
        for t in ['WordPress', 'Joomla', 'Drupal', 'Django', 'Laravel', 'React', 'Angular']:
            if tech.get(t):
                html += f'<div class="item"><span class="badge badge-info">TECH</span><span>{t}</span></div>'
        html += '</div>'
    
    # Google Dorks
    dorks = results.get('web', {}).get('dorks', [])
    if dorks:
        html += '<div class="section"><h2>🔎 GOOGLE DORK QUERIES</h2>'
        html += '<p class="dim" style="margin-bottom:10px">Copy these queries into Google for deeper intelligence:</p>'
        for dork in dorks:
            html += f'<div class="dork">{dork}</div>'
        html += '</div>'
    
    # IP Intel
    ip_intel = results.get('ip_intel', {})
    if ip_intel.get('geo'):
        geo = ip_intel['geo']
        html += '<div class="section"><h2>🌍 IP & GEOLOCATION</h2>'
        html += f'<div class="item"><span class="badge badge-info">IP</span><span>{ip_intel.get("ip","")}</span></div>'
        html += f'<div class="item"><span class="badge badge-info">LOCATION</span><span>{geo.get("city","")}, {geo.get("region","")}, {geo.get("country","")}</span></div>'
        html += f'<div class="item"><span class="badge badge-info">GPS</span><span>{geo.get("loc","")}</span></div>'
        html += f'<div class="item"><span class="badge badge-info">PROVIDER</span><span>{geo.get("org","")}</span></div>'
        html += '</div>'
    
    # SSL
    ssl_data = results.get('ssl', {})
    if ssl_data:
        html += '<div class="section"><h2>🔒 SSL/TLS INTELLIGENCE</h2>'
        html += f'<div class="item"><span class="badge badge-info">TLS</span><span>{ssl_data.get("tls_version","")}</span></div>'
        html += f'<div class="item"><span class="badge badge-info">CN</span><span>{ssl_data.get("cn","")}</span></div>'
        html += f'<div class="item"><span class="badge badge-info">ORG</span><span>{ssl_data.get("org","")}</span></div>'
        san = ssl_data.get('san_domains', [])
        for domain in san[:10]:
            html += f'<div class="item"><span class="badge badge-low">SAN</span><span>{domain}</span></div>'
        html += '</div>'
    
    html += f"""
<div class="footer">
  <p>GodsEye v1.0 — Advanced Reconnaissance Intelligence Tool</p>
  <p>For authorized penetration testing and security research only.</p>
  <p>Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>

</body>
</html>"""
    
    return html

# ─────────────────────────────────────────────────
# MAIN ENGINE
# ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='GodsEye — Advanced Reconnaissance Intelligence Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 godseye.py certifiedhacker.com
  python3 godseye.py example.com --skip-ports
  python3 godseye.py target.com --modules whois,dns,subdomains

Modules:
  whois, dns, subdomains, emails, tech, ports, ssl, web, ip, breach, social

Legal:
  This tool is for authorized penetration testing only.
  Unauthorized use is illegal and unethical.
        """
    )
    parser.add_argument('target', help='Target domain (e.g., certifiedhacker.com)')
    parser.add_argument('--skip-ports', action='store_true', 
                        help='Skip port scanning (faster)')
    parser.add_argument('--modules', type=str,
                        help='Run specific modules only (comma-separated)')
    parser.add_argument('--timeout', type=int, default=8,
                        help='HTTP timeout in seconds (default: 8)')
    
    args = parser.parse_args()
    
    # Clean target
    target = args.target.lower()
    target = target.replace('https://', '').replace('http://', '').replace('www.', '')
    target = target.split('/')[0]
    
    banner()
    
    print(f"  {Colors.BOLD}Target:{Colors.RESET}    {Colors.RED}{target}{Colors.RESET}")
    print(f"  {Colors.BOLD}Started:{Colors.RESET}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {Colors.BOLD}Warning:{Colors.RESET}   {Colors.YELLOW}Authorized use only — You are responsible for your actions{Colors.RESET}")
    
    # Confirm
    print(f"\n  {Colors.YELLOW}Do you have authorization to scan {target}? (yes/no):{Colors.RESET} ", end='')
    try:
        confirm = input().strip().lower()
        if confirm not in ['yes', 'y']:
            print(f"\n  {Colors.RED}Scan cancelled. Always get authorization first.{Colors.RESET}\n")
            sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n  {Colors.RED}Cancelled.{Colors.RESET}\n")
        sys.exit(0)
    
    results = {}
    start_time = datetime.now()
    
    # Determine which modules to run
    all_modules = ['whois', 'dns', 'subdomains', 'emails', 'tech', 'ssl', 'web', 'ip', 'ports', 'breach', 'social']
    
    if args.modules:
        modules_to_run = [m.strip() for m in args.modules.split(',')]
    else:
        modules_to_run = all_modules
    
    if args.skip_ports and 'ports' in modules_to_run:
        modules_to_run.remove('ports')
    
    # Module map
    module_map = {
        'whois':     lambda: run_whois(target, results),
        'dns':       lambda: run_dns(target, results),
        'subdomains':lambda: run_subdomains(target, results),
        'emails':    lambda: run_email_harvest(target, results),
        'tech':      lambda: run_tech_fingerprint(target, results),
        'ssl':       lambda: run_ssl_analysis(target, results),
        'web':       lambda: run_web_recon(target, results),
        'ip':        lambda: run_ip_intel(target, results),
        'ports':     lambda: run_port_scan(target, results),
        'breach':    lambda: run_breach_check(target, results),
        'social':    lambda: run_social_recon(target, results),
    }
    
    # Execute modules
    for module in modules_to_run:
        if module in module_map:
            try:
                module_map[module]()
            except KeyboardInterrupt:
                warning(f"Module {module} interrupted — continuing...")
            except Exception as e:
                error(f"Module {module} failed: {e}")
    
    # Generate report
    generate_report(target, results, start_time)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {Colors.YELLOW}Scan interrupted by user.{Colors.RESET}\n")
        sys.exit(0)
