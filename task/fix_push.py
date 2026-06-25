#!/usr/bin/env python3
"""Fix the broken push-to-github route"""
import base64

with open('/root/umkm-copilot/app.py', 'r') as f:
    lines = f.readlines()

# Find the route boundaries
start = None
end = None
for i, line in enumerate(lines):
    if "@app.route('/push-to-github'" in line:
        start = i
    if start and "@app.route('/debug/whatsapp')" in line:
        end = i
        break

if start and end:
    print(f"Removing lines {start+1} to {end} (broken route)")
    new_lines = lines[:start] + lines[end:]
    with open('/root/umkm-copilot/app.py', 'w') as f:
        f.writelines(new_lines)
    print(f"Removed {end - start} lines")
else:
    print(f"start={start}, end={end} - markers not found")
