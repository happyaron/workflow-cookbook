#!/usr/bin/env python3
"""Syntax-check Workflow scripts with node before they are submitted.

  check-script.py                 checks every ```js block in SKILL.md
  check-script.py path/to/wf.js   checks one script as the model would submit it

Placeholders such as /* section 8 */ are stubbed. `export` is stripped and the
body is wrapped in an async function so top-level await and return parse. Exit
status is non-zero when any block fails; the node error (with line and column
relative to the ORIGINAL script) is printed.
"""
import re, subprocess, sys, tempfile, os

GLOBALS = "agent, parallel, pipeline, log, phase, args, budget, workflow"

def wrap(src):
    src = re.sub(r'^\s*export\s+const\s+meta', 'const meta', src, flags=re.M)
    src = re.sub(r'\[/\*[^*]*\*/\]', '[]', src)
    src = re.sub(r'/\*[^*]*\*/', '{}', src)
    return "async function main(" + GLOBALS + ") {\n" + src + "\n}\n"

def check(name, src):
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(wrap(src)); path = f.name
    try:
        r = subprocess.run(['node', '--check', path], capture_output=True, text=True)
    except FileNotFoundError:
        os.unlink(path)
        sys.exit("node is not on PATH; cannot parse-check. Submit the script anyway.")
    finally:
        if os.path.exists(path): os.unlink(path)
    if r.returncode == 0:
        print(f"ok    {name}")
        return True
    msg = r.stderr.replace(path, name)
    msg = re.sub(r':(\d+)\n', lambda m: f":{int(m.group(1)) - 1}\n", msg, count=1)
    print(f"FAIL  {name}\n{msg}")
    return False

def main(argv):
    if argv:
        return all([check(p, open(p).read()) for p in argv])
    here = os.path.dirname(os.path.realpath(__file__))
    text = open(os.path.join(here, 'SKILL.md')).read()
    ok = True
    for i, m in enumerate(re.finditer(r'```js\n(.*?)```', text, flags=re.S), 1):
        head = text[:m.start()]
        title = re.findall(r'^#+ (.*)$', head, flags=re.M)[-1]
        ok &= check(f"block {i} ({title})", m.group(1))
    return ok

if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1:]) else 1)
