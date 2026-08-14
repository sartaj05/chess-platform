from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "project_documentation"
AUDIT_DATE = date(2026, 8, 14).strftime("%d %B %Y")


def run(text: str, bold: bool = False) -> str:
    props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{props}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def paragraph(text: str = "", style: str | None = None, bullet: bool = False) -> str:
    properties = []
    if style:
        properties.append(f'<w:pStyle w:val="{style}"/>')
    if bullet:
        properties.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>')
    ppr = f"<w:pPr>{''.join(properties)}</w:pPr>" if properties else ""
    return f"<w:p>{ppr}{run(text)}</w:p>"


def table(headers: list[str], rows: list[list[str]], widths: list[int] | None = None) -> str:
    widths = widths or [2400] * len(headers)

    def cell(value: str, width: int, header: bool = False) -> str:
        fill = '<w:shd w:fill="24563B"/>' if header else ""
        color = '<w:color w:val="FFFFFF"/>' if header else ""
        bold = "<w:b/>" if header else ""
        return (
            f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{fill}</w:tcPr>'
            f'<w:p><w:r><w:rPr>{bold}{color}</w:rPr><w:t xml:space="preserve">'
            f"{escape(str(value))}</w:t></w:r></w:p></w:tc>"
        )

    lines = ['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr>']
    lines.append("<w:tr>" + "".join(cell(value, widths[i], True) for i, value in enumerate(headers)) + "</w:tr>")
    for row in rows:
        lines.append("<w:tr>" + "".join(cell(value, widths[i]) for i, value in enumerate(row)) + "</w:tr>")
    lines.append("</w:tbl>")
    return "".join(lines)


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def heading(text: str, level: int = 1) -> str:
    return paragraph(text, f"Heading{level}")


def bullet_list(items: list[str]) -> str:
    return "".join(paragraph(item, bullet=True) for item in items)


def write_docx(filename: str, title: str, subtitle: str, body: list[str]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    document = "".join(
        [
            paragraph(title, "Title"),
            paragraph(subtitle, "Subtitle"),
            paragraph(f"Verified against the repository on {AUDIT_DATE}", "Subtitle"),
            paragraph("Repository: Chess Platform (Django website/API + Flutter Android app)", "Subtitle"),
            page_break(),
            *body,
            paragraph("End of document", "Subtitle"),
        ]
    )
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{document}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/><w:footerReference w:type="default" r:id="rId2" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></w:sectPr></w:body>
</w:document>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
 <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:style>
 <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:jc w:val="center"/><w:spacing w:before="1800" w:after="240"/></w:pPr><w:rPr><w:color w:val="173B2A"/><w:b/><w:sz w:val="42"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="140"/></w:pPr><w:rPr><w:color w:val="55705D"/><w:sz w:val="22"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="300" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:color w:val="173B2A"/><w:b/><w:sz w:val="32"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:keepNext/><w:spacing w:before="220" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:color w:val="24563B"/><w:b/><w:sz w:val="26"/></w:rPr></w:style>
 <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
 <w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="BAC8BA"/><w:left w:val="single" w:sz="4" w:color="BAC8BA"/><w:bottom w:val="single" w:sz="4" w:color="BAC8BA"/><w:right w:val="single" w:sz="4" w:color="BAC8BA"/><w:insideH w:val="single" w:sz="4" w:color="DCE5D8"/><w:insideV w:val="single" w:sz="4" w:color="DCE5D8"/></w:tblBorders></w:tblPr></w:style>
</w:styles>'''
    numbering = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="720"/></w:tabs><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'''
    footer = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:color w:val="68756B"/><w:sz w:val="18"/></w:rPr><w:t>Chess Platform • Project Handover</w:t></w:r></w:p></w:ftr>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    document_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{escape(title)}</dc:title><dc:creator>Chess Platform Engineering</dc:creator><dc:subject>Project handover</dc:subject><dcterms:created xsi:type="dcterms:W3CDTF">2026-08-14T00:00:00Z</dcterms:created></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Chess Platform Documentation Generator</Application></Properties>'''
    with ZipFile(OUTPUT / filename, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/numbering.xml", numbering)
        archive.writestr("word/footer1.xml", footer)
        archive.writestr("word/_rels/document.xml.rels", document_rels)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app)


def feature_document() -> list[str]:
    return [
        heading("1. Executive assessment"),
        paragraph("Chess Platform is a substantial full-stack chess product, not a starter template. The audited repository contains 374 tracked files, 18 Python test modules, three Flutter/widget integration test files, Docker production infrastructure, WebSocket gameplay, asynchronous workers, Stockfish integration, and an Android application. The current automated Django suite contains 84 passing tests."),
        paragraph("The main risk is not absence of chess functionality. It is completing real production configuration, proving behavior on physical devices, finishing several partially wired mobile workflows, and reducing maintainability risk in large Flutter/API files."),
        heading("2. Technology and architecture"),
        table(["Layer", "Implemented technology", "Purpose"], [
            ["Website/backend", "Django 5.2, Django REST Framework", "HTML pages, REST APIs, authentication and domain logic"],
            ["Realtime", "Django Channels, Daphne, WebSockets", "Room lobbies, games, chat, reconnect and presence"],
            ["Background", "Celery worker and beat", "Analysis, notifications, clocks, abandonment and cleanup"],
            ["Data", "PostgreSQL production; SQLite development", "Users, games, moves, puzzles, social and tournaments"],
            ["Cache/broker", "Redis", "Channels, cache, Celery broker and results"],
            ["Chess engine", "Local Stockfish UCI", "Bot play, post-game analysis and fair-play signals"],
            ["Android", "Flutter/Dart, native Kotlin channels", "Offline-first Android client, deep links and sharing"],
            ["Delivery", "Docker, Nginx, GitHub Actions", "Repeatable production and automated quality checks"],
        ], [1700, 2700, 4800]),
        heading("3. Existing backend and website features"),
        heading("3.1 Identity and account security", 2),
        bullet_list([
            "Email registration, OTP/email verification, login/logout and password reset.",
            "JWT access/refresh/verify endpoints for mobile clients.",
            "TOTP two-factor authentication and security settings on the website.",
            "Google and GitHub social-login wiring through django-allauth; provider records still require deployment configuration.",
            "Profiles, avatars, country, biography, public profile, comparison and game history.",
            "Secure mobile token storage and automatic refresh.",
        ]),
        heading("3.2 Chess gameplay", 2),
        bullet_list([
            "Legal server-authoritative standard chess using python-chess.",
            "Same-device, same-PC, LAN, private code rooms, public rooms, rated matchmaking and spectator mode.",
            "WebSocket moves, clocks, presence, reconnect grace, abandonment, resign, abort and draw offers.",
            "Threefold/50-move claims, promotion selection, premoves, takeback requests and rematches.",
            "PGN/FEN import/export, replay, game chat and spectator chat with moderation.",
            "Bullet, blitz, rapid, classical and daily/correspondence time controls.",
            "Separate bullet/blitz/rapid Elo values and expanding matchmaking rating windows.",
            "Progressive bot levels with locally configured Stockfish and built-in fallback behavior.",
        ]),
        heading("3.3 Training, analysis and fair play", 2),
        bullet_list([
            "Visual puzzles, daily puzzle, puzzle ratings, streaks and leaderboard.",
            "Asynchronous Stockfish game review with evaluation graph data, accuracy, classifications, best lines and retry.",
            "Narrative game-review moments and result sharing in Flutter.",
            "Opening explorer and personal opening statistics.",
            "Engine-match risk signals, fair-play review queue, moderator decisions and audit notes; no automatic bans.",
        ]),
        heading("3.4 Community and retention", 2),
        bullet_list([
            "Friends, requests, challenges, direct messages, blocking and reporting.",
            "Notifications and Firebase device registration/delivery worker.",
            "Tournaments with formats, entry, rounds, pairings, results and standings.",
            "Achievements, daily goals, recommendations, live activity, recent champions and comparison.",
            "Responsive website header/footer, dashboard, leaderboards, profiles and history.",
        ]),
        heading("4. Existing Flutter Android features"),
        bullet_list([
            "Registration, email verification, login/logout, secure JWT persistence and refresh.",
            "Offline same-device and bot boards; online rooms, matchmaking and WebSocket gameplay.",
            "Profiles, comparison, history, replay, Stockfish review, puzzles, leaderboard and openings.",
            "Friends, chat, challenges, tournaments and mobile notifications.",
            "Promotion, premoves, draw claims, takebacks, rematch, spectator mode and reconnect UI.",
            "Onboarding lessons for movement, castling, promotion and checkmate, plus First Steps reward.",
            "Themes, sound choices, localization framework, tablet width constraints and semantic board labels.",
            "Deep links, native Android result sharing, background turn reminders and connection-quality indicator.",
            "Signed APK/AAB build scripts, signature validation, checksums and Play Store content drafts.",
        ]),
        page_break(),
        heading("5. Verified pending and missing work"),
        table(["Priority", "Gap", "Why it matters / completion condition"], [
            ["Release blocker", "Real production environment", "Replace every domain/secret/SMTP/database placeholder; configure DNS and trusted HTTPS; run check --deploy."],
            ["Release blocker", "Firebase production setup", "Provide real Android Firebase values and Admin service account; verify foreground/background navigation and delivery on a physical phone."],
            ["Release blocker", "Android signing custody", "Back up release-keystore.jks and passwords in encrypted off-device storage; verify upgrade installation with the same key."],
            ["Release blocker", "Play Store assets", "Capture truthful phone/tablet screenshots; publish privacy policy; complete Data Safety, content rating and release tracks."],
            ["High", "Physical-device evidence", "Run the integration journey on at least one low-memory and one current Android phone; record OS/device/results."],
            ["High", "Windows Flutter SDK repair", "The local Flutter executable currently hangs even for flutter --version; reinstall/repair SDK and rerun tests."],
            ["High", "Offline synchronization UI", "Repository/service logic exists, but no clear user-facing sync queue/conflict-resolution screen is wired into the current home flow."],
            ["High", "Mobile account parity", "Add mobile password reset, TOTP challenge/setup, account export and account deletion workflows."],
            ["High", "Localization completion", "Many Flutter strings remain hard-coded English; move all user text into ARB/localization files and test RTL if supported."],
            ["Medium", "Theme parity", "Online Flutter board is still hard-coded green while offline/replay boards use saved board themes."],
            ["Medium", "Remote observability", "Request timing and logs exist, but a real hosted crash/error service and alert routing still require operator configuration."],
            ["Medium", "API maintainability", "Some API modules and simple_home_page.dart are large and compressed; split clients, repositories, state and feature widgets."],
            ["Medium", "Accessibility verification", "Semantic labels exist, but TalkBack, keyboard navigation, contrast and 200% text scaling need recorded manual tests."],
            ["Optional", "iOS/Desktop clients", "Current mobile release configuration is Android-focused; iOS/desktop are not productized."],
            ["Optional", "Clubs and seasonal leagues", "Not currently implemented; recommended only after production stabilization."],
        ], [1200, 2500, 5500]),
        heading("6. Repository hygiene findings"),
        bullet_list([
            "apps/blog, apps/cms, apps/payments and apps/users contain only ignored Python cache files in this working copy. They are not installed Django applications and may disappear after cache cleanup.",
            "venv, staticfiles, build output, SQLite development data and caches are local/generated and should not be transferred as source.",
            "Migrations are required source history and must never be deleted for normal transfer or deployment.",
            "media, backups and the Android release keystore may contain irreplaceable data. Preserve separately; do not casually clean them.",
        ]),
        heading("7. Recommended next delivery order"),
        table(["Phase", "Outcome"], [
            ["1. Configure", "Production DNS/HTTPS, PostgreSQL, Redis, SMTP, Stockfish, Firebase and OAuth."],
            ["2. Prove", "Restore backup drill; full CI; emulator and physical device matrix; WebSocket/reconnect/load smoke tests."],
            ["3. Publish", "Signed internal APK/AAB, upgrade test, privacy/Data Safety, screenshots, internal then closed Play track."],
            ["4. Complete parity", "Offline sync UI, mobile password reset/2FA/account controls, full localization and online themes."],
            ["5. Extend", "Only then add clubs, seasons, missions and additional social discovery."],
        ], [1800, 7400]),
    ]


def deployment_document() -> list[str]:
    return [
        heading("1. Deployment target"),
        paragraph("Recommended production topology: Nginx -> Django ASGI web container; PostgreSQL database; Redis cache/Channels/Celery; Celery worker and beat; persistent static/media volumes; local Stockfish binary; optional Firebase service credential. The supplied Docker Compose production overlay implements this topology."),
        heading("2. Required infrastructure"),
        bullet_list([
            "Linux server or VM with Docker Engine and Docker Compose v2.",
            "A registered domain with DNS A/AAAA records pointing to the server.",
            "HTTPS certificate terminated at Nginx or an upstream reverse proxy/load balancer.",
            "SMTP account for verification and password-reset email.",
            "Firebase project/service account for real push notifications (optional for basic chess).",
            "Encrypted off-site storage for PostgreSQL/media backups and Android signing material.",
        ]),
        heading("3. Prepare production configuration"),
        paragraph("Copy .env.production.example to .env.production. Never commit the resulting file."),
        table(["Setting", "Required production value"], [
            ["DJANGO_SECRET_KEY", "Long random unique secret"],
            ["DJANGO_ALLOWED_HOSTS", "Production hostname(s), comma separated"],
            ["CSRF_TRUSTED_ORIGINS", "https://your-real-domain"],
            ["DATABASE_URL / POSTGRES_*", "Strong unique credentials matching the Compose database"],
            ["REDIS/CELERY URLs", "Internal Redis service databases"],
            ["EMAIL_*", "Real SMTP host, user, password and sender"],
            ["STOCKFISH_BINARY", "/usr/games/stockfish in the supplied image"],
            ["FIREBASE_*", "Mounted service account path when push is enabled"],
        ], [2800, 6400]),
        heading("4. First production deployment"),
        bullet_list([
            "Copy the repository to the server using Git or a clean transfer archive.",
            "Create .env.production and secrets/firebase-service-account.json outside Git.",
            "Run: .\\scripts\\deploy_production.ps1 -Build (Windows operator) or the documented docker compose command on Linux.",
            "The deployment script validates placeholders, starts services, applies migrations, collects static assets and runs Django deployment checks.",
            "Create the first administrator: docker compose ... exec web python manage.py createsuperuser.",
            "Confirm /health/ returns status ok with database/cache timings.",
            "Confirm HTTP redirects to HTTPS, secure cookies are set and WebSocket upgrade succeeds.",
        ]),
        heading("5. Reverse proxy and network"),
        bullet_list([
            "Expose only ports 80/443 publicly. PostgreSQL and Redis ports are reset/hidden by the production overlay.",
            "Proxy normal HTTP and WebSocket Upgrade/Connection headers to the ASGI service.",
            "Set trusted proxy/forwarded protocol behavior consistently with the TLS termination point.",
            "Restrict SSH, enable host firewall and apply operating-system/container security updates.",
        ]),
        heading("6. Data migration and static files"),
        bullet_list([
            "Run migrations on every deployment before serving changed code.",
            "Never delete migration files to fix production history.",
            "Run collectstatic after frontend/static changes.",
            "Back up PostgreSQL and media before schema changes; test restore regularly.",
        ]),
        heading("7. Celery, Redis and Stockfish"),
        bullet_list([
            "WebSocket rooms need Channels/Redis for multi-process production operation.",
            "Celery worker performs Stockfish reviews and push jobs; beat schedules clocks, abandonment and cleanup.",
            "Verify Stockfish inside the web/worker image and confirm /stockfish/status/.",
            "Limit Stockfish threads/hash per worker to avoid exhausting the host under concurrent analysis.",
        ]),
        heading("8. Monitoring and backup operations"),
        bullet_list([
            "Monitor /health/, container health, disk, memory, CPU, Redis and PostgreSQL connections.",
            "Use X-Request-ID and Server-Timing to correlate slow client requests with logs.",
            "Configure a hosted error/crash platform and alert destinations before public launch.",
            "Schedule scripts/backup_production.ps1, encrypt/copy off-site and perform restore drills with restore_production.ps1.",
            "Define retention for games, chat, reports, device tokens, logs and backups in the published privacy policy.",
        ]),
        page_break(),
        heading("9. Flutter Android production build"),
        bullet_list([
            "Install stable Flutter, Android Studio/SDK Build Tools and Java 17.",
            "Repair the local SDK first if flutter --version does not return.",
            "Run flutter doctor -v and scripts/test_mobile.ps1.",
            "Run emulator integration: scripts/test_mobile.ps1 -Integration -DeviceId emulator-5554.",
            "Repeat with a physical phone device ID and record results.",
            "Use scripts/build_signed_apk.ps1 with secure StorePassword/KeyPassword and the real HTTPS ServerUrl.",
            "The script generates APK/AAB, verifies the APK signature when apksigner exists and prints SHA-256 hashes.",
        ]),
        heading("10. Android signing safety"),
        paragraph("The release keystore is the permanent application identity. Keep at least two encrypted backups in separate locations. Never send it with normal source transfers, never commit key.properties/password files, and never regenerate a different key for updates to an existing Play listing."),
        heading("11. Firebase and deep links"),
        bullet_list([
            "Register application ID com.chessplatform.mobile in Firebase.",
            "Provide build-time Firebase defines and mount the Admin service account for the worker.",
            "Replace the example app-link domain in Android configuration.",
            "Host /.well-known/assetlinks.json containing the release certificate fingerprint.",
            "Test foreground, background and terminated notification navigation on a real phone.",
        ]),
        heading("12. Play Store release procedure"),
        bullet_list([
            "Publish a real HTTPS privacy-policy page and replace the operator-contact placeholder.",
            "Capture truthful screenshots from the production-configured build; phone and tablet where supported.",
            "Complete Data Safety, content rating, target audience and app access forms accurately.",
            "Upload AAB to Internal testing first; test fresh install and upgrade over the previous signed build.",
            "Promote to Closed/Open/Production only after crash, login, push, online game and purchase-free policy checks pass.",
        ]),
        heading("13. Rollback"),
        bullet_list([
            "Keep the prior image tag and deployment environment.",
            "Prefer forward-compatible database migrations; create explicit reverse migrations when feasible.",
            "Restore database/media only after confirming rollback compatibility and taking a pre-restore snapshot.",
            "Android releases cannot be silently rolled back for installed users; publish a higher version code containing the fix.",
        ]),
    ]


def transfer_document() -> list[str]:
    return [
        heading("1. Safest transfer method"),
        paragraph("Preferred: commit intended source changes, then clone the repository on the second PC. This automatically excludes ignored caches and secrets. If Git is unavailable, copy a clean source folder after running the provided dry-run cleanup utility."),
        heading("2. Run the cleanup script"),
        bullet_list([
            "Preview only: python scripts/prepare_project_transfer.py",
            "Delete generated/local artifacts: python scripts/prepare_project_transfer.py --apply",
            "Remove private configuration from this copy only: python scripts/prepare_project_transfer.py --apply --private-config --i-have-a-backup",
            "Remove the SQLite development database only after backup: python scripts/prepare_project_transfer.py --apply --local-data --i-have-a-backup",
            "The default is always dry-run. Read the printed target list before using --apply.",
            "The script never deletes release-keystore.jks, backups or media.",
        ]),
        heading("3. Files that should not be sent as source"),
        table(["Category", "Examples", "Reason / recreate"], [
            ["Python environment", "venv, .venv", "Machine-specific; recreate with python -m venv and pip install."],
            ["Python caches", "__pycache__, *.pyc, .pytest_cache, .ruff_cache", "Generated automatically."],
            ["Django output", "staticfiles, *.log, .coverage, htmlcov", "Generated by collectstatic/tests/runtime."],
            ["Local database", "db.sqlite3", "May contain useful data; protected by default. Back up, then remove explicitly with --local-data when an empty copy is intended."],
            ["Flutter output", "mobile_app/build, .dart_tool, .flutter-plugins-dependencies", "Recreated by flutter pub get/build."],
            ["Android local", ".gradle, local.properties, *.iml, .idea", "SDK/IDE/machine paths; regenerated."],
            ["Private configuration", ".env, .env.production, secrets/", "Contains secrets and machine/domain-specific values."],
            ["Signing password files", "key.properties, *.dpapi", "Secret/machine-bound; transfer only through a secure password channel if necessary."],
        ], [1800, 3400, 4200]),
        heading("4. Files that must be kept"),
        bullet_list([
            "All tracked source under apps, chess_platform, templates, static, mobile_app/lib and Android project source.",
            "All Django migration .py files (except generated __pycache__).",
            "requirements files, pubspec.yaml/pubspec.lock, Gradle wrapper/project configuration, Dockerfiles and Compose files.",
            "Scripts, tests, CI workflow, Nginx configuration, README and project documentation.",
            ".env.example and .env.production.example because they contain safe templates, not real secrets.",
        ]),
        heading("5. Sensitive or irreplaceable items: transfer separately"),
        table(["Item", "Handling"], [
            ["release-keystore.jks", "Encrypt, checksum and transfer separately. Keep backups. Never include in ordinary source ZIP."],
            ["Signing passwords", "Use a password manager/secure channel, not email or source control."],
            ["Production .env", "Recreate or transfer encrypted; rotate secrets if exposure is possible."],
            ["Firebase service account", "Download/transfer securely; rotate/revoke if mishandled."],
            ["Database/media backups", "Encrypt, checksum and restore deliberately; these contain user data."],
        ], [3000, 6200]),
        heading("6. Empty local app folders"),
        paragraph("apps/blog, apps/cms, apps/payments and apps/users currently contain only ignored __pycache__ bytecode and are not listed in INSTALLED_APPS. After cleanup they may be absent. Do not describe them as implemented modules."),
        heading("7. Second-PC setup"),
        bullet_list([
            "Install Git, Python 3.11+, Flutter stable, Android Studio/SDK, Java 17, Docker Desktop and Stockfish as required.",
            "Copy/clone the clean source folder.",
            "Run .\\scripts\\setup_windows.ps1 (or -SkipMobile for website only).",
            "Review the newly created .env; use 10.0.2.2 for Android emulator access or the PC LAN IP for a physical phone.",
            "Run python manage.py migrate, check and pytest -q.",
            "Run flutter doctor -v, flutter pub get, flutter analyze and scripts/test_mobile.ps1.",
            "Start with scripts/run_local.ps1 or scripts/run_local.ps1 -Mobile -ServerUrl http://10.0.2.2:8000.",
        ]),
        heading("8. Verification checklist after transfer"),
        bullet_list([
            "Website opens; static CSS/JS return 200; no missing vendor files.",
            "Register/verify/login/logout and password reset work with configured email backend.",
            "Bot move works with Stockfish or documented fallback; bot victory advances level.",
            "Room code works between browser/emulator; WebSocket moves and reconnect work.",
            "Puzzles are seeded/published; empty puzzle data is not mistaken for a rendering defect.",
            "Flutter installs on emulator/phone and reaches the PC using the correct host address.",
            "Do not copy the old venv, local.properties or build folders to fix setup errors—recreate them.",
        ]),
    ]


def kt_document() -> list[str]:
    return [
        heading("1. KT objective and audience"),
        paragraph("This guide is the presentation script for transferring ownership to another developer, tester or operator. A complete session should explain product behavior, code ownership, runtime dependencies, deployment, common failures, security and the next backlog—not only demonstrate screens."),
        heading("2. 60-minute KT agenda"),
        table(["Time", "Topic", "Demonstration"], [
            ["0-5 min", "Product overview", "Website and Android share the Django API, data and realtime game rules."],
            ["5-15 min", "Architecture", "Django apps, Channels/WebSockets, PostgreSQL, Redis, Celery, Stockfish, Flutter."],
            ["15-25 min", "Core journeys", "Register/login; bot game; private room; online move; puzzle; history/review."],
            ["25-35 min", "Code map", "Models/services/views/consumers; templates/static; Flutter pages/services."],
            ["35-45 min", "Operations", "Environment, migrations, worker/beat, health, logs, backups and restore."],
            ["45-52 min", "Mobile release", "Emulator/phone test, version, signing, APK/AAB and Play tracks."],
            ["52-60 min", "Risks and questions", "Pending production config, SDK issue, secrets, gap backlog and ownership."],
        ], [1200, 2400, 5600]),
        heading("3. One-sentence system explanation"),
        paragraph("Chess Platform is a Django/Channels server that owns identity, chess rules, ratings and shared data, with a responsive server-rendered website and a Flutter Android client using REST plus WebSockets; Redis/Celery handle realtime coordination and background work, while Stockfish supplies bot and analysis capabilities."),
        heading("4. Repository map"),
        table(["Path", "Explain it as"], [
            ["apps/accounts", "Users, email verification, 2FA, profiles and mobile account APIs"],
            ["apps/rooms", "Lobby, room codes, participants and matchmaking"],
            ["apps/games", "Authoritative games, moves, clocks, ratings, chat, WebSocket consumer"],
            ["apps/analysis + stockfish", "Engine jobs, review, openings and UCI execution"],
            ["apps/puzzles", "Puzzle content, attempts, progression and daily puzzle"],
            ["apps/friends/chat/notifications", "Community, messaging, moderation and push"],
            ["apps/tournaments/dashboard/core", "Competition, account summary and product home/health"],
            ["templates + static", "Website UI and locally served assets"],
            ["mobile_app/lib", "Flutter UI, sessions, boards, APIs, push, sync and deep links"],
            ["chess_platform", "Settings, ASGI, routing, Celery and root URLs"],
            ["scripts + Docker/Nginx", "Setup, test, backup, build and deployment operations"],
        ], [3000, 6200]),
        heading("5. Important runtime flows"),
        heading("5.1 Website/API request", 2),
        paragraph("Browser or Flutter -> Nginx -> Django ASGI -> authentication/middleware -> view/API -> service layer -> PostgreSQL/Redis -> response. X-Request-ID and Server-Timing support tracing."),
        heading("5.2 Online game", 2),
        paragraph("Create/join Room -> participant identity -> start Game -> client opens /ws/games/{id}/ -> GameConsumer validates actor and event -> services validate legal move/clock -> database update -> group broadcast -> both clients render authoritative state."),
        heading("5.3 Bot game and review", 2),
        paragraph("Bot game requests Stockfish best move with a configured level and falls back locally where designed. Post-game analysis creates a job; Celery worker runs Stockfish and persists MoveReview/evaluation/accuracy; website/Flutter poll the job and render the story."),
        heading("5.4 Notifications", 2),
        paragraph("Domain action creates Notification -> background task selects PushDevice -> Firebase Admin sends -> Flutter background/foreground handlers display and route. Without Firebase credentials, in-app data remains but real remote delivery is disabled."),
        heading("6. Development demonstration commands"),
        bullet_list([
            ".\\scripts\\setup_windows.ps1",
            ".\\scripts\\run_local.ps1",
            ".\\scripts\\run_local.ps1 -Mobile -ServerUrl http://10.0.2.2:8000",
            "python manage.py migrate; python manage.py check; pytest -q",
            ".\\scripts\\test_mobile.ps1 -Integration -DeviceId emulator-5554",
            "celery -A chess_platform worker -l info and celery -A chess_platform beat -l info when not using Docker",
        ]),
        heading("7. Configuration concepts to explain"),
        bullet_list([
            "Development and production settings are separate; never run production with DEBUG or development secrets.",
            "10.0.2.2 means the host PC from the Android emulator; a physical phone needs the PC LAN IP and matching allowed hosts.",
            "Redis is not optional for full multi-process realtime/background behavior.",
            "Stockfish path differs on Windows and Docker/Linux.",
            "Email, OAuth and Firebase features need external provider credentials even though code exists.",
        ]),
        heading("8. Common failures and diagnosis"),
        table(["Symptom", "Likely cause and action"], [
            ["DisallowedHost 10.0.2.2", "Add 10.0.2.2 to DJANGO_ALLOWED_HOSTS and restart Django."],
            ["Login raises Kombu connection refused", "Celery/Redis unavailable and task was called synchronously; start Redis/worker or use the broker-safe fallback."],
            ["Flutter cannot reach localhost", "Use 10.0.2.2 for emulator or PC LAN IP for phone; bind Django to 0.0.0.0."],
            ["WebSocket disconnects", "Check Redis/Channels, proxy Upgrade headers, auth token, firewall and server URL scheme."],
            ["Puzzle list empty", "No published Puzzle records; seed/import data and verify is_published."],
            ["Stockfish unavailable", "Set STOCKFISH_BINARY, verify executable permissions/path and restart web/worker."],
            ["flutter command hangs", "Local SDK issue; close IDE/stale processes, run doctor, reinstall stable SDK; use CI as clean reference."],
            ["Static vendor 404", "Run collectstatic/fetch assets and confirm static configuration rather than using a CDN."],
        ], [2800, 6400]),
        heading("9. Security rules for the new owner"),
        bullet_list([
            "Never commit .env, Firebase service JSON, signing keys, DPAPI files, database/media backups or user exports.",
            "Never delete migration history or the Android release keystore as cleanup.",
            "Rotate secrets before launch and after any suspected exposure.",
            "Fair-play signals require human review; do not automate bans from the risk score alone.",
            "Backups are not trusted until a complete restore has been tested.",
        ]),
        heading("10. Current known gaps to disclose"),
        bullet_list([
            "Production domains, secrets, SMTP, OAuth and Firebase are templates, not completed external configuration.",
            "Play screenshots/contact/Data Safety and actual Play Console release are pending.",
            "Physical-phone test evidence is pending and local Flutter SDK repair is required.",
            "Mobile offline sync conflict UI, password reset/2FA/account controls and full localization remain incomplete.",
            "Online-board theme parity and hosted crash/alert service configuration remain pending.",
        ]),
        heading("11. KT acceptance checklist"),
        bullet_list([
            "Recipient can start website and mobile app without the presenter.",
            "Recipient can explain REST versus WebSocket responsibilities.",
            "Recipient can locate models, service logic, consumers, templates and Flutter API code.",
            "Recipient can run migrations/tests and diagnose emulator addressing.",
            "Recipient can perform backup/restore rehearsal and explain secret/signing-key custody.",
            "Recipient has the gap backlog and knows which external accounts/credentials are still required.",
        ]),
    ]


def main() -> None:
    write_docx(
        "04_feature_inventory_and_gap_analysis.docx",
        "Feature Inventory and Gap Analysis",
        "Website, Django backend, APIs and Flutter Android application",
        feature_document(),
    )
    write_docx(
        "05_deployment_guide_django_and_flutter.docx",
        "Deployment Guide",
        "Django production infrastructure and Flutter Android/Play Store release",
        deployment_document(),
    )
    write_docx(
        "06_project_transfer_and_cleanup_guide.docx",
        "Project Transfer and Cleanup Guide",
        "What to delete, retain, protect and recreate on another PC",
        transfer_document(),
    )
    write_docx(
        "07_knowledge_transfer_guide.docx",
        "Knowledge Transfer Guide",
        "Architecture, demonstrations, operations, troubleshooting and ownership handover",
        kt_document(),
    )
    for path in sorted(OUTPUT.glob("0[4-7]_*.docx")):
        print(f"Created {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
