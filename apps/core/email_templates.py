"""
apps/core/email_templates.py

Single source of truth for every MediLink HTML email.

Public API
----------
    from apps.core.email_templates import build_email

    html = build_email(
        variant="notification",
        user_name="Sarah",
        title="Ambulance Dispatched",
        message="Your ambulance is on the way. Estimated arrival: 8 minutes.",
        action_url="/requests/abc-123/",
        notification_type="ambulance_dispatched",
        extra_data={"provider": "Mulago EMS", "eta": "8 minutes", "plate": "UAB 123X"},
    )

    html = build_email(
        variant="verification",
        user_name="Alex",
        title="Verify your MediLink account",
        otp="847291",
        verify_url="https://medilink.ug/verify-email?token=xxx",
    )

    html = build_email(
        variant="welcome",
        user_name="James",
        title="Welcome to MediLink",
    )

Variants
--------
    "verification"  — OTP code + magic-link button
    "welcome"       — post-verification onboarding card
    "notification"  — ambulance dispatch, booking, system, and provider alerts

Design: Emergency Medical — Clinical & Urgent
---------------------------------------------
  #FDF2F2  outer background       (warm off-white — clinical calm)
  #FFFFFF  card surface
  #FFF5F5  accent tint panels     (light red wash)
  #C62828  primary red            (emergency red — deep, accessible)
  #E53935  secondary red          (alert red)
  #FFCDD2  border/divider         (rose.shade100)
  #B71C1C  dark red               (headings, strong emphasis)
  #1A1D1F  primary text
  #4B5563  secondary text
  #9CA3AF  muted text
  Inter (via Google Fonts) + system fallback sans-serif
"""

from django.conf import settings

# ── Shared constants ──────────────────────────────────────────────────────────
_FROM_ADDRESS = getattr(settings, "DEFAULT_FROM_EMAIL", "MediLink <alerts@medilink.ug>")
_FRONTEND_URL = getattr(settings, "FRONTEND_URL",       "http://localhost:3000")
_SITE_NAME    = getattr(settings, "SITE_NAME",          "MediLink")
_SITE_URL     = getattr(settings, "SITE_URL",           "https://medilink.ug")

# ── Palette tokens ────────────────────────────────────────────────────────────
_BG           = "#FDF2F2"          # warm off-white
_SURFACE      = "#FFFFFF"
_BORDER       = "#F3E0E0"
_RED          = "#C62828"          # primary — deep emergency red
_RED_MID      = "#E53935"          # secondary — alert red
_RED_LIGHT    = "#FFF5F5"          # tint panels
_RED_BORDER   = "#FFCDD2"          # rose dividers
_RED_DARK     = "#B71C1C"          # headings
_WHITE        = "#FFFFFF"
_TEXT_PRIM    = "#1A1D1F"
_TEXT_SEC     = "#4B5563"
_TEXT_MUTED   = "#9CA3AF"
_CROSS_COLOR  = "#C62828"          # medical cross accent


# ══════════════════════════════════════════════════════════════════════════════
# SHARED CHROME
# ══════════════════════════════════════════════════════════════════════════════

def _wrap(body_html: str) -> str:
    """
    Outer shell shared by every email variant.
    Clinical white card on warm off-white. Red emergency bar at top.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:{_BG};
             font-family:'Inter','Segoe UI',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:{_BG};padding:48px 0 64px;">
    <tr>
      <td align="center" style="padding:0 16px;">

        <!-- ── Card ───────────────────────────────────────────────── -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;
                      background:{_SURFACE};
                      border-radius:16px;
                      overflow:hidden;
                      border:1px solid {_BORDER};
                      box-shadow:0 4px 32px rgba(198,40,40,0.10);">

          <!-- Emergency top bar — pulsing gradient -->
          <tr>
            <td style="height:5px;
                       background:linear-gradient(90deg,{_RED_DARK} 0%,{_RED} 40%,{_RED_MID} 100%);
                       font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- Header: wordmark -->
          <tr>
            <td style="padding:28px 48px 22px;
                       background:{_SURFACE};
                       border-bottom:1px solid {_BORDER};">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="vertical-align:middle;">
                    <table cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <!-- Medical cross badge -->
                        <td style="width:36px;height:36px;
                                   background:linear-gradient(135deg,{_RED},{_RED_MID});
                                   border-radius:10px;
                                   text-align:center;vertical-align:middle;">
                          <span style="color:#fff;font-size:18px;
                                       font-weight:800;line-height:36px;
                                       font-family:'Inter',Arial,sans-serif;">✚</span>
                        </td>
                        <td style="padding-left:10px;vertical-align:middle;">
                          <span style="color:{_RED_DARK};font-size:21px;font-weight:800;
                                       letter-spacing:-0.5px;
                                       font-family:'Inter','Segoe UI',Arial,sans-serif;">
                            Medi<span style="color:{_RED_MID};">Link</span>
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td align="right" style="vertical-align:middle;">
                    <span style="color:{_TEXT_MUTED};font-size:10px;
                                 text-transform:uppercase;letter-spacing:2px;
                                 font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      Emergency Services · Uganda
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── BODY (variant-specific) ─────────────────────────── -->
          {body_html}

          <!-- Footer -->
          <tr>
            <td style="padding:22px 48px 26px;
                       background:{_BG};
                       border-top:1px solid {_BORDER};">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <p style="margin:0 0 3px;color:{_TEXT_MUTED};font-size:11px;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      {_SITE_NAME} &middot; Kampala, Uganda
                    </p>
                    <p style="margin:0;color:{_TEXT_MUTED};font-size:11px;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      &copy; 2026 {_SITE_NAME}. All rights reserved.
                    </p>
                  </td>
                  <td align="right" style="vertical-align:middle;">
                    <a href="{_FRONTEND_URL}"
                       style="color:{_RED};font-size:12px;text-decoration:none;
                              font-weight:600;
                              font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      medilink.ug &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        <!-- /Card -->

        <!-- Emergency hotline strip -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;margin-top:12px;">
          <tr>
            <td style="text-align:center;padding:10px 16px;
                       background:linear-gradient(90deg,{_RED_DARK},{_RED_MID});
                       border-radius:10px;">
              <span style="color:#fff;font-size:12px;font-weight:700;
                           letter-spacing:1px;text-transform:uppercase;
                           font-family:'Inter',Arial,sans-serif;">
                ✚ Emergency Hotline: 0800 100 066 &nbsp;|&nbsp; Available 24/7
              </span>
            </td>
          </tr>
        </table>

      </td>
    </tr>
  </table>

</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
# VARIANT: VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def _verification_body(user_name: str, otp: str, verify_url: str) -> str:
    return f"""
          <!-- Eyebrow + headline -->
          <tr>
            <td style="padding:40px 48px 0;">
              <p style="margin:0 0 8px;color:{_RED};font-size:11px;
                         text-transform:uppercase;letter-spacing:2.5px;
                         font-weight:700;
                         font-family:'Inter','Segoe UI',Arial,sans-serif;">
                ✚ Account Verification
              </p>
              <h1 style="margin:0 0 16px;color:{_RED_DARK};font-size:28px;
                         font-weight:800;line-height:1.2;letter-spacing:-0.5px;
                         font-family:'Inter','Segoe UI',Arial,sans-serif;">
                Confirm your identity.
              </h1>
              <p style="margin:0 0 28px;color:{_TEXT_SEC};font-size:15px;
                        line-height:1.75;
                        font-family:'Inter','Segoe UI',Arial,sans-serif;">
                Hi <span style="color:{_TEXT_PRIM};font-weight:700;">{user_name}</span>
                &mdash; thank you for joining {_SITE_NAME}. Enter the code below
                or click the button to activate your account and access
                emergency services across Uganda.
              </p>
            </td>
          </tr>

          <!-- OTP card -->
          <tr>
            <td style="padding:0 48px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:{_RED_LIGHT};
                            border:1px solid {_RED_BORDER};
                            border-radius:14px;overflow:hidden;">
                <!-- Thin inner accent line -->
                <tr>
                  <td style="height:3px;
                             background:linear-gradient(90deg,{_RED_DARK},{_RED_MID});
                             font-size:0;line-height:0;">&nbsp;</td>
                </tr>
                <tr>
                  <td style="padding:28px 32px;text-align:center;">
                    <p style="margin:0 0 14px;color:{_RED};font-size:11px;
                               text-transform:uppercase;letter-spacing:2.5px;
                               font-weight:700;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      One-time code &mdash; expires in 30 minutes
                    </p>
                    <!-- Digits -->
                    <p style="margin:0;
                               color:{_RED};
                               font-size:56px;font-weight:800;
                               letter-spacing:16px;text-indent:16px;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;
                               line-height:1;">
                      {otp}
                    </p>
                    <!-- Divider -->
                    <table cellpadding="0" cellspacing="0" border="0"
                           style="margin:24px auto 4px;">
                      <tr>
                        <td style="width:48px;height:1px;
                                   background:{_RED_BORDER};font-size:0;">&nbsp;</td>
                        <td style="padding:0 14px;color:{_TEXT_MUTED};font-size:12px;
                                   font-family:'Inter','Segoe UI',Arial,sans-serif;">or</td>
                        <td style="width:48px;height:1px;
                                   background:{_RED_BORDER};font-size:0;">&nbsp;</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Magic-link button -->
          <tr>
            <td style="padding:24px 48px 0;text-align:center;">
              <a href="{verify_url}"
                 style="display:inline-block;
                        background:linear-gradient(135deg,{_RED_DARK} 0%,{_RED_MID} 100%);
                        color:#ffffff;text-decoration:none;
                        padding:16px 52px;border-radius:12px;
                        font-size:15px;font-weight:700;letter-spacing:0.3px;
                        font-family:'Inter','Segoe UI',Arial,sans-serif;
                        box-shadow:0 4px 16px rgba(198,40,40,0.30);">
                ✚&nbsp;&nbsp;Verify My Account
              </a>
            </td>
          </tr>

          <!-- Safety note -->
          <tr>
            <td style="padding:28px 48px 44px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:{_BG};
                            border:1px solid {_BORDER};
                            border-left:3px solid {_RED_BORDER};
                            border-radius:0 10px 10px 0;">
                <tr>
                  <td style="padding:13px 16px;">
                    <p style="margin:0;color:{_TEXT_MUTED};font-size:13px;
                               line-height:1.6;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      Didn&rsquo;t create a {_SITE_NAME} account?
                      You can safely ignore this email. No action is required.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""


# ══════════════════════════════════════════════════════════════════════════════
# VARIANT: WELCOME
# ══════════════════════════════════════════════════════════════════════════════

# (emoji, label, description)
_WELCOME_FEATURES = [
    ("🚑", "Request an Ambulance",   "One-tap access to verified ambulance providers near you"),
    ("📍", "Real-Time Tracking",     "Live location tracking so you know exactly when help arrives"),
    ("🏥", "Choose Your Hospital",   "Specify your preferred destination hospital before dispatch"),
    ("⭐", "Rate Providers",         "Help others by rating your experience after every trip"),
    ("📋", "First-Aid Guides",       "Access CPR instructions and emergency guides while you wait"),
    ("🔔", "Instant Alerts",         "Get real-time status updates at every stage of your request"),
]


def _welcome_body(user_name: str) -> str:
    feature_rows = ""
    for i, (emoji, label, desc) in enumerate(_WELCOME_FEATURES):
        mb = "margin-bottom:8px;" if i < len(_WELCOME_FEATURES) - 1 else ""
        feature_rows += f"""
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:{_SURFACE};border-radius:12px;
                            border:1px solid {_BORDER};{mb}">
                <tr>
                  <td style="width:60px;padding:14px 0 14px 16px;vertical-align:middle;">
                    <div style="width:38px;height:38px;
                                background:{_RED_LIGHT};
                                border-radius:10px;text-align:center;
                                font-size:17px;line-height:38px;
                                border:1px solid {_RED_BORDER};">
                      {emoji}
                    </div>
                  </td>
                  <td style="padding:14px 12px;vertical-align:middle;">
                    <p style="margin:0 0 2px;color:{_TEXT_PRIM};font-size:13px;
                               font-weight:700;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      {label}
                    </p>
                    <p style="margin:0;color:{_TEXT_SEC};font-size:12px;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;
                               line-height:1.5;">
                      {desc}
                    </p>
                  </td>
                  <td style="padding:14px 16px 14px 0;vertical-align:middle;
                             text-align:right;">
                    <span style="color:{_RED_BORDER};font-size:16px;">&rarr;</span>
                  </td>
                </tr>
              </table>"""

    return f"""
          <!-- Headline -->
          <tr>
            <td style="padding:40px 48px 8px;">
              <p style="margin:0 0 8px;color:{_RED};font-size:11px;
                         text-transform:uppercase;letter-spacing:2.5px;
                         font-weight:700;
                         font-family:'Inter','Segoe UI',Arial,sans-serif;">
                ✚ Welcome Aboard
              </p>
              <h1 style="margin:0 0 14px;color:{_RED_DARK};font-size:28px;
                         font-weight:800;line-height:1.2;letter-spacing:-0.5px;
                         font-family:'Inter','Segoe UI',Arial,sans-serif;">
                You&rsquo;re in,
                <span style="color:{_RED};">{user_name}.</span>
              </h1>
              <p style="margin:0 0 24px;color:{_TEXT_SEC};font-size:15px;
                        line-height:1.75;
                        font-family:'Inter','Segoe UI',Arial,sans-serif;">
                Your account is verified and active. When every second counts,
                {_SITE_NAME} connects you to the nearest available ambulance
                across Uganda — instantly.
              </p>
            </td>
          </tr>

          <!-- Urgent tip panel -->
          <tr>
            <td style="padding:0 48px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:linear-gradient(135deg,{_RED_DARK},{_RED_MID});
                            border-radius:12px;overflow:hidden;">
                <tr>
                  <td style="padding:16px 20px;">
                    <p style="margin:0;color:#fff;font-size:14px;font-weight:700;
                               font-family:'Inter',Arial,sans-serif;
                               letter-spacing:0.2px;">
                      🚨 In a life-threatening emergency, always call
                      <span style="font-size:16px;">0800 100 066</span> first.
                    </p>
                    <p style="margin:4px 0 0;color:rgba(255,255,255,0.80);font-size:12px;
                               font-family:'Inter',Arial,sans-serif;">
                      MediLink is available 24/7 for non-critical and critical transport needs.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Feature cards -->
          <tr>
            <td style="padding:0 48px;">
              {feature_rows}
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td style="padding:28px 48px 44px;text-align:center;">
              <a href="{_FRONTEND_URL}"
                 style="display:inline-block;
                        background:linear-gradient(135deg,{_RED_DARK} 0%,{_RED_MID} 100%);
                        color:#ffffff;text-decoration:none;
                        padding:16px 56px;border-radius:12px;
                        font-size:15px;font-weight:700;letter-spacing:0.3px;
                        font-family:'Inter','Segoe UI',Arial,sans-serif;
                        box-shadow:0 4px 16px rgba(198,40,40,0.30);">
                Open MediLink &nbsp;&rarr;
              </a>
              <p style="margin:14px 0 0;color:{_TEXT_MUTED};font-size:11px;
                        letter-spacing:1.5px;text-transform:uppercase;
                        font-family:'Inter','Segoe UI',Arial,sans-serif;">
                medilink.ug
              </p>
            </td>
          </tr>"""


# ══════════════════════════════════════════════════════════════════════════════
# VARIANT: NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

# (emoji, accent_hex) — all tuned for medical/emergency context
_NOTIF_META: dict[str, tuple[str, str]] = {
    # Ambulance / dispatch lifecycle
    "ambulance_requested":    ("🚑", "#C62828"),   # deep red
    "ambulance_dispatched":   ("🚨", "#D32F2F"),   # urgent red
    "ambulance_en_route":     ("📍", "#E64A19"),   # deep orange
    "ambulance_arrived":      ("✅", "#2E7D32"),   # green — relief
    "ambulance_completed":    ("🏁", "#1B5E20"),   # dark green
    "ambulance_cancelled":    ("❌", "#B71C1C"),   # dark red
    "ambulance_no_show":      ("⚠️", "#F57F17"),   # amber warning

    # Provider
    "provider_approved":      ("✅", "#2E7D32"),
    "provider_rejected":      ("🚫", "#C62828"),
    "provider_suspended":     ("⛔", "#B71C1C"),
    "new_booking_request":    ("📋", "#1565C0"),   # blue — info

    # Driver
    "driver_verified":        ("🪪", "#2E7D32"),
    "driver_suspended":       ("⛔", "#B71C1C"),
    "shift_started":          ("🟢", "#2E7D32"),
    "shift_ended":            ("🔴", "#C62828"),

    # Ratings / reviews
    "new_review":             ("⭐", "#F9A825"),   # gold
    "review_response":        ("💬", "#4527A0"),   # deep purple

    # Account / system
    "account_verified":       ("🔐", "#1565C0"),
    "account_suspended":      ("⚠️", "#C62828"),
    "password_changed":       ("🔑", "#6A1B9A"),
    "admin_note":             ("📋", "#37474F"),
    "system_alert":           ("🔔", "#37474F"),
}
_NOTIF_DEFAULT = ("🔔", "#C62828")


def _hex_to_light_bg(accent: str) -> str:
    _tint_map = {
        "#C62828": "#FFF5F5",
        "#D32F2F": "#FFF5F5",
        "#B71C1C": "#FFF5F5",
        "#E64A19": "#FFF3E0",
        "#F57F17": "#FFFDE7",
        "#2E7D32": "#F1F8E9",
        "#1B5E20": "#F1F8E9",
        "#1565C0": "#E3F2FD",
        "#4527A0": "#EDE7F6",
        "#6A1B9A": "#F3E5F5",
        "#F9A825": "#FFFDE7",
        "#37474F": "#ECEFF1",
    }
    return _tint_map.get(accent, "#FFF5F5")


def _hex_to_border(accent: str) -> str:
    _border_map = {
        "#C62828": "#FFCDD2",
        "#D32F2F": "#FFCDD2",
        "#B71C1C": "#FFCDD2",
        "#E64A19": "#FFCCBC",
        "#F57F17": "#FFF9C4",
        "#2E7D32": "#C8E6C9",
        "#1B5E20": "#C8E6C9",
        "#1565C0": "#BBDEFB",
        "#4527A0": "#D1C4E9",
        "#6A1B9A": "#E1BEE7",
        "#F9A825": "#FFF9C4",
        "#37474F": "#CFD8DC",
    }
    return _border_map.get(accent, "#FFCDD2")


def _notification_body(
    *,
    user_name: str,
    title: str,
    message: str,
    action_url: str,
    notification_type: str,
    extra_data: dict,
) -> str:
    emoji, accent = _NOTIF_META.get(notification_type, _NOTIF_DEFAULT)
    type_label    = notification_type.replace("_", " ").title()
    badge_bg      = _hex_to_light_bg(accent)
    badge_border  = _hex_to_border(accent)

    # ── Optional CTA ─────────────────────────────────────────────────────────
    cta_block = ""
    if action_url:
        cta_block = f"""
              <tr>
                <td style="padding:24px 0 0;text-align:center;">
                  <a href="{action_url}"
                     style="display:inline-block;
                            background:linear-gradient(135deg,{accent},{accent}cc);
                            color:#ffffff;text-decoration:none;
                            padding:14px 40px;border-radius:12px;
                            font-size:14px;font-weight:700;letter-spacing:0.2px;
                            font-family:'Inter','Segoe UI',Arial,sans-serif;
                            box-shadow:0 4px 12px rgba(0,0,0,0.15);">
                    View Details &nbsp;&rarr;
                  </a>
                </td>
              </tr>"""

    # ── Optional extra-data rows ──────────────────────────────────────────────
    extras_rows = ""
    useful = {
        k: v for k, v in extra_data.items()
        if k in ("provider", "eta", "plate", "hospital", "driver", "amount", "reason") and v
    }
    if useful:
        inner = "".join(
            f"""
                  <tr>
                    <td style="padding:10px 0;border-bottom:1px solid {_BORDER};
                               color:{_TEXT_MUTED};font-size:12px;
                               text-transform:capitalize;letter-spacing:0.3px;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      {k.replace("_", " ")}
                    </td>
                    <td style="padding:10px 0;border-bottom:1px solid {_BORDER};
                               text-align:right;color:{_TEXT_PRIM};font-size:13px;
                               font-weight:700;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      {v}
                    </td>
                  </tr>"""
            for k, v in useful.items()
        )
        extras_rows = f"""
              <tr>
                <td style="padding:20px 0 0;">
                  <table width="100%" cellpadding="0" cellspacing="0" border="0"
                         style="border-top:1px solid {_BORDER};">
                    {inner}
                  </table>
                </td>
              </tr>"""

    return f"""
          <!-- Eyebrow + headline -->
          <tr>
            <td style="padding:40px 48px 0;">
              <!-- Type badge -->
              <div style="display:inline-block;
                          background:{badge_bg};
                          border:1px solid {badge_border};
                          border-radius:20px;
                          padding:5px 14px;
                          margin-bottom:18px;">
                <span style="color:{accent};font-size:11px;font-weight:700;
                             text-transform:uppercase;letter-spacing:1.5px;
                             font-family:'Inter','Segoe UI',Arial,sans-serif;">
                  {emoji}&nbsp;&nbsp;{type_label}
                </span>
              </div>

              <p style="margin:0 0 4px;color:{_TEXT_SEC};font-size:14px;
                        font-family:'Inter','Segoe UI',Arial,sans-serif;">
                Hi <span style="color:{_TEXT_PRIM};font-weight:700;">{user_name}</span>,
              </p>
              <h1 style="margin:0;color:{_RED_DARK};font-size:24px;
                         font-weight:800;line-height:1.25;letter-spacing:-0.4px;
                         font-family:'Inter','Segoe UI',Arial,sans-serif;">
                {title}
              </h1>
            </td>
          </tr>

          <!-- Message panel — left accent stripe -->
          <tr>
            <td style="padding:18px 48px 0;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:{_RED_LIGHT};
                            border:1px solid {_RED_BORDER};
                            border-left:4px solid {accent};
                            border-radius:0 12px 12px 0;">
                <tr>
                  <td style="padding:16px 18px;">
                    <p style="margin:0;color:{_TEXT_SEC};font-size:15px;
                               line-height:1.75;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      {message}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Extra data + CTA -->
          <tr>
            <td style="padding:0 48px 36px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {extras_rows}
                {cta_block}
              </table>
            </td>
          </tr>

          <!-- Emergency reminder -->
          <tr>
            <td style="padding:0 48px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background:{_BG};border:1px solid {_BORDER};
                            border-left:3px solid {_RED_BORDER};
                            border-radius:0 10px 10px 0;">
                <tr>
                  <td style="padding:12px 16px;">
                    <p style="margin:0;color:{_TEXT_MUTED};font-size:12px;
                               line-height:1.6;
                               font-family:'Inter','Segoe UI',Arial,sans-serif;">
                      For life-threatening emergencies call
                      <span style="color:{_RED};font-weight:700;">0800 100 066</span>
                      immediately. You are receiving this because you have an
                      active {_SITE_NAME} account.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def build_email(variant: str, **kwargs) -> str:
    """
    Build a complete HTML email string.

    variant="verification"
        user_name:  str
        otp:        str
        verify_url: str

    variant="welcome"
        user_name: str

    variant="notification"
        user_name:         str
        title:             str
        message:           str
        notification_type: str
        action_url:        str   (optional, pass "" to omit button)
        extra_data:        dict  (optional keys: provider, eta, plate,
                                  hospital, driver, amount, reason)
    """
    if variant == "verification":
        body = _verification_body(
            user_name=kwargs["user_name"],
            otp=kwargs["otp"],
            verify_url=kwargs["verify_url"],
        )
    elif variant == "welcome":
        body = _welcome_body(
            user_name=kwargs["user_name"],
        )
    elif variant == "notification":
        body = _notification_body(
            user_name=kwargs["user_name"],
            title=kwargs["title"],
            message=kwargs["message"],
            action_url=kwargs.get("action_url", ""),
            notification_type=kwargs.get("notification_type", "system_alert"),
            extra_data=kwargs.get("extra_data", {}),
        )
    else:
        raise ValueError(f"Unknown email variant: {variant!r}")

    return _wrap(body)