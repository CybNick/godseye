# ⚡ GodsEye — Advanced Reconnaissance Intelligence Tool

> *"See Everything. Miss Nothing. Strike First."*

GodsEye is a professional all-in-one footprinting and reconnaissance tool built for ethical hackers, penetration testers, and security researchers. One command. Complete intelligence.

---

## ⚡ What GodsEye Does

```
godseye certifiedhacker.com
```

Automatically runs 11 intelligence modules:

| Module | What It Finds |
|--------|--------------|
| 01 WHOIS | Registrant, expiry, nameservers, privacy gaps |
| 02 DNS | All record types, SPF/DMARC analysis, zone transfer attempt |
| 03 Subdomains | crt.sh + bruteforce + HackerTarget API |
| 04 Emails | Email harvesting + format pattern detection |
| 05 Technology | Server, CMS, frameworks, version numbers, security headers |
| 06 Ports | 25 common ports with risk classification |
| 07 SSL/TLS | Certificate analysis, SAN subdomains, expiry |
| 08 Web Intel | robots.txt, sitemap, sensitive paths, Wayback Machine, dorks |
| 09 IP & Network | Geolocation, ASN, reverse IP, hosting provider |
| 10 Breach Check | HIBP, paste sites, dark web guidance |
| 11 Social Media | LinkedIn, Twitter, GitHub repos, credential leak hunting |

---

## 🚀 Installation (Kali Linux)

```bash
git clone https://github.com/yourusername/godseye.git
cd godseye
chmod +x install.sh
sudo bash install.sh
```

After install, use from anywhere:
```bash
godseye certifiedhacker.com
```

---

## 📖 Usage

### Basic scan (all modules)
```bash
godseye certifiedhacker.com
```

### Fast scan (skip port scanning)
```bash
godseye certifiedhacker.com --skip-ports
```

### Specific modules only
```bash
godseye certifiedhacker.com --modules whois,dns,subdomains
```

### Available module names
```
whois, dns, subdomains, emails, tech, ports, ssl, web, ip, breach, social
```

---

## 📊 Output

GodsEye generates two reports automatically:

- **JSON** — Machine-readable full data dump
- **HTML** — Professional visual intelligence report

```
godseye_certifiedhacker_com_20241215_143022.json
godseye_certifiedhacker_com_20241215_143022.html
```

Open the HTML report:
```bash
firefox godseye_certifiedhacker_com_*.html
```

---

## 🔑 API Keys (Optional — Enhances Results)

Add to your `.bashrc` or `.zshrc` for enhanced results:

```bash
export SHODAN_API_KEY='your_key_here'
export HUNTER_API_KEY='your_key_here'
export HIBP_API_KEY='your_key_here'
export VIRUSTOTAL_API_KEY='your_key_here'
```

Get free API keys at:
- Shodan: shodan.io/register
- Hunter.io: hunter.io (free tier: 25/month)
- HIBP: haveibeenpwned.com/API/Key

---

## 🔧 Manual Companion Commands

GodsEye covers passive + semi-active recon. For deep active scanning, chain these:

```bash
# Deep subdomain enumeration
sublist3r -d target.com -o subdomains.txt

# Email harvesting
theHarvester -d target.com -b all -l 500

# Full port scan
nmap -sV -sC -A -p- target.com -oA nmap_full

# WordPress specific
wpscan --url target.com --enumerate ap,u,tt

# GitHub secret scanning
trufflehog github --org targetcompany

# Credential leak check
python3 dehashed.py -q "@target.com"
```

---

## 📋 Module Details

### Module 03 — Subdomain Enumeration
- **crt.sh** — Certificate transparency logs
- **Wordlist bruteforce** — 80+ common subdomains with threading
- **HackerTarget API** — Additional discovery
- Flags dangerous subdomains: admin, vpn, dev, backup, staging, old, db

### Module 06 — Port Intelligence
Scans 25 high-value ports with risk classification:
- `CRIT` — RDP, SMB, MySQL, MongoDB, Redis, Elasticsearch
- `HIGH` — FTP, SMTP, POP3, IMAP, Oracle DB
- `MED` — SSH, DNS, HTTP, alternate web ports

### Module 08 — Web Intelligence
- robots.txt analysis → reveals hidden directories
- sitemap.xml → complete URL mapping
- Sensitive path probing → .env, .git, backup files, admin panels
- Wayback Machine → historical site data
- Google Dork generation → 16 targeted queries

### Module 10 — Breach Intelligence
- Have I Been Pwned domain search
- Paste site monitoring
- Dark web monitoring recommendations
- Credential stuffing risk assessment

---

## ⚠️ Legal Disclaimer

GodsEye is for **authorized penetration testing and security research only**.

- Only scan systems you own or have explicit written permission to test
- Unauthorized scanning is illegal under the IT Act (India), CFAA (USA), and equivalent laws worldwide
- The tool asks for authorization confirmation before every scan
- You are fully responsible for how you use this tool

---

## 🗺️ Roadmap

- [ ] Shodan API integration (full)
- [ ] theHarvester integration
- [ ] Metasploit module generation
- [ ] Nuclei template generation
- [ ] Slack/Discord report webhooks
- [ ] Continuous monitoring mode
- [ ] Docker container
- [ ] Web UI dashboard

---

## 📁 File Structure

```
godseye/
├── godseye.py      # Main tool (11 modules, ~1500 lines)
├── install.sh      # Kali Linux installer
├── README.md       # This file
└── reports/        # Generated reports (auto-created)
```

---

*Built for ethical hackers. Use responsibly.*
