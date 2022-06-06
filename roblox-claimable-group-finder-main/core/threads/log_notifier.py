from ..utils import send_webhook, make_embed

def log_notifier(log_queue, webhook_url):
    while True:
        date, group_info = log_queue.get()

        print(
            f"[{date.strftime('%H:%M:%S')}]",
            f"roblox.com/groups/{group_info['id']:08d}",
            "|", f"{str(group_info['memberCount']).rjust(2)} member{'s' if group_info['memberCount'] != 1 else ' '}",
            "|", group_info["name"])
            
        if webhook_url:
            try:
                send_webhook(
                    webhook_url, embeds=(make_embed(group_info, date),))
            except Exception as err:
                print(f"[log-notifier] webhook error: {err!r}")