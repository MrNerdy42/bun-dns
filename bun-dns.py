import requests, sys
import os
from typing import Any

class ConfigurationError(Exception):
    pass

class PorkBunResponse():
    def __init__(self, status_code: int, status_text: str | None, data: Any | None):
        self.status_code = status_code
        self.status_text = status_text.lower() if status_text else None
        self.data: Any = data or {}
    def successful(self):
        return self.status_code == 200 and self.status_text == 'success'
    
    def __str__(self):
        return f"HTTP status: {self.status_code} Porkbun API status:{self.status_text}\n{self.data}"

def get_pb_response(res: requests.Response):
    try:
        response_json = res.json()
        status_text = response_json['status']
    except:
        status_text = None
        response_json = None
    return PorkBunResponse(res.status_code, status_text, response_json)

def send_pb_request(url: str, secret_key: str, public_key: str, **data: str):
    req = {
        'secretapikey':secret_key,
        'apikey':public_key,
        **data
    }
    return get_pb_response(requests.post(url, json=req))

def get_previous_public_ip(file: str):
    with open(file, 'r') as cfg:
        return cfg.readline().replace('\n', '')
    
def get_subdomains(file: str):
    with open(file, 'r') as cfg:
        return [l.replace('\n', '') for l in cfg.readlines() if l != '\n']
    
def write_new_public_ip(file: str, ip: str):
    with open(file, 'w') as cfg:
        cfg.write(ip + '\n')

domain: str
subdomain_config_path: str
public_ip_path: str
secret_key: str
public_key: str

try:
    domain = os.environ['BUN_DNS_DOMAIN']
    subdomain_config_path = os.environ['BUN_DNS_SUBDOMAIN_CONFIG_PATH']
    public_ip_path = os.environ['BUN_DNS_PUBLIC_IP_PATH']
    secret_key = os.environ['PORKBUN_SECRET_KEY']
    public_key = os.environ['PORKBUN_PUBLIC_KEY']  
except KeyError as e:
    print(f'Environment variable {e.args[0]} was not found.', file=sys.stderr)
    sys.exit(100)

dns_endpoint = 'https://api.porkbun.com/api/json/v3/dns/editByNameType'
ping_endpoint = 'https://api-ipv4.porkbun.com/api/json/v3/ping'

try:
    ping_response = send_pb_request(ping_endpoint, secret_key, public_key)

    if not ping_response.successful():
        print(ping_response, file=sys.stderr)
        sys.exit(200)

    public_ip = ping_response.data['yourIp']
    print(f'Public IP: {public_ip}')

    previous_ip = get_previous_public_ip(public_ip_path)
    print(f'Previous public IP: {previous_ip}')
    if previous_ip == public_ip:
        print(f'Previous public IP matches current. No updates will be preformed.')
        sys.exit(0)

    subdomains = get_subdomains(subdomain_config_path)
    for sd in subdomains:
        sub_domain_path = '' if sd == '@' else sd
        url = f'{dns_endpoint}/{domain}/A/{sub_domain_path}'
        print(f'Request url: {url}')

        update_response = send_pb_request(url, secret_key, public_key, content=public_ip)
        if not update_response.successful():
            print(update_response, file=sys.stderr)
            sys.exit(300)

        print(update_response)
        print(f'DNS record for {sub_domain_path}{"" if sub_domain_path == "" else "."}{domain} updated successfully.')

    write_new_public_ip(public_ip_path, public_ip)
except Exception as e:
    print('AN UNEXPECTED ERROR OCURRED', sys.stderr)
    print(e)












