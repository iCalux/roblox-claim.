from ..utils import parse_batch_response, make_http_socket, shutdown_socket
from json import loads as json_loads
from zlib import decompress
from datetime import datetime, timezone
from time import time

GROUP_API = "groups.roblox.com"
GROUP_API_ADDR = (__import__("socket").gethostbyname(GROUP_API), 443)

def group_scanner(log_queue, count_queue, proxy_iter, timeout,
                  gid_ranges, gid_cutoff, gid_chunk_size):
    gid_tracked = set()
    gid_list = [
        str(gid).encode()
        for gid_range in gid_ranges
        for gid in range(*gid_range)]
    gid_list_len = len(gid_list)
    gid_list_idx = 0

    if gid_cutoff:
        gid_cutoff = str(gid_cutoff).encode()

    while gid_list_len >= gid_chunk_size:
        proxy_auth, proxy_addr = next(proxy_iter)
        try:
            sock = make_http_socket(
                GROUP_API_ADDR,
                timeout,
                proxy_addr,
                proxy_headers={"Proxy-Authorization": proxy_auth} if proxy_auth else {},
                hostname=GROUP_API)
        except:
            continue
        
        while True:
            gid_chunk = [
                gid_list[(gid_list_idx + n) % gid_list_len]
                for n in range(1, gid_chunk_size + 1)]
            gid_list_idx += gid_chunk_size

            try:
                # Request batch group details.
                sock.send(
                    b"GET /v2/groups?groupIds=" + b",".join(gid_chunk) + b" HTTP/1.1\n"
                    b"Host:groups.roblox.com\n"
                    b"Accept-Encoding:deflate\n"
                    b"\n")
                resp = sock.recv(1048576)
                if resp[:12] != b"HTTP/1.1 200":
                    break
                resp = resp[resp.find(b"\r\n\r\n") + 4:]
                while resp[-1] != 0:
                    resp += sock.recv(1048576)
                owner_status = parse_batch_response(
                    decompress(resp, -15), gid_chunk_size)

                for gid in gid_chunk:
                    if gid not in owner_status:
                        # Group is missing from the batch response.
                        if not gid_cutoff or gid_cutoff > gid:
                            # Group is outside of cut-off range.
                            # Assume it doesn't exist and ignore it in the future.
                            gid_list.remove(gid)
                            gid_list_len -= 1
                        continue
                    
                    if gid not in gid_tracked:
                        if owner_status[gid]:
                            # Group has an owner and this is the first time it's been checked.
                            # Mark it as tracked.
                            gid_tracked.add(gid)
                        else:
                            # Group doesn't have an owner, and this is only the first time it's been checked.
                            # Assume that it's locked or manual-approval only, and ignore it in the future.
                            gid_list.remove(gid)
                            gid_list_len -= 1
                        continue

                    if owner_status[gid]:
                        # Group has an owner and it's been checked previously.
                        # Skip to next group in the batch.
                        continue

                    # Group is marked as tracked and doesn't have an owner.
                    # Request extra details and determine if it's claimable.
                    sock.send(
                        b"GET /v1/groups/" + gid + b" HTTP/1.1\n"
                        b"Host:groups.roblox.com\n"
                        b"\n")
                    resp = sock.recv(1048576)
                    if not resp.startswith(b"HTTP/1.1 200 OK"):
                        break
                    group_info = json_loads(resp[resp.find(b"\r\n\r\n") + 4:])

                    if (not group_info["publicEntryAllowed"]
                        or group_info["owner"]
                        or "isLocked" in group_info):
                        # Group cannot be claimed, ignore it in the future.
                        gid_list.remove(gid)
                        gid_list_len -= 1
                        continue
                    
                    # Send group info back to main process.
                    log_queue.put((datetime.now(timezone.utc), group_info))
                    
                    # Ignore group in the future.
                    gid_list.remove(gid)
                    gid_list_len -= 1

                # Let the counter know <gid_chunk_size> groups were checked.
                count_queue.put((time(), gid_chunk_size))

            except KeyboardInterrupt:
                exit()
            
            except:
                break
            
        shutdown_socket(sock)
