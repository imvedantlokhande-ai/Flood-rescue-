"""
Emergency Notification Service for NGO Dispatch and Flood Warnings.

Supported Channels (configured via NOTIFY_CHANNEL in .env):
- DEMO (default): Formats real-time operational messages and logs to in-memory delivery history
- EMAIL: Transmits automated dispatch dispatches via SMTP (smtplib)
- TELEGRAM: Sends real-time bot alerts with instant acknowledgment links

Strict Rule Compliance:
Includes manual retry loop (up to 3 attempts), delivery status tracking,
and one-click acknowledgment callback URLs.
"""

import os
import sys
import time
import json
import logging
import smtplib
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any

logger = logging.getLogger("FloodNotifier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# In-memory delivery history
DELIVERY_HISTORY: List[Dict[str, Any]] = []


def build_dispatch_message(
    request_data: Dict[str, Any],
    risk_level: str,
    base_url: str = "http://localhost:8000",
) -> Dict[str, str]:
    """
    Format standard emergency alert payload for field responders.
    """
    req_id = request_data.get("id", "UNKNOWN")
    stranded_name = request_data.get("stranded_name", "Unknown Area")
    stranded_node = request_data.get("stranded_node", "N/A")
    pop = request_data.get("population", 0)
    risk_score = request_data.get("risk_score", 0.0)
    rank = request_data.get("priority_rank", 1)
    needs_airlift = request_data.get("needs_airlift", False)
    ngo = request_data.get("ngo_assigned") or {}
    ngo_name = ngo.get("name", "NDRF / District Emergency Response")
    contact = ngo.get("contact", "112 / Emergency Ops")
    distance_km = request_data.get("distance_km", 0.0)
    eta = request_data.get("eta_minutes", 0.0)
    coords = request_data.get("rescue_route_coords", [])
    app_route_url = f"{base_url}/route/{req_id}"
    ack_url = f"{base_url}/api/dispatch/{req_id}/ack"
    timestamp = request_data.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    # Build plain text waypoints and OpenStreetMap URL
    if coords and len(coords) > 0:
        waypoints_str = " -> ".join([f"{c.get('lat', 0.0):.4f},{c.get('lng', 0.0):.4f}" for c in coords])
        target_lat = coords[-1].get("lat", 18.6274)
        target_lng = coords[-1].get("lng", 73.8016)
        osm_url = f"https://www.openstreetmap.org/?mlat={target_lat}&mlon={target_lng}&zoom=15#map=15/{target_lat}/{target_lng}"
    else:
        waypoints_str = "Airlift Direct Grid (Ground roads submerged)"
        target_lat = 18.6274
        target_lng = 73.8016
        osm_url = f"https://www.openstreetmap.org/?mlat={target_lat}&mlon={target_lng}&zoom=15"

    if needs_airlift:
        subject = f"🚨 [CRITICAL AIRLIFT DISPATCH #{rank}] Stranded: {stranded_name}"
        body = (
            f"=====================================================\n"
            f"⚠️ CRITICAL FLOOD EMERGENCY - AIRLIFT / BOAT REQUIRED ⚠️\n"
            f"=====================================================\n"
            f"Request ID       : {req_id}\n"
            f"Priority Rank    : #{rank} (HIGHEST PRIORITY)\n"
            f"Stranded Sector  : {stranded_name} ({stranded_node})\n"
            f"Population       : {pop:,} citizens completely isolated\n"
            f"Flood Threat     : {risk_level} (Hydrologic Risk Score: {risk_score}/100)\n"
            f"Ground Status    : ALL INGRESS / EGRESS ROADS SUBMERGED\n"
            f"Escalation       : Request immediate NDRF Helicopter / Inflatable Zodiac Rescue\n"
            f"Target Location  : {osm_url}\n"
            f"Mission Link     : {app_route_url}\n"
            f"Timestamp        : {timestamp}\n"
            f"-----------------------------------------------------\n"
            f"👉 Acknowledge Mission: {ack_url}\n"
            f"====================================================="
        )
    else:
        subject = f"🚨 [FLOOD DISPATCH #{rank}] Urgent Evacuation: {stranded_name}"
        body = (
            f"=====================================================\n"
            f"🚨 EMERGENCY NGO DISPATCH DISPATCH #{rank} 🚨\n"
            f"=====================================================\n"
            f"Request ID       : {req_id}\n"
            f"Assigned Unit    : {ngo_name}\n"
            f"Emergency Contact: {contact}\n"
            f"Target Sector    : {stranded_name} ({stranded_node})\n"
            f"Population at Risk: {pop:,} residents\n"
            f"Flood Threat     : {risk_level} (Score: {risk_score}/100)\n"
            f"Passable Route   : {distance_km} km (via custom Dijkstra on open roads)\n"
            f"Estimated ETA    : {eta} minutes\n"
            f"Route App Link   : {app_route_url}\n"
            f"Route Waypoints  : {waypoints_str}\n"
            f"OpenStreetMap    : {osm_url}\n"
            f"Timestamp        : {timestamp}\n"
            f"-----------------------------------------------------\n"
            f"👉 ACKNOWLEDGE DISPATCH: {ack_url}\n"
            f"====================================================="
        )

    return {"subject": subject, "body": body, "ack_url": ack_url}


def send_via_smtp(subject: str, body: str, recipient: str) -> bool:
    """Deliver dispatch alert using SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured; falling back to demo log.")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    return True


def send_via_telegram(body: str) -> bool:
    """Deliver dispatch alert to Telegram Bot channel."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured; falling back to demo log.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": body, "parse_mode": "HTML"}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status == 200


def notify_ngo_dispatch(
    request_data: Dict[str, Any],
    risk_level: str = "SEVERE",
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Transmit emergency notification to assigned NGO with automated retries.
    """
    channel = os.getenv("NOTIFY_CHANNEL", "DEMO").upper().strip()
    app_url = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
    msg_dict = build_dispatch_message(request_data, risk_level, base_url=app_url)

    req_id = request_data.get("id", "REQ-UNKNOWN")
    recipient = os.getenv("NOTIFICATION_EMAIL", "dsadons2006@gmail.com")

    delivery_status = "PENDING"
    error_message: Optional[str] = None
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        try:
            if channel == "EMAIL":
                success = send_via_smtp(msg_dict["subject"], msg_dict["body"], recipient)
                if success:
                    delivery_status = "DELIVERED_EMAIL"
                    break
                else:
                    delivery_status = "DEMO_LOGGED"
                    break
            elif channel == "TELEGRAM":
                success = send_via_telegram(msg_dict["body"])
                if success:
                    delivery_status = "DELIVERED_TELEGRAM"
                    break
                else:
                    delivery_status = "DEMO_LOGGED"
                    break
            else:
                # Default DEMO channel: purely in-memory operational dispatch
                logger.info(f"\n[DEMO ALERT DISPATCH #{attempt}]\n{msg_dict['body']}\n")
                delivery_status = "DEMO_LOGGED"
                break
        except Exception as ex:
            error_message = str(ex)
            logger.warning(f"Notification attempt {attempt} failed: {ex}")
            if attempt < max_retries:
                time.sleep(0.5 * attempt)
            else:
                delivery_status = "FAILED"

    log_entry = {
        "request_id": req_id,
        "stranded_node": request_data.get("stranded_node"),
        "channel": channel,
        "delivery_status": delivery_status,
        "attempts": attempt,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject": msg_dict["subject"],
        "error": error_message,
        "ack_url": msg_dict["ack_url"],
    }
    DELIVERY_HISTORY.append(log_entry)
    return log_entry


def get_notification_logs() -> List[Dict[str, Any]]:
    """Return historical notification transmission log."""
    return list(reversed(DELIVERY_HISTORY[-50:]))
