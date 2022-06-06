from .constants import EMBED_FOOTER_TEXT
from socket import socket
from json import dumps as json_dumps
from base64 import b64encode

ssl_context = __import__("ssl").create_default_context()

def parse_proxy_string(proxy_str):
    proxy_str = proxy_str.rpartition("://")[2]
    auth, _, fields = proxy_str.rpartition("@")
    fields = fields.split(":", 2)

    if len(fields) == 2:
        hostname, port = fields
        if auth:
            auth = "Basic " + b64encode(auth.encode()).decode()
    elif len(fields) == 3:
        hostname, port, auth = fields
        auth = "Basic " + b64encode(auth.encode()).decode()
    else:
        raise Exception(f"Unrecognized proxy format: {proxy_str}")

    addr = (hostname.lower(), int(port))
    return auth, addr

def parse_batch_response(data, limit):
    index = 10
    status_assoc = {}
    for _ in range(limit):
        id_index = data.find(b'"id":', index)
        if id_index == -1:
            break
        index = data.find(b",", id_index + 5)
        group_id = data[id_index + 5 : index]
        index = data.find(b'"owner":', index) + 8
        status_assoc[group_id] = (data[index] == 123)
        index += 25
    return status_assoc

def find_latest_group_id():
    group_id = 0
    sock = make_http_socket(("www.roblox.com", 443))

    def exists(group_id):
        sock.send(f"GET /groups/{group_id}/- HTTP/1.1\nHost:www.roblox.com\n\n".encode())
        resp = sock.recv(1048576)
        return not b"location: https://www.roblox.com/search/groups?keyword=" in resp

    for l in range(8, 0, -1):
        num = int("1" + ("0" * (l - 1)))
        for inc in range(1, 10):
            if inc == 9 or not exists(group_id + (num * inc)):
                group_id += num * (inc - 1)
                break

    return group_id

def send_webhook(url, **kwargs):
    payload = json_dumps(kwargs, separators=(",", ":"))
    hostname, path = url.split("://", 1)[1].split("/", 1)
    https = url.startswith("https")
    if ":" in hostname:
        hostname, port = hostname.split(":", 1)
        port = int(port)
    else:
        port = 443 if https else 80

    sock = make_http_socket((hostname, port), ssl_wrap=https)
    try:
        sock.send(
            f"POST /{path} HTTP/1.1\r\n"
            f"Host: {hostname}\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            f"{payload}".encode())
        sock.recv(4096)
    finally:
        shutdown_socket(sock)

def make_embed(group_info, date):
    return dict(
        title="Found claimable group",
        url=f"https://www.roblox.com/groups/{group_info['id']}",
        fields=[
            dict(name="Group ID", value=group_info["id"]),
            dict(name="Group Name", value=group_info["name"]),
            dict(name="Group Members", value=group_info["memberCount"])
        ],
        footer=dict(
            text=EMBED_FOOTER_TEXT
        ),
        timestamp=date.isoformat()
    )

def make_http_socket(addr, timeout=5, proxy_addr=None, proxy_headers=None,
                     ssl_wrap=True, hostname=None):    
    sock = socket()
    sock.settimeout(timeout)
    sock.connect(proxy_addr or addr)
    
    try:
        if proxy_addr:
            sock.send("".join([
                f"CONNECT {addr[0]}:{addr[1]} HTTP/1.1\r\n",
                *([
                    f"{header}: {value}\r\n"
                    for header, value in proxy_headers.items()
                ] if proxy_headers else []),
                "\r\n"
            ]).encode())
            connect_resp = sock.recv(4096)
            if not (
                connect_resp.startswith(b"HTTP/1.1 200") or\
                connect_resp.startswith(b"HTTP/1.0 200")
            ):
                raise ConnectionRefusedError

        if ssl_wrap:
            sock = ssl_context.wrap_socket(
                sock, False, False, False, hostname or addr[0])
            sock.do_handshake()

        return sock

    except:
        shutdown_socket(sock)
        raise

def shutdown_socket(sock):
    try:
        sock.shutdown(2)
    except OSError:
        pass
    sock.close()

def slice_list(lst, num, total):
    per = int(len(lst)/total)
    chunk = lst[per * num : per * (num + 1)]
    return chunk

def slice_range(r, num, total):
    per = int((r[1]-r[0]+1)/total)
    return (
        r[0] + (num * per),
        r[0] + ((num + 1) * per)
    )