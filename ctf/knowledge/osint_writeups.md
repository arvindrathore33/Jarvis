# OSINT Knowledge Base for JARVIS

## 1. Metadata Analysis
- **Tool:** `exiftool`
- **Pattern:** Always check `License`, `Comment`, `Artist`, and `Software` fields.
- **Example:** In "Information", the flag was hidden in the `License` field as a Base64-encoded string.

## 2. Infrastructure Mapping
- **Tool:** `dns_recon`, `wayback_dump`
- **Pattern:** Forgotten subdomains and historical versions often contain staging environment flags.
- **Example:** "Scavenger Hunt" required checking `/robots.txt`, `/.htaccess`, and `/.DS_Store` to reconstruct the flag.

## 3. Blockchain OSINT
- **Tool:** `dork_gen` (for address search)
- **Pattern:** Publicly traded addresses link back to known malware families and threat reports.
- **Example:** "money-ware" required searching a Bitcoin address to identify the ransomware (Petya).

## 4. Source & Metadata
- **Tool:** `curl_source`, `grep`, `binwalk`
- **Pattern:** Flags are frequently split across multiple file headers or hidden in obfuscated CSS/JS classes.
- **Example:** "Enhance!" flag was hidden in the SVG XML nodes.
