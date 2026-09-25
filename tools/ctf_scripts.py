# tools/ctf_scripts.py — JARVIS picks the right tool automatically

CTF_TOOLS = {
    "crypto_rsa":    "python RsaCtfTool.py --publickey key.pub --private",
    "crypto_xor":    "xortool -x -l 16 file.bin",
    "pwn_checksec":  "checksec --file=binary",
    "pwn_rop":       "ROPgadget --binary binary",
    "web_sqli":      "sqlmap -u TARGET --batch --dbs",
    "web_lfi":       "dotdotpwn -m http -h TARGET",
    "forensics_str": "strings -n 8 file | grep -i flag",
    "forensics_steg":"steghide extract -sf image.jpg",
    "rev_strings":   "ghidra_headless . proj -import binary -postScript analyze.py",
    "net_pcap":      "tshark -r capture.pcap -Y 'http' -T fields -e http.file_data",
}