"""
Email service — sends alerts via Gmail SMTP.
Only sends ONE email per event, never duplicates.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALERT_EMAIL


def _send(subject: str, body: str, to_email: str = None) -> bool:
    """Core send function — returns True if sent, False if failed."""
    recipient = to_email or ALERT_EMAIL
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("⚠️  Email not configured — skipping")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"SmartAC AI <{GMAIL_ADDRESS}>"
        msg["To"]      = recipient

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient, msg.as_string())

        print(f"✅ Email sent to {recipient}: {subject}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def send_high_risk_alert(
    high_risk_transactions: list,
    anomaly_count: int,
    report_content: str = None,
    client_name: str = "Unknown Client",
) -> bool:
    """
    Send ONE alert email when high risk transactions are detected.
    Includes summary table + report excerpt.
    """
    count = len(high_risk_transactions)
    if count == 0:
        return False

    # Build transaction rows
    rows = ""
    for t in high_risk_transactions[:10]:  # max 10 rows in email
        vendor = t.get("vendor", "Unknown")
        amount = t.get("amount", 0)
        score  = t.get("risk_score", 0)
        exp    = t.get("xai_explanation", "No explanation available")
        rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #2a3a6e">{vendor}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #2a3a6e">£{amount:,.2f}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #2a3a6e;color:#ef4444">{score}/100</td>
            <td style="padding:8px 12px;border-bottom:1px solid #2a3a6e;font-size:12px">{exp}</td>
        </tr>
        """

    # Report excerpt
    report_section = ""
    if report_content:
        excerpt = report_content[:800] + "..." if len(report_content) > 800 else report_content
        report_section = f"""
        <div style="margin-top:24px;padding:16px;background:#1a2550;border-radius:8px">
            <h3 style="color:#4f8ef7;margin:0 0 12px">AI Anomaly Report Excerpt</h3>
            <p style="color:#c8d4f8;font-size:13px;line-height:1.6;white-space:pre-wrap">{excerpt}</p>
        </div>
        """

    body = f"""
    <div style="font-family:Arial,sans-serif;background:#0d1224;color:#ffffff;padding:32px;max-width:700px;margin:0 auto;border-radius:12px">

        <!-- Header -->
        <div style="text-align:center;margin-bottom:32px">
            <h1 style="color:#4f8ef7;margin:0;font-size:28px">🤖 SmartAC</h1>
            <p style="color:#7b8bb2;margin:4px 0 0">AI-Powered Accounting Platform</p>
        </div>

        <!-- Alert banner -->
        <div style="background:#ef444420;border:1px solid #ef4444;border-radius:8px;padding:16px;margin-bottom:24px">
            <h2 style="color:#ef4444;margin:0 0 8px">⚠️ High Risk Alert — {client_name}</h2>
            <p style="color:#fca5a5;margin:0">
                SmartAC has detected <strong>{count} high-risk transaction(s)</strong>
                and <strong>{anomaly_count} anomalie(s)</strong> that require your attention.
            </p>
        </div>

        <!-- Stats row -->
        <div style="display:flex;gap:16px;margin-bottom:24px">
            <div style="flex:1;background:#1a2550;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:32px;font-weight:bold;color:#ef4444">{count}</div>
                <div style="color:#7b8bb2;font-size:13px">High Risk</div>
            </div>
            <div style="flex:1;background:#1a2550;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:32px;font-weight:bold;color:#f59e0b">{anomaly_count}</div>
                <div style="color:#7b8bb2;font-size:13px">Anomalies</div>
            </div>
        </div>

        <!-- Table -->
        <h3 style="color:#4f8ef7;margin:0 0 12px">High Risk Transactions</h3>
        <table style="width:100%;border-collapse:collapse;background:#1a2550;border-radius:8px;overflow:hidden">
            <thead>
                <tr style="background:#2a3a6e">
                    <th style="padding:10px 12px;text-align:left;color:#7b8bb2;font-size:12px">VENDOR</th>
                    <th style="padding:10px 12px;text-align:left;color:#7b8bb2;font-size:12px">AMOUNT</th>
                    <th style="padding:10px 12px;text-align:left;color:#7b8bb2;font-size:12px">RISK</th>
                    <th style="padding:10px 12px;text-align:left;color:#7b8bb2;font-size:12px">REASON</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>

        {report_section}

        <!-- Footer -->
        <div style="margin-top:32px;padding-top:16px;border-top:1px solid #2a3a6e;text-align:center">
            <p style="color:#7b8bb2;font-size:12px;margin:0">
                This alert was generated automatically by SmartAC AI.<br>
                University of Essex × Active Software Platform UK Ltd
            </p>
        </div>
    </div>
    """

    return _send(
        subject=f"🚨 SmartAC Alert: {count} High Risk Transactions Detected — {client_name}",
        body=body,
    )


def send_report_ready(
    report_type: str,
    content: str,
    client_name: str = "Unknown Client",
) -> bool:
    """Send notification when any report is generated."""
    excerpt = content[:600] + "..." if len(content) > 600 else content
    type_label = "Anomaly Report" if report_type == "anomaly_report" else "Client Letter"

    body = f"""
    <div style="font-family:Arial,sans-serif;background:#0d1224;color:#ffffff;padding:32px;max-width:700px;margin:0 auto;border-radius:12px">

        <div style="text-align:center;margin-bottom:32px">
            <h1 style="color:#4f8ef7;margin:0">🤖 SmartAC</h1>
            <p style="color:#7b8bb2;margin:4px 0 0">AI-Powered Accounting Platform</p>
        </div>

        <div style="background:#4f8ef720;border:1px solid #4f8ef7;border-radius:8px;padding:16px;margin-bottom:24px">
            <h2 style="color:#4f8ef7;margin:0 0 8px">✅ {type_label} Ready — {client_name}</h2>
            <p style="color:#93c5fd;margin:0">Your AI-generated report is ready for review.</p>
        </div>

        <div style="background:#1a2550;border-radius:8px;padding:16px">
            <h3 style="color:#4f8ef7;margin:0 0 12px">Report Preview</h3>
            <p style="color:#c8d4f8;font-size:13px;line-height:1.6;white-space:pre-wrap">{excerpt}</p>
        </div>

        <div style="margin-top:32px;padding-top:16px;border-top:1px solid #2a3a6e;text-align:center">
            <p style="color:#7b8bb2;font-size:12px;margin:0">
                Generated by SmartAC AI<br>
                University of Essex × Active Software Platform UK Ltd
            </p>
        </div>
    </div>
    """

    return _send(
        subject=f"📄 SmartAC: {type_label} Ready — {client_name}",
        body=body,
    )
