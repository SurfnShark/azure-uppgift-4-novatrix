"""Installera labbappen med Azure Run Command. Kräver inloggad Azure CLI."""
import argparse
import base64
import json
import subprocess
import tempfile
from pathlib import Path


def run_az(*args):
    import shutil
    command = shutil.which('az') or shutil.which('az.cmd')
    if not command:
        raise SystemExit('Installera Azure CLI och logga in först.')
    result = subprocess.run([command, *args], check=True, capture_output=True, text=True, encoding='utf-8')
    return json.loads(result.stdout) if result.stdout.strip() else None


def install_script(account, client):
    app = Path(__file__).resolve().parent.parent / 'app'
    commands = ['set -eu', 'install -d -m 755 /opt/novatrix-api']
    files = {'app.py':'/opt/novatrix-api/app.py', 'storage.py':'/opt/novatrix-api/storage.py',
             'index.html':'/var/www/html/index.html', 'nginx.conf':'/etc/nginx/sites-available/default',
             'novatrix-api.service':'/etc/systemd/system/novatrix-api.service'}
    for source, destination in files.items():
        data = base64.b64encode((app/source).read_bytes()).decode('ascii')
        commands += [f"printf '%s' '{data}' | base64 -d > '{destination}'", f"chmod 644 '{destination}'"]
    environment = f'STORAGE_ACCOUNT={account}\nSTORAGE_CONTAINER=arenden\nMANAGED_IDENTITY_CLIENT_ID={client}\n'
    data = base64.b64encode(environment.encode()).decode('ascii')
    commands += [f"printf '%s' '{data}' | base64 -d > /etc/novatrix-api.env",
                 'chown root:www-data /etc/novatrix-api.env', 'chmod 640 /etc/novatrix-api.env',
                 'systemctl daemon-reload', 'systemctl enable --now novatrix-api',
                 'systemctl restart novatrix-api', 'nginx -t', 'systemctl reload nginx',
                 'systemctl is-active novatrix-api',
                 'curl --fail --silent --retry 5 --retry-delay 1 --retry-all-errors http://127.0.0.1/api/health',
                 "printf '\\nNOVATRIX_INSTALL_OK\\n'"]
    return '\n'.join(commands)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--resource-group', required=True)
    parser.add_argument('--storage-account', required=True)
    parser.add_argument('--vm', default='vm-novatrix-web')
    args = parser.parse_args()
    identity = run_az('identity', 'show', '-g', args.resource_group, '-n', 'id-novatrix-app')
    # VM:n startas för driftsättningen och frigörs även om installationen misslyckas.
    try:
        run_az('vm', 'start', '-g', args.resource_group, '-n', args.vm)
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary)/'install.sh'
            script.write_text(install_script(args.storage_account, identity['clientId']), encoding='utf-8', newline='\n')
            result = run_az('vm', 'run-command', 'invoke', '-g', args.resource_group, '-n', args.vm,
                            '--command-id', 'RunShellScript', '--scripts', '@'+str(script))
            for message in result.get('value', []):
                print(message.get('message', ''))
            if not any('NOVATRIX_INSTALL_OK' in value.get('message', '') for value in result.get('value', [])):
                raise RuntimeError('Installationen kunde inte bekräftas. Läs resultatet från Run Command.')
    finally:
        run_az('vm', 'deallocate', '-g', args.resource_group, '-n', args.vm)
