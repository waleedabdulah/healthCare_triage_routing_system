"""
Email service: generates a PDF appointment receipt and sends it via SMTP.
If SMTP credentials are not configured the function logs a warning and returns
without raising — booking still succeeds without email.
"""
import io
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

from fpdf import FPDF

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


# ── PDF receipt ───────────────────────────────────────────────────────────────

def _build_pdf(appt: dict) -> bytes:
    """Return a styled PDF receipt as bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Header bar ────────────────────────────────────────────────────────────
    pdf.set_fill_color(26, 86, 219)          # blue-700
    pdf.rect(0, 0, 210, 28, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, "CITY HOSPITAL", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(10, 19)
    pdf.cell(0, 6, "Appointment Confirmation Receipt", ln=True)

    # ── Confirmation badge ────────────────────────────────────────────────────
    pdf.set_xy(140, 6)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(26, 86, 219)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(60, 16, appt["confirmation_code"], border=1, align="C", fill=True)

    # ── Sub-heading ───────────────────────────────────────────────────────────
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(140, 22)
    pdf.cell(60, 6, "Confirmation Code", align="C")

    pdf.ln(10)

    # ── Section: Patient Information ──────────────────────────────────────────
    _section_header(pdf, "Patient Information")
    _row(pdf, "Full Name",    appt["patient_name"])
    _row(pdf, "Email",        appt["patient_email"])
    _row(pdf, "Phone",        appt["patient_phone"])

    pdf.ln(4)

    # ── Section: Appointment Details ──────────────────────────────────────────
    _section_header(pdf, "Appointment Details")
    _row(pdf, "Department",      appt["department"])
    _row(pdf, "Doctor",          appt["doctor_name"])
    _row(pdf, "Specialization",  appt["doctor_specialization"])
    _row(pdf, "Date & Time",     appt["slot_label"])
    _row(pdf, "Status",          "Pending Email Confirmation")

    pdf.ln(4)

    # ── Instructions box ──────────────────────────────────────────────────────
    pdf.set_fill_color(239, 246, 255)        # blue-50
    pdf.set_draw_color(147, 197, 253)        # blue-300
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 64, 175)
    pdf.multi_cell(
        190, 6,
        "IMPORTANT: The confirmation link in your email is valid for 15 minutes only.\n"
        "Please click it immediately to finalise your booking.\n"
        "Present this receipt at the department reception on arrival.",
        border=1, fill=True,
    )

    pdf.ln(6)

    # ── Footer ────────────────────────────────────────────────────────────────
    pdf.set_text_color(150, 150, 150)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_x(10)
    issued = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    pdf.cell(0, 5, f"Issued: {issued}  |  City Hospital Automated Triage System  |  NOT a medical diagnosis", align="C")

    return bytes(pdf.output())


def _section_header(pdf: FPDF, title: str) -> None:
    pdf.set_fill_color(241, 245, 249)       # slate-100
    pdf.set_text_color(30, 41, 59)          # slate-800
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(10)
    pdf.cell(190, 7, f"  {title}", fill=True, ln=True)
    pdf.ln(1)


def _row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)       # slate-500
    pdf.set_x(14)
    pdf.cell(50, 6, label)
    pdf.set_text_color(15, 23, 42)          # slate-950
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(130, 6, str(value), ln=True)


# ── Email sender ──────────────────────────────────────────────────────────────

def send_appointment_email(appt: dict, confirmation_url: str) -> None:
    """
    Send a confirmation email with a PDF receipt attached.
    appt must contain: patient_name, patient_email, doctor_name, slot_label,
                       department, doctor_specialization, patient_phone,
                       confirmation_code, status.
    """
    settings = get_settings()
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP not configured — skipping appointment email")
        return

    to_addr = appt["patient_email"]
    from_addr = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    subject = f"Appointment Confirmation — {appt['department']} | {appt['slot_label']}"

    # ── HTML body ─────────────────────────────────────────────────────────────
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:32px 16px;">
    <table width="560" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

      <!-- Header -->
      <tr><td style="background:#1d4ed8;padding:24px 32px;">
        <p style="margin:0;color:#fff;font-size:20px;font-weight:700;">City Hospital</p>
        <p style="margin:4px 0 0;color:#bfdbfe;font-size:13px;">Appointment Confirmation</p>
      </td></tr>

      <!-- Greeting -->
      <tr><td style="padding:28px 32px 0;">
        <p style="margin:0;font-size:15px;color:#1e293b;">
          Dear <strong>{appt['patient_name']}</strong>,
        </p>
        <p style="margin:12px 0 0;font-size:14px;color:#475569;line-height:1.6;">
          Your appointment request has been received. Please click the button below to
          <strong>confirm your booking</strong>.
        </p>
        <p style="margin:10px 0 0;font-size:13px;color:#b45309;font-weight:600;">
          ⏰ This confirmation link is valid for <strong>15 minutes only</strong>.
          Please confirm immediately.
        </p>
      </td></tr>

      <!-- Confirm button -->
      <tr><td style="padding:24px 32px;">
        <a href="{confirmation_url}"
           style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;
                  padding:13px 32px;border-radius:8px;font-size:15px;font-weight:600;">
          Confirm My Appointment
        </a>
      </td></tr>

      <!-- Details card -->
      <tr><td style="padding:0 32px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">
          <tr><td style="padding:16px 20px;">
            <p style="margin:0 0 12px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Appointment Details</p>
            {_html_row('Department',     appt['department'])}
            {_html_row('Doctor',         appt['doctor_name'])}
            {_html_row('Specialization', appt['doctor_specialization'])}
            {_html_row('Date & Time',    appt['slot_label'])}
            {_html_row('Confirmation',   appt['confirmation_code'])}
          </td></tr>
        </table>
      </td></tr>

      <!-- PDF note -->
      <tr><td style="padding:0 32px 24px;">
        <p style="margin:0;font-size:13px;color:#64748b;">
          A PDF receipt is attached to this email. Please bring it (printed or on your phone)
          to the reception desk on arrival.
        </p>
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#f1f5f9;padding:16px 32px;border-top:1px solid #e2e8f0;">
        <p style="margin:0;font-size:11px;color:#94a3b8;text-align:center;">
          This is an automated message from the City Hospital Triage System.<br>
          This is NOT a medical diagnosis. For emergencies call 115 / 1122.
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

    # ── Build MIME message ────────────────────────────────────────────────────
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    alt = MIMEMultipart("alternative")
    plain = (
        f"Dear {appt['patient_name']},\n\n"
        f"Please confirm your appointment by visiting the link below.\n"
        f"IMPORTANT: This link expires in 15 minutes.\n\n"
        f"{confirmation_url}\n\n"
        f"Department: {appt['department']}\n"
        f"Doctor: {appt['doctor_name']}\n"
        f"Time: {appt['slot_label']}\n"
        f"Confirmation code: {appt['confirmation_code']}\n\n"
        "A PDF receipt is attached.\n\n"
        "City Hospital Automated Triage System"
    )
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)

    # Attach PDF
    try:
        pdf_bytes = _build_pdf(appt)
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"appointment_{appt['confirmation_code']}.pdf",
        )
        msg.attach(pdf_part)
    except Exception as e:
        logger.warning(f"PDF generation failed — sending email without attachment: {e}")

    # Send
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to_addr, msg.as_string())
        logger.info(f"Appointment email sent to {to_addr}")
    except Exception as e:
        logger.error(f"Failed to send appointment email to {to_addr}: {e}")


def _html_row(label: str, value: str) -> str:
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">'
        f'<tr>'
        f'<td style="font-size:13px;color:#64748b;width:40%;">{label}</td>'
        f'<td style="font-size:13px;color:#0f172a;font-weight:600;">{value}</td>'
        f'</tr></table>'
    )


# ── Cancellation email ────────────────────────────────────────────────────────

def send_cancellation_email(appt: dict) -> None:
    """
    Send a cancellation notification email to the patient.
    appt must contain: patient_name, patient_email, department, doctor_name,
                       doctor_specialization, slot_label, confirmation_code.
    """
    settings = get_settings()
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP not configured — skipping cancellation email")
        return

    to_addr   = appt["patient_email"]
    from_addr = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    subject   = f"Appointment Cancelled — {appt['department']} | {appt['slot_label']}"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:32px 16px;">
    <table width="560" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

      <!-- Header -->
      <tr><td style="background:#dc2626;padding:24px 32px;">
        <p style="margin:0;color:#fff;font-size:20px;font-weight:700;">City Hospital</p>
        <p style="margin:4px 0 0;color:#fca5a5;font-size:13px;">Appointment Cancellation Notice</p>
      </td></tr>

      <!-- Greeting -->
      <tr><td style="padding:28px 32px 0;">
        <p style="margin:0;font-size:15px;color:#1e293b;">
          Dear <strong>{appt['patient_name']}</strong>,
        </p>
        <p style="margin:12px 0 0;font-size:14px;color:#475569;line-height:1.6;">
          Your appointment has been <strong>cancelled</strong> as per your request.
          The slot has been released and is now available to other patients.
        </p>
      </td></tr>

      <!-- Details card -->
      <tr><td style="padding:24px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;">
          <tr><td style="padding:16px 20px;">
            <p style="margin:0 0 12px;font-size:12px;font-weight:700;color:#991b1b;text-transform:uppercase;letter-spacing:.05em;">Cancelled Appointment</p>
            {_html_row('Department',    appt['department'])}
            {_html_row('Doctor',        appt['doctor_name'])}
            {_html_row('Specialization',appt['doctor_specialization'])}
            {_html_row('Date & Time',   appt['slot_label'])}
            {_html_row('Ref. Code',     appt['confirmation_code'])}
          </td></tr>
        </table>
      </td></tr>

      <!-- Rebook note -->
      <tr><td style="padding:0 32px 24px;">
        <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6;">
          If you still need medical attention, please use the City Hospital Triage System
          to book a new appointment, or visit the reception desk directly.
        </p>
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#f1f5f9;padding:16px 32px;border-top:1px solid #e2e8f0;">
        <p style="margin:0;font-size:11px;color:#94a3b8;text-align:center;">
          This is an automated message from the City Hospital Triage System.<br>
          This is NOT a medical diagnosis. For emergencies call 115 / 1122.
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>
"""

    plain = (
        f"Dear {appt['patient_name']},\n\n"
        f"Your appointment has been cancelled.\n\n"
        f"Department: {appt['department']}\n"
        f"Doctor: {appt['doctor_name']}\n"
        f"Time: {appt['slot_label']}\n"
        f"Reference code: {appt['confirmation_code']}\n\n"
        "If you still need care, please book a new appointment or visit reception.\n\n"
        "City Hospital Automated Triage System"
    )

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_addr

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(html,  "html"))
    msg.attach(alt)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to_addr, msg.as_string())
        logger.info(f"Cancellation email sent to {to_addr}")
    except Exception as e:
        logger.error(f"Failed to send cancellation email to {to_addr}: {e}")
