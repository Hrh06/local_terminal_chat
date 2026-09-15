import socket
import threading
import subprocess
import sys

HOST = "0.0.0.0"
PORT = 5000

print("==============================================")
print("               LAN GROUP CHAT - SERVER")
print("==============================================")
server_name = input("Enter your display name (Host): ").strip()
if not server_name:
    server_name = "Host"

notify_choice = input("Enable popup notifications for messages? (y/n): ").strip().lower()
notifications_enabled = notify_choice in ["y", "yes"]

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()
server.settimeout(1.0)

clients = {}
lock = threading.Lock()
running = True

def show_windows_toast(title, message):
    """Triggers modern Windows toast using PowerShell's official AppID to bypass blocking."""
    clean_msg = message.replace('"', '`"').replace("'", "’")
    clean_title = title.replace('"', '`"').replace("'", "’")

    # Windows requires a registered AppUserModelID, otherwise it silently blocks the toast.
    app_id = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"

    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $template = @"
    <toast>
        <visual>
            <binding template="ToastGeneric">
                <text>{clean_title}</text>
                <text>{clean_msg}</text>
            </binding>
        </visual>
    </toast>
"@
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{app_id}").Show($toast)
    """

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        pass

def broadcast(message, sender_socket=None):
    with lock:
        for client in list(clients.keys()):
            if client != sender_socket:
                try:
                    client.sendall(message.encode())
                except:
                    client.close()
                    clients.pop(client, None)

def handle_client(client, address):
    try:
        username = client.recv(1024).decode().strip()
        if not username:
            username = f"{address[0]}:{address[1]}"
    except Exception:
        client.close()
        return

    with lock:
        clients[client] = username

    join_msg = f"[+] {username} joined the chat.\n"
    print(f"\n{join_msg.strip()}")
    broadcast(f"\n{join_msg}", sender_socket=client)
    if notifications_enabled:
        show_windows_toast("LAN Chat", f"{username} joined the room")

    try:
        while running:
            data = client.recv(1024)
            if not data:
                break

            message = data.decode().strip()
            if message:
                formatted = f"{username}: {message}\n"
                print(formatted.strip())
                broadcast(formatted, sender_socket=client)

                if notifications_enabled:
                    show_windows_toast(username, message)

    except Exception:
        pass

    finally:
        with lock:
            name = clients.pop(client, username)
        client.close()
        leave_msg = f"[-] {name} left the chat.\n"
        print(f"\n{leave_msg.strip()}")
        broadcast(f"\n{leave_msg}")

def server_input():
    global running, notifications_enabled
    while running:
        try:
            message = input()
            if not message.strip():
                continue

            if message.strip().lower() == "/notify":
                notifications_enabled = not notifications_enabled
                status = "ENABLED" if notifications_enabled else "DISABLED"
                print(f"[*] Notifications are now {status}.\n")
                continue

            formatted = f"{server_name}: {message}\n"
            broadcast(formatted)
        except (EOFError, KeyboardInterrupt):
            running = False
            break

print(f"\nServer running on port {PORT}")
print(f"Notifications: {'ON' if notifications_enabled else 'OFF'}")
print("Commands: Type '/notify' anytime to toggle popups on/off.")
print("Press Ctrl+C to stop the server.\n")

threading.Thread(target=server_input, daemon=True).start()

try:
    while running:
        try:
            client, address = server.accept()
            threading.Thread(
                target=handle_client,
                args=(client, address),
                daemon=True
            ).start()
        except socket.timeout:
            continue
except KeyboardInterrupt:
    pass
finally:
    running = False
    print("\nShutting down server...")
    with lock:
        for c in list(clients.keys()):
            try:
                c.close()
            except:
                pass
        clients.clear()
    server.close()
    sys.exit(0)