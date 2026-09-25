from pwn import *
import sys

def run_checksec(binary_path):
    try:
        elf = ELF(binary_path, checksec=False)
        return elf.checksec()
    except Exception as e:
        return f"[ERROR] checksec: {e}"

def run_cyclic(length):
    return cyclic(int(length)).decode()

def run_find_offset(pattern):
    return str(cyclic_find(pattern))

def generate_exploit_template(binary_path):
    try:
        elf = ELF(binary_path, checksec=False)
        template = f"""from pwn import *

# Context
context.binary = '{binary_path}'
elf = ELF('{binary_path}')

# Start process
p = process('{binary_path}')

# Exploit
# ... 
p.interactive()
"""
        return template
    except Exception as e:
        return f"[ERROR] template: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 2:
        cmd = sys.argv[1]
        arg = sys.argv[2]
        if cmd == "checksec":
            print(run_checksec(arg))
        elif cmd == "cyclic":
            print(run_cyclic(arg))
        elif cmd == "offset":
            print(run_find_offset(arg))
        elif cmd == "template":
            print(generate_exploit_template(arg))
