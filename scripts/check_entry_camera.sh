#!/usr/bin/env bash
# T22 — diagnose why CAM-ENTRY (10.1.13.100) stopped sending webhook events
# after 2026-03-11. Run from the PMS-AI host (where the cameras are reachable).
#
# Compares the entry camera vs the exit camera across three signals:
# 1. Network reachability (ping)
# 2. ISAPI deviceInfo (does the camera respond to ISAPI at all?)
# 3. ISAPI HTTP listening config (is the webhook destination still configured?)
#
# Usage: ./check_entry_camera.sh
# Requires: curl, ping. Run as the user that has network access to 10.1.13.0/24.

set -u

ENTRY_IP="10.1.13.100"
EXIT_IP="10.1.13.101"
ENTRY_USER="kloudspot"
ENTRY_PASS="Kloudspot@321"
EXIT_USER="kloudspot1"
EXIT_PASS="Kloudspot@321"

echo "=========================================="
echo "T22 — Entry vs Exit camera diagnostic"
echo "=========================================="

probe() {
    local label="$1" ip="$2" user="$3" pass="$4"
    echo
    echo "── ${label} (${ip}) ──"

    echo -n "  [1/3] ping (3 probes): "
    if ping -n 3 -w 2000 "${ip}" >/dev/null 2>&1 || ping -c 3 -W 2 "${ip}" >/dev/null 2>&1; then
        echo "OK"
    else
        echo "UNREACHABLE — likely cause if entry events have stopped"
    fi

    echo -n "  [2/3] ISAPI /System/deviceInfo: "
    deviceinfo=$(curl -s -m 5 --digest -u "${user}:${pass}" "http://${ip}/ISAPI/System/deviceInfo" 2>/dev/null)
    if echo "${deviceinfo}" | grep -qiE "<deviceName>|<serialNumber>"; then
        echo "OK ($(echo "${deviceinfo}" | grep -oE '<deviceName>[^<]+' | head -1))"
    elif [ -n "${deviceinfo}" ]; then
        echo "RESPONSE BUT MALFORMED — auth issue?"
        echo "  > ${deviceinfo:0:200}"
    else
        echo "NO RESPONSE — camera not serving ISAPI or auth failed"
    fi

    echo -n "  [3/3] ISAPI HTTP-host listener (where ANPR posts to): "
    listener=$(curl -s -m 5 --digest -u "${user}:${pass}" "http://${ip}/ISAPI/Event/notification/httpHosts" 2>/dev/null)
    if echo "${listener}" | grep -qE "<url>"; then
        echo "OK"
        echo "${listener}" | grep -oE '<(url|protocolType|enabled)>[^<]+' | sed 's/^/    /'
    else
        echo "NO LISTENER CONFIGURED — this is likely why webhooks stopped"
    fi
}

probe "ENTRY" "${ENTRY_IP}" "${ENTRY_USER}" "${ENTRY_PASS}"
probe "EXIT"  "${EXIT_IP}"  "${EXIT_USER}"  "${EXIT_PASS}"

echo
echo "=========================================="
echo "Interpretation"
echo "=========================================="
echo "If ENTRY is unreachable but EXIT works → network / cable / power issue at"
echo "  the entry camera."
echo "If ENTRY responds to ISAPI but its httpHosts listener is empty/disabled →"
echo "  the webhook destination got cleared. Reconfigure to point to PMS-AI:"
echo "    http://<PMS-AI-host>:8080/api/v1/events/camera"
echo "  ANPR / vehicleMatchResult event triggers must also be enabled on the"
echo "  camera config."
echo "If ENTRY looks identical to EXIT → re-check PMS-AI's CAMERA_IP_MAP and"
echo "  middleware at app/main.py:71 (drops events from IPs not in the map)."
