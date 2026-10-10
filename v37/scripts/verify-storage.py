"""Körs på labbservern med en separat, tillfällig läsidentitet."""
import argparse
import json
import socket
import sys
from urllib.error import HTTPError
sys.path.insert(0, '/opt/novatrix-api')
from storage import ACCOUNT, blob_request


def denied(label, method, name, **kwargs):
    try:
        blob_request(method, name, **kwargs)
    except HTTPError as error:
        assert error.code == 403, (label, error.code)
        print(label + ': NEKAD (403)', flush=True)
        return
    raise AssertionError(label + ': åtkomst var oväntat tillåten')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--reader-client-id', required=True)
    parser.add_argument('--expected-message', required=True)
    args = parser.parse_args()
    ip = socket.gethostbyname(ACCOUNT + '.blob.core.windows.net')
    assert ip.startswith('10.10.2.'), ip
    print('Blob DNS: privat IP i 10.10.2.0/24', flush=True)
    name = args.ticket + '/arende.json'
    status, content = blob_request('GET', name, client_id=args.reader_client_id)
    record = json.loads(content)
    assert status == 200 and record['id'] == args.ticket and record['message'] == args.expected_message
    print('Arende: sparat och aterlast, innehallet stammer', flush=True)
    print('Sparad JSON: '+json.dumps(record, ensure_ascii=True), flush=True)
    if record['attachment']:
        status, attachment = blob_request('GET', record['attachment'], client_id=args.reader_client_id)
        assert status == 200 and attachment == b'Novatrix bilaga - labbtest\n'
        print('Bilaga: sparad och aterlast, innehallet stammer', flush=True)
    denied('Appen laser arende', 'GET', name)
    denied('Appen raderar arende', 'DELETE', name)
    denied('Appen skriver i annan behallare', 'PUT', 'kontroll.txt', data=b'kontroll', container='kontroll')
    print('Alla lagringskontroller godkanda.', flush=True)
