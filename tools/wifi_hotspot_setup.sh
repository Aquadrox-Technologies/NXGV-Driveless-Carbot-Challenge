#!/usr/bin/env bash
# ==============================================================================
# RISA-Bot Wi-Fi Hotspot Setup & Manager for RDK X5 (NetworkManager)
# ==============================================================================
# Creates an independent Wi-Fi Access Point (Hotspot) on the robot so devices
# can connect directly and view the dashboard (http://192.168.4.1:8080)
# without needing an external Wi-Fi router.
#
# Usage:
#   sudo ./wifi_hotspot_setup.sh start [SSID] [PASSWORD]
#   sudo ./wifi_hotspot_setup.sh stop
#   sudo ./wifi_hotspot_setup.sh status
# ==============================================================================

set -e

CON_NAME="RISA-HOTSPOT"
DEFAULT_SSID="RISA-BOT-3"
DEFAULT_PASS="sunriserisabot3"
HOTSPOT_IP="192.168.4.1"

ACTION="${1:-status}"
SSID="${2:-$DEFAULT_SSID}"
PASSWORD="${3:-$DEFAULT_PASS}"

# Find wireless interface
IFACE=$(nmcli device status | grep wifi | awk '{print $1}' | head -n 1)
if [ -z "$IFACE" ]; then
    IFACE="wlan0"
fi

case "$ACTION" in
    start)
        echo "[*] Initializing Wi-Fi Hotspot on interface: $IFACE"
        echo "    SSID:     $SSID"
        echo "    Password: $PASSWORD"
        echo "    Robot IP: $HOTSPOT_IP"

        # Remove old hotspot connection if it exists
        if nmcli connection show "$CON_NAME" >/dev/null 2>&1; then
            echo "[*] Re-configuring existing connection '$CON_NAME'..."
            nmcli connection delete "$CON_NAME" >/dev/null 2>&1 || true
        fi

        # Create NetworkManager AP profile
        nmcli connection add type wifi ifname "$IFACE" con-name "$CON_NAME" autoconnect no ssid "$SSID"
        nmcli connection modify "$CON_NAME" 802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6
        nmcli connection modify "$CON_NAME" 802-11-wireless-security.key-mgmt wpa-psk 802-11-wireless-security.psk "$PASSWORD"
        # Apple iOS compatibility: enforce strict WPA2-PSK (RSN with AES/CCMP)
        nmcli connection modify "$CON_NAME" 802-11-wireless-security.proto rsn
        nmcli connection modify "$CON_NAME" 802-11-wireless-security.pairwise ccmp
        nmcli connection modify "$CON_NAME" 802-11-wireless-security.group ccmp
        nmcli connection modify "$CON_NAME" ipv4.method shared ipv4.addresses "$HOTSPOT_IP/24"
        nmcli connection modify "$CON_NAME" ipv6.method ignore

        # Activate Hotspot
        echo "[*] Activating Hotspot..."
        nmcli connection up "$CON_NAME"

        echo "=========================================================="
        echo " [SUCCESS] Hotspot is ACTIVE!"
        echo " Connect your phone/laptop to Wi-Fi: $SSID"
        echo " Password: $PASSWORD"
        echo " Web Dashboard URL: http://$HOTSPOT_IP:8080"
        echo "=========================================================="
        ;;

    stop)
        echo "[*] Deactivating Hotspot '$CON_NAME'..."
        if nmcli connection show --active | grep -q "$CON_NAME"; then
            nmcli connection down "$CON_NAME"
        fi
        echo "[*] Re-connecting to saved Wi-Fi router network..."
        nmcli device connect "$IFACE" || true
        echo "[OK] Returned to normal client Wi-Fi mode."
        ;;

    status)
        echo "=== RISA-Bot Hotspot Status ==="
        if nmcli connection show --active | grep -q "$CON_NAME"; then
            echo "Status:   ACTIVE (Broadcasting)"
            echo "SSID:     $(nmcli -g 802-11-wireless.ssid connection show "$CON_NAME" 2>/dev/null || echo "$SSID")"
            echo "Robot IP: $HOTSPOT_IP"
            echo "Dashboard: http://$HOTSPOT_IP:8080"
        else
            echo "Status:   INACTIVE (Connected to normal Wi-Fi / Offline)"
        fi
        ;;

    *)
        echo "Usage: sudo $0 {start|stop|status} [SSID] [PASSWORD]"
        exit 1
        ;;
esac
