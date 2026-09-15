import socket
import threading
import subprocess

SERVER_IP = "192.168.213.79"  # Change to your Server PC IP
PORT = 5000

print("==============================================")
print("               LAN GROUP CHAT - CLIENT")
print("==============================================")
username = input("Enter your username: ").strip()
if not username:
    username = "Anonymous"

notify_choice = input("Enable popup notifications for messages? (y/n): ").strip().lower()
notifications_enabled = notify_choice in ["y", "yes"]

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((SERVER_IP, PORT))
    client.sendall(username.encode())
except Exception:
    print("\nCould not connect to server.")
    print("Check the Server IP, port, and network connection.")
    input("\nPress Enter to exit...")
    exit()

print(f"\nConnected to the room as '{username}'!")
print(f"Notifications: {'ON' if notifications_enabled else 'OFF'}")
print("Commands: Type '/notify' anytime to toggle popups on/off.\n")

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

def receive_messages():
    global notifications_enabled
    while True:
        try:
            raw_data = client.recv(4096).decode()
            if not raw_data:
                break

            print(raw_data, end="")

            if notifications_enabled:
                text = raw_data.strip()
                if ":" in text:
                    sender, content = text.split(":", 1)
                    show_windows_toast(sender.strip(), content.strip())
                elif text:
                    show_windows_toast("LAN Chat", text)

        except Exception:
            print("\nDisconnected from server.")
            break

threading.Thread(target=receive_messages, daemon=True).start()

while True:
    try:
        message = input()
        if not message.strip():
            continue

        if message.strip().lower() == "/notify":
            notifications_enabled = not notifications_enabled
            status = "ENABLED" if notifications_enabled else "DISABLED"
            print(f"[*] Notifications are now {status}.\n")
            continue

        client.sendall((message + "\n").encode())
    except (EOFError, KeyboardInterrupt):
        client.close()
        break