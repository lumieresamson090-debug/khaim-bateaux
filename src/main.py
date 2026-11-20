import flet as ft
import requests
import csv
import io
import logging
from datetime import datetime, date, timedelta, timezone
from calendar import monthrange

# ==========================================================
# K-HAIM BATEAU - Flet 0.28.3 / Android
# ==========================================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("khaim")

FIREBASE_URL = "https://k-haime-suivi-48bc4-default-rtdb.firebaseio.com"
PATRON_PIN = "2497"  # ⚠️ À remplacer par Firebase Auth en production.

PRIX_ECO = 25
PRIX_1ERE = 50
PRIX_VIP = 80
PRIX_KG = 2

ROUTES = [
    "Kalemie → Kigoma", "Kigoma → Kalemie",
    "Kalemie → Uvira", "Uvira → Kalemie",
    "Kalemie → Moba", "Moba → Kalemie"
]

DEPENSE_CATEGORIES = [
    "Carburant", "Entretien / réparation", "Salaires équipage",
    "Nourriture", "Frais portuaires", "Autres"
]


class C:
    NAVY = "#0A2342"
    NAVY2 = "#123B64"
    YELLOW = "#FFD60A"
    WHITE = "#FFFFFF"
    GREEN = "#168A52"
    RED = "#D93636"
    GRAY = "#687789"
    BG = "#F3F6FA"
    LIGHT = "#E7EEF8"
    BORDER = "#DCE4EE"


def money(value):
    return f"{value:,.2f} $".replace(",", " ")


def parse_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def main(page: ft.Page):
    page.title = "K-HAIM BATEAU"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = C.BG
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    session = {"equipage": "Non spécifié", "route": ""}

    # FilePicker : instanciation unique, ajout via services (Flet 0.28+)
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def notify(message, color=C.GREEN):
        page.open(
            ft.SnackBar(
                content=ft.Text(message, color=C.WHITE),
                bgcolor=color
            )
        )

    # ---------------- FIREBASE ----------------

    def fb_get(path):
        try:
            response = requests.get(
                f"{FIREBASE_URL}/{path}.json", timeout=15
            )
            response.raise_for_status()
            return response.json() or {}
        except Exception as ex:
            log.warning("Firebase GET %s: %s", path, ex)
            return {}

    def fb_post(path, data):
        try:
            response = requests.post(
                f"{FIREBASE_URL}/{path}.json", json=data, timeout=15
            )
            response.raise_for_status()
            return response.json().get("name")
        except Exception as ex:
            log.warning("Firebase POST %s: %s", path, ex)
            return None

    def fb_put(path, data):
        try:
            response = requests.put(
                f"{FIREBASE_URL}/{path}.json", json=data, timeout=15
            )
            response.raise_for_status()
            return True
        except Exception as ex:
            log.warning("Firebase PUT %s: %s", path, ex)
            return False

    def load_all():
        voyages = fb_get("bateaux/traversees")
        depenses = fb_get("bateaux/depenses")
        return (
            voyages if isinstance(voyages, dict) else {},
            depenses if isinstance(depenses, dict) else {}
        )

    # ---------------- OUTILS RAPPORTS ----------------

    def period_bounds(period):
        today = date.today()
        if period == "Journalier":
            return today, today
        if period == "Hebdomadaire":
            start = today - timedelta(days=today.weekday())
            return start, today
        start = today.replace(day=1)
        end = today.replace(day=monthrange(today.year, today.month)[1])
        return start, end

    def in_period(item_date, start, end):
        d = parse_date(item_date)
        return d is not None and start <= d <= end

    def build_report(period):
        start, end = period_bounds(period)
        voyages, depenses = load_all()

        voyages_list = [
            (key, value) for key, value in voyages.items()
            if isinstance(value, dict) and in_period(value.get("date"), start, end)
        ]
        depenses_list = [
            (key, value) for key, value in depenses.items()
            if isinstance(value, dict) and in_period(value.get("date"), start, end)
        ]

        recettes = sum(float(v.get("recette", 0) or 0) for _, v in voyages_list)
        couts = sum(float(d.get("montant", 0) or 0) for _, d in depenses_list)
        passagers = sum(int(v.get("passagers_total", 0) or 0) for _, v in voyages_list)
        cargo = sum(float(v.get("cargo_kg", 0) or 0) for _, v in voyages_list)
        return {
            "period": period, "start": start, "end": end,
            "voyages": voyages_list, "depenses": depenses_list,
            "recettes": recettes, "depenses_total": couts,
            "benefice": recettes - couts,
            "passagers": passagers, "cargo": cargo
        }

    def report_csv_bytes(report):
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", lineterminator="\n")
        writer.writerow([
            "Type", "Date", "Route / catégorie", "Description",
            "Passagers", "Cargo kg", "Equipage",
            "Recettes USD", "Dépenses USD", "Bénéfice USD"
        ])

        for _, v in report["voyages"]:
            writer.writerow([
                "Traversée", v.get("date", ""), v.get("route", ""),
                "Statut: " + str(v.get("statut", "")),
                v.get("passagers_total", 0), v.get("cargo_kg", 0),
                v.get("equipage", ""),
                v.get("recette", 0), 0, v.get("recette", 0)
            ])

        for _, d in report["depenses"]:
            writer.writerow([
                "Dépense", d.get("date", ""), d.get("categorie", ""),
                d.get("description", ""), 0, 0, d.get("enregistre_par", ""),
                0, d.get("montant", 0), -float(d.get("montant", 0) or 0)
            ])

        writer.writerow([])
        writer.writerow(["RÉSUMÉ", report["start"], report["end"]])
        writer.writerow(["Nombre de traversées", len(report["voyages"])])
        writer.writerow(["Nombre de passagers", report["passagers"]])
        writer.writerow(["Cargo total (kg)", report["cargo"]])
        writer.writerow(["RECETTES USD", report["recettes"]])
        writer.writerow(["DÉPENSES USD", report["depenses_total"]])
        writer.writerow(["BÉNÉFICE NET USD", report["benefice"]])

        return ("\ufeff" + output.getvalue()).encode("utf-8")

    async def export_report(report):
        filename = (
            f"rapport_khaim_{report['period'].lower()}_"
            f"{report['start'].isoformat()}.csv"
        )
        try:
            saved_path = await file_picker.save_file(
                dialog_title="Enregistrer le rapport CSV",
                file_name=filename,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=report_csv_bytes(report)
            )
            if saved_path:
                notify("Rapport CSV enregistré.")
            else:
                notify("Enregistrement annulé.", C.GRAY)
        except Exception as ex:
            log.warning("Export CSV: %s", ex)
            notify(
                "Export impossible. Vérifiez les permissions de stockage.",
                C.RED
            )

    # ---------------- COMPOSANTS UI ----------------

    def header(title, subtitle="", back="/patron"):
        return ft.Container(
            bgcolor=C.NAVY,
            padding=ft.padding.only(top=42, left=16, right=16, bottom=18),
            content=ft.Row(
                controls=[
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, icon_color=C.WHITE,
                        on_click=lambda e: page.go(back)
                    ),
                    ft.Column(
                        [
                            ft.Text(title, color=C.WHITE, size=19,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text(subtitle, color=C.YELLOW, size=11)
                        ],
                        spacing=2, expand=True
                    )
                ]
            )
        )

    def card(label, value, color=C.NAVY, icon=ft.Icons.ANALYTICS):
        return ft.Container(
            expand=True, padding=14, bgcolor=C.WHITE,
            border=ft.border.all(1, C.BORDER), border_radius=14,
            content=ft.Column(
                [
                    ft.Row([
                        ft.Icon(icon, color=color, size=20),
                        ft.Text(label, size=11, color=C.GRAY)
                    ]),
                    ft.Text(value, size=19, weight=ft.FontWeight.BOLD,
                            color=color)
                ],
                spacing=8
            )
        )

    def action_button(label, icon, route, color=C.NAVY):
        return ft.Container(
            expand=True,
            content=ft.ElevatedButton(
                text=label, icon=icon, on_click=lambda e: page.go(route),
                bgcolor=color, color=C.WHITE, height=48,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10)
                )
            )
        )

    # ---------------- LOGIN ----------------

    def view_login():
        pin = ft.TextField(
            label="Code d'accès Patron", password=True, can_reveal_password=True,
            width=280, border_radius=10
        )

        def patron(_):
            if pin.value == PATRON_PIN:
                page.go("/patron")
            else:
                pin.error_text = "Code incorrect"
                page.update()

        return ft.View(
            "/",
            [
                ft.Container(
                    expand=True, bgcolor=C.BG,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            ft.Container(height=25),
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                    size=76, color=C.NAVY),
                            ft.Text("K-HAIM BATEAU", size=28,
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            ft.Text("GESTION MARITIME • LAC TANGANYIKA",
                                    size=10, color=C.GRAY),
                            ft.Container(height=35),
                            ft.ElevatedButton(
                                "ESPACE ÉQUIPAGE", icon=ft.Icons.GROUPS,
                                width=280, height=52, bgcolor=C.YELLOW,
                                color=C.NAVY,
                                on_click=lambda e: page.go("/route")
                            ),
                            ft.Container(height=16),
                            ft.Text("ACCÈS ADMINISTRATEUR",
                                    size=11, color=C.GRAY,
                                    weight=ft.FontWeight.BOLD),
                            pin,
                            ft.ElevatedButton(
                                "ESPACE PATRON",
                                icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                                width=280, height=52, bgcolor=C.NAVY,
                                color=C.WHITE, on_click=patron
                            ),
                            ft.Container(height=25)
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    )
                )
            ],
            bgcolor=C.BG, padding=18
        )

    # ---------------- EQUIPE / ROUTE ----------------

    def view_route():
        route = ft.Dropdown(
            label="Choisir la route",
            options=[ft.dropdown.Option(r) for r in ROUTES],
            width=320
        )
        nom = ft.TextField(label="Nom du chef d'équipage", width=320)

        def start(_):
            if not route.value or not (nom.value or "").strip():
                notify("Choisissez une route et entrez votre nom.", C.RED)
                return
            session["route"] = route.value
            session["equipage"] = nom.value.strip()
            page.go("/embarquement")

        return ft.View(
            "/route",
            [
                header("ESPACE ÉQUIPAGE", "Nouvelle traversée", "/"),
                ft.Container(
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                    size=58, color=C.NAVY),
                            ft.Text("Préparer une traversée", size=19,
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            route, nom,
                            ft.ElevatedButton(
                                "COMMENCER L'EMBARQUEMENT",
                                icon=ft.Icons.PLAY_ARROW,
                                bgcolor=C.YELLOW, color=C.NAVY,
                                width=320, height=52, on_click=start
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=18
                    )
                )
            ],
            bgcolor=C.BG, padding=0
        )

    # ---------------- EMBARQUEMENT ----------------

    def view_embarquement():
        if not session.get("route"):
            page.go("/route")
            return ft.View("/embarquement", [])

        eco = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        premiere = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        vip = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        kg = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        total = ft.Text("0 passagers • 0 kg • 0.00 $",
                        color=C.WHITE, weight=ft.FontWeight.BOLD)

        def refresh():
            e = int(eco.value or 0)
            p = int(premiere.value or 0)
            v = int(vip.value or 0)
            k = int(kg.value or 0)
            total.value = (
                f"{e+p+v} passagers • {k} kg • "
                f"{money(e*PRIX_ECO+p*PRIX_1ERE+v*PRIX_VIP+k*PRIX_KG)}"
            )
            page.update()

        def counter(label, price, control):
            def change(delta):
                n = max(0, int(control.value or 0) + delta)
                control.value = str(n)
                refresh()
            return ft.Container(
                padding=12, bgcolor=C.WHITE, border_radius=12,
                border=ft.border.all(1, C.BORDER),
                content=ft.Row(
                    [
                        ft.Column([
                            ft.Text(label, weight=ft.FontWeight.BOLD,
                                    color=C.NAVY),
                            ft.Text(f"{price} $", size=11, color=C.GRAY)
                        ], expand=True, spacing=2),
                        ft.IconButton(ft.Icons.REMOVE,
                                      on_click=lambda e: change(-1)),
                        control,
                        ft.IconButton(ft.Icons.ADD,
                                      on_click=lambda e: change(1))
                    ]
                )
            )

        def cargo():
            def change(delta):
                kg.value = str(max(0, int(kg.value or 0) + delta))
                refresh()
            return ft.Container(
                padding=12, bgcolor=C.WHITE, border_radius=12,
                border=ft.border.all(1, C.BORDER),
                content=ft.Column([
                    ft.Text("MARCHANDISES / CARGO",
                            weight=ft.FontWeight.BOLD, color=C.NAVY),
                    ft.Text(f"{PRIX_KG} $ / kg", size=11, color=C.GRAY),
                    ft.Row([
                        ft.OutlinedButton("-1", on_click=lambda e: change(-1)),
                        kg,
                        ft.OutlinedButton("+1", on_click=lambda e: change(1)),
                        ft.OutlinedButton("+10", on_click=lambda e: change(10)),
                        ft.OutlinedButton("+50", on_click=lambda e: change(50))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ])
            )

        def finish(_):
            e = int(eco.value or 0)
            p = int(premiere.value or 0)
            v = int(vip.value or 0)
            k = int(kg.value or 0)
            passengers = e + p + v
            if passengers == 0 and k == 0:
                notify("Ajoutez au moins un passager ou du cargo.", C.RED)
                return
            revenue = e*PRIX_ECO + p*PRIX_1ERE + v*PRIX_VIP + k*PRIX_KG
            now = datetime.now(timezone.utc)
            data = {
                "route": session["route"],
                "date": now.strftime("%Y-%m-%d %H:%M:%S"),
                "passagers_eco": e, "passagers_1ere": p,
                "passagers_vip": v, "passagers_total": passengers,
                "cargo_kg": k, "recette": revenue,
                "equipage": session["equipage"], "statut": "Terminé"
            }
            key = fb_post("bateaux/traversees", data)
            if key:
                notify(f"Traversée enregistrée : {money(revenue)}")
                session["route"] = ""
                page.go("/route")
            else:
                notify("Envoi Firebase échoué. Vérifiez Internet.", C.RED)

        return ft.View(
            "/embarquement",
            [
                header(f"ROUTE : {session['route']}",
                       "Enregistrement de la traversée", "/route"),
                ft.Container(
                    padding=14,
                    content=ft.Column(
                        [
                            counter("ÉCO", PRIX_ECO, eco),
                            counter("1ÈRE CLASSE", PRIX_1ERE, premiere),
                            counter("VIP", PRIX_VIP, vip),
                            cargo(),
                            ft.Container(
                                padding=16, bgcolor=C.NAVY, border_radius=12,
                                content=total
                            ),
                            ft.ElevatedButton(
                                "TERMINER ET ENVOYER",
                                icon=ft.Icons.SEND, bgcolor=C.YELLOW,
                                color=C.NAVY, height=54, expand=True,
                                on_click=finish
                            )
                        ],
                        spacing=12, scroll=ft.ScrollMode.AUTO
                    )
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- PATRON DASHBOARD ----------------

    def view_patron():
        voyages, depenses = load_all()
        valid_v = [v for v in voyages.values() if isinstance(v, dict)]
        valid_d = [d for d in depenses.values() if isinstance(d, dict)]
        recettes = sum(float(v.get("recette", 0) or 0) for v in valid_v)
        couts = sum(float(d.get("montant", 0) or 0) for d in valid_d)
        passagers = sum(int(v.get("passagers_total", 0) or 0) for v in valid_v)

        recent = sorted(
            valid_v, key=lambda x: x.get("date", ""), reverse=True
        )[:5]

        recent_controls = []
        for v in recent:
            recent_controls.append(
                ft.Container(
                    padding=12, bgcolor=C.WHITE, border_radius=10,
                    border=ft.border.all(1, C.BORDER),
                    content=ft.Row([
                        ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=C.NAVY),
                        ft.Column([
                            ft.Text(v.get("route", "Route inconnue"),
                                    ft.Container(height=25),
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                    size=76, color=C.NAVY),
                            ft.Text("K-HAIM BATEAU", size=28,
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            ft.Text("GESTION MARITIME • LAC TANGANYIKA",
                                    size=10, color=C.GRAY),
                            ft.Container(height=35),
                            ft.ElevatedButton(
                                "ESPACE ÉQUIPAGE", icon=ft.Icons.GROUPS,
                                width=280, height=52, bgcolor=C.YELLOW,
                                color=C.NAVY,
                                on_click=lambda e: page.go("/route")
                            ),
                            ft.Container(height=16),
                            ft.Text("ACCÈS ADMINISTRATEUR",
                                    size=11, color=C.GRAY,
                                    weight=ft.FontWeight.BOLD),
                            pin,
                            ft.ElevatedButton(
                                "ESPACE PATRON",
                                icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                                width=280, height=52, bgcolor=C.NAVY,
                                color=C.WHITE, on_click=patron
                            ),
                            ft.Container(height=25)
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    )
                )
            ],
            bgcolor=C.BG, padding=18
        )

    # ---------------- EQUIPE / ROUTE ----------------

    def view_route():
        route = ft.Dropdown(
            label="Choisir la route",
            options=[ft.dropdown.Option(r) for r in ROUTES],
            width=320
        )
        nom = ft.TextField(label="Nom du chef d'équipage", width=320)

        def start(_):
            if not route.value or not (nom.value or "").strip():
                notify("Choisissez une route et entrez votre nom.", C.RED)
                return
            session["route"] = route.value
            session["equipage"] = nom.value.strip()
            page.go("/embarquement")

        return ft.View(
            "/route",
            [
                header("ESPACE ÉQUIPAGE", "Nouvelle traversée", "/"),
                ft.Container(
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                    size=58, color=C.NAVY),
                            ft.Text("Préparer une traversée", size=19,
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            route, nom,
                            ft.ElevatedButton(
                                "COMMENCER L'EMBARQUEMENT",
                                icon=ft.Icons.PLAY_ARROW,
                                bgcolor=C.YELLOW, color=C.NAVY,
                                width=320, height=52, on_click=start
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=18
                    )
                )
            ],
            bgcolor=C.BG, padding=0
        )

    # ---------------- EMBARQUEMENT ----------------

    def view_embarquement():
        if not session.get("route"):
            page.go("/route")
            return ft.View("/embarquement", [])

        eco = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        premiere = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        vip = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        kg = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        total = ft.Text("0 passagers • 0 kg • 0.00 $",
                        color=C.WHITE, weight=ft.FontWeight.BOLD)

        def refresh():
            e = int(eco.value or 0)
            p = int(premiere.value or 0)
            v = int(vip.value or 0)
            k = int(kg.value or 0)
            total.value = (
                f"{e+p+v} passagers • {k} kg • "
                f"{money(e*PRIX_ECO+p*PRIX_1ERE+v*PRIX_VIP+k*PRIX_KG)}"
            )
            page.update()

        def counter(label, price, control):
            def change(delta):
                n = max(0, int(control.value or 0) + delta)
                control.value = str(n)
                refresh()
            return ft.Container(
                padding=12, bgcolor=C.WHITE, border_radius=12,
                border=ft.border.all(1, C.BORDER),
                content=ft.Row(
                    [
                        ft.Column([
                            ft.Text(label, weight=ft.FontWeight.BOLD,
                                    color=C.NAVY),
                            ft.Text(f"{price} $", size=11, color=C.GRAY)
                        ], expand=True, spacing=2),
                        ft.IconButton(ft.Icons.REMOVE,
                                      on_click=lambda e: change(-1)),
                        control,
                        ft.IconButton(ft.Icons.ADD,
                                      on_click=lambda e: change(1))
                    ]
                )
            )

        def cargo():
            def change(delta):
                kg.value = str(max(0, int(kg.value or 0) + delta))
                refresh()
            return ft.Container(
                padding=12, bgcolor=C.WHITE, border_radius=12,
                border=ft.border.all(1, C.BORDER),
                content=ft.Column([
                    ft.Text("MARCHANDISES / CARGO",
                            weight=ft.FontWeight.BOLD, color=C.NAVY),
                    ft.Text(f"{PRIX_KG} $ / kg", size=11, color=C.GRAY),
                    ft.Row([
                        ft.OutlinedButton("-1", on_click=lambda e: change(-1)),
                        kg,
                        ft.OutlinedButton("+1", on_click=lambda e: change(1)),
                        ft.OutlinedButton("+10", on_click=lambda e: change(10)),
                        ft.OutlinedButton("+50", on_click=lambda e: change(50))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ])
            )

        def finish(_):
            e = int(eco.value or 0)
            p = int(premiere.value or 0)
            v = int(vip.value or 0)
            k = int(kg.value or 0)
            passengers = e + p + v
            if passengers == 0 and k == 0:
                notify("Ajoutez au moins un passager ou du cargo.", C.RED)
                return
            revenue = e*PRIX_ECO + p*PRIX_1ERE + v*PRIX_VIP + k*PRIX_KG
            now = datetime.now(timezone.utc)
            data = {
                "route": session["route"],
                "date": now.strftime("%Y-%m-%d %H:%M:%S"),
                "passagers_eco": e, "passagers_1ere": p,
                "passagers_vip": v, "passagers_total": passengers,
                "cargo_kg": k, "recette": revenue,
                "equipage": session["equipage"], "statut": "Terminé"
            }
            key = fb_post("bateaux/traversees", data)
            if key:
                notify(f"Traversée enregistrée : {money(revenue)}")
                session["route"] = ""
                page.go("/route")
            else:
                notify("Envoi Firebase échoué. Vérifiez Internet.", C.RED)

        return ft.View(
            "/embarquement",
            [
                header(f"ROUTE : {session['route']}",
                       "Enregistrement de la traversée", "/route"),
                ft.Container(
                    padding=14,
                    content=ft.Column(
                        [
                            counter("ÉCO", PRIX_ECO, eco),
                            counter("1ÈRE CLASSE", PRIX_1ERE, premiere),
                            counter("VIP", PRIX_VIP, vip),
                            cargo(),
                            ft.Container(
                                padding=16, bgcolor=C.NAVY, border_radius=12,
                                content=total
                            ),
                            ft.ElevatedButton(
                                "TERMINER ET ENVOYER",
                                icon=ft.Icons.SEND, bgcolor=C.YELLOW,
                                color=C.NAVY, height=54, expand=True,
                                on_click=finish
                            )
                        ],
                        spacing=12, scroll=ft.ScrollMode.AUTO
                    )
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- PATRON DASHBOARD ----------------

    def view_patron():
        voyages, depenses = load_all()
        valid_v = [v for v in voyages.values() if isinstance(v, dict)]
        valid_d = [d for d in depenses.values() if isinstance(d, dict)]
        recettes = sum(float(v.get("recette", 0) or 0) for v in valid_v)
        couts = sum(float(d.get("montant", 0) or 0) for d in valid_d)
        passagers = sum(int(v.get("passagers_total", 0) or 0) for v in valid_v)

        recent = sorted(
            valid_v, key=lambda x: x.get("date", ""), reverse=True
        )[:5]

        recent_controls = []
        for v in recent:
            recent_controls.append(
                ft.Container(
                    padding=12, bgcolor=C.WHITE, border_radius=10,
                    border=ft.border.all(1, C.BORDER),
                    content=ft.Row([
                        ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=C.NAVY),
                        ft.Column([
                            ft.Text(v.get("route", "Route inconnue"),
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            ft.Text(str(v.get("date", "")), size=10,
                                    color=C.GRAY)
                        ], expand=True),
                        ft.Text(money(float(v.get("recette", 0) or 0)),
                                weight=ft.FontWeight.BOLD, color=C.GREEN)
                    ])
                )
            )

        if not recent_controls:
            recent_controls.append(ft.Text("Aucune traversée enregistrée.",
                                           color=C.GRAY))

        return ft.View(
            "/patron",
            [
                ft.Container(
                    bgcolor=C.NAVY,
                    padding=ft.padding.only(top=42, left=18, right=18, bottom=20),
                    content=ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text("K-HAIM BATEAU", size=20,
                                        color=C.WHITE,
                                        weight=ft.FontWeight.BOLD),
                                ft.Text("TABLEAU DE BORD PATRON",
                                        color=C.YELLOW, size=10)
                            ], expand=True),
                            ft.IconButton(ft.Icons.REFRESH,
                                          icon_color=C.WHITE,
                                          on_click=lambda e: page.go("/patron")),
                            ft.IconButton(ft.Icons.LOGOUT,
                                          icon_color=C.WHITE,
                                          on_click=lambda e: page.go("/"))
                        ])
                    ])
                ),
                ft.Container(
                    padding=14,
                    content=ft.Column([
                        ft.Text("Vue générale", size=17,
                                weight=ft.FontWeight.BOLD, color=C.NAVY),
                        ft.Row([
                            card("Recettes", money(recettes), C.GREEN,
                                 ft.Icons.PAYMENTS),
                            card("Dépenses", money(couts), C.RED,
                                 ft.Icons.RECEIPT_LONG)
                        ]),
                        ft.Row([
                            card("Bénéfice net", money(recettes-couts),
                                 C.NAVY, ft.Icons.ACCOUNT_BALANCE_WALLET),
                            card("Passagers", str(passagers),
                                 C.NAVY2, ft.Icons.GROUPS)
                        ]),
                        ft.Text("Gestion", size=17, weight=ft.FontWeight.BOLD,
                                color=C.NAVY),
                        ft.Row([
                            action_button("Rapports", ft.Icons.BAR_CHART,
                                          "/rapports", C.NAVY),
                            action_button("Dépenses", ft.Icons.RECEIPT,
                                          "/depenses", C.NAVY2)
                        ]),
                        ft.Row([
                            action_button("Historique", ft.Icons.HISTORY,
                                          "/historique", C.NAVY2),
                            action_button("Nouvelle traversée",
                                          ft.Icons.DIRECTIONS_BOAT,
                                          "/route", C.GREEN)
                        ]),
                        ft.Text("Dernières traversées", size=17,
                                weight=ft.FontWeight.BOLD, color=C.NAVY),
                        ft.Column(recent_controls, spacing=8)
                    ], spacing=12)
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- EXPENSE MANAGEMENT ----------------

    def view_depenses():
        category = ft.Dropdown(
            label="Catégorie",
            options=[ft.dropdown.Option(x) for x in DEPENSE_CATEGORIES],
            width=320
        )
        amount = ft.TextField(label="Montant en USD", width=320,
                              keyboard_type=ft.KeyboardType.NUMBER)
        description = ft.TextField(
            label="Description / justificatif", width=320,
            multiline=True, min_lines=2, max_lines=4
        )
        operator = ft.TextField(label="Enregistré par", width=320)

        expense_list = ft.Column(spacing=8)

        def refresh_expenses():
            _, all_expenses = load_all()
            expense_list.controls.clear()
            rows = sorted(
                [(k, v) for k, v in all_expenses.items()
                 if isinstance(v, dict)],
                key=lambda x: x[1].get("date", ""), reverse=True
            )
            for key, item in rows[:30]:
                expense_list.controls.append(
                    ft.Container(
                        padding=12, bgcolor=C.WHITE, border_radius=10,
                        border=ft.border.all(1, C.BORDER),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(item.get("categorie", "Autre"),
                                        weight=ft.FontWeight.BOLD,
                                        color=C.NAVY),
                                ft.Text(item.get("description", ""),
                                        size=11, color=C.GRAY),
                                ft.Text(item.get("date", ""), size=10,
                                        color=C.GRAY)
                            ], expand=True, spacing=3),
                            ft.Text("-" + money(float(item.get("montant", 0) or 0)),
                                    color=C.RED, weight=ft.FontWeight.BOLD)
                        ])
                    )
                )
            if not rows:
                expense_list.controls.append(
                    ft.Text("Aucune dépense enregistrée.", color=C.GRAY)
                )

        def save_expense(_):
            try:
                value = float((amount.value or "").replace(",", "."))
                if value <= 0:
                    raise ValueError()
            except ValueError:
                notify("Entrez un montant valide supérieur à zéro.", C.RED)
                return
            if not category.value:
                notify("Choisissez une catégorie.", C.RED)
                return
            if not (description.value or "").strip():
                notify("Ajoutez une description.", C.RED)
                return

            data = {
                "date": datetime.now(timezone.utc)
                        .strftime("%Y-%m-%d %H:%M:%S"),
                "categorie": category.value,
                "montant": value,
                "description": description.value.strip(),
                "enregistre_par": (operator.value or "Patron").strip()
            }
            if fb_post("bateaux/depenses", data):
                notify("Dépense enregistrée.")
                amount.value = ""
                description.value = ""
                category.value = None
                page.update()
                refresh_expenses()
            else:
                notify("Impossible d'enregistrer dans Firebase.", C.RED)

        refresh_expenses()
        return ft.View(
            "/depenses",
            [
                header("GESTION DES DÉPENSES",
                       "Enregistrer et consulter les dépenses"),
                ft.Container(
                    padding=14,
                    content=ft.Column([
                        ft.Container(
                            padding=14, bgcolor=C.WHITE, border_radius=12,
                            border=ft.border.all(1, C.BORDER),
                            content=ft.Column([
                                ft.Text("Nouvelle dépense", size=17,
                                        weight=ft.FontWeight.BOLD,
                                        color=C.NAVY),
                                category, amount, description, operator,
                                ft.ElevatedButton(
                                    "ENREGISTRER LA DÉPENSE",
                                    icon=ft.Icons.SAVE, bgcolor=C.YELLOW,
                                    color=C.NAVY, height=48,
                                    on_click=save_expense
                                )
                            ], spacing=10)
                        ),
                        ft.Text("Dépenses récentes", size=17,
                                weight=ft.FontWeight.BOLD, color=C.NAVY),
                        expense_list
                    ], spacing=14)
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- REPORTS ----------------

    def view_rapports():
        period = ft.Dropdown(
            label="Période du rapport",
            value="Journalier",
            options=[
                ft.dropdown.Option("Journalier"),
                ft.dropdown.Option("Hebdomadaire"),
                ft.dropdown.Option("Mensuel")
            ],
            width=320
        )
        result = ft.Column(spacing=10)
        current_report = {"data": None}

        def render_report(_=None):
            report = build_report(period.value or "Journalier")
            current_report["data"] = report
            result.controls.clear()

            result.controls.extend([
                ft.Text(
                    f"Période : {report['start'].strftime('%d/%m/%Y')} au "
                    f"{report['end'].strftime('%d/%m/%Y')}",
                    color=C.GRAY, size=12
                ),
                ft.Row([
                    card("Recettes", money(report["recettes"]),
                         C.GREEN, ft.Icons.PAYMENTS),
                    card("Dépenses", money(report["depenses_total"]),
                         C.RED, ft.Icons.RECEIPT_LONG)
                ]),
                ft.Row([
                    card("Bénéfice net", money(report["benefice"]),
                         C.NAVY, ft.Icons.ACCOUNT_BALANCE_WALLET),
                    card("Passagers", str(report["passagers"]),
                         C.NAVY2, ft.Icons.GROUPS)
                ]),
                ft.Row([
                    card("Traversées", str(len(report["voyages"])),
                         C.NAVY2, ft.Icons.DIRECTIONS_BOAT),
                    card("Cargo", f"{report['cargo']:,.0f} kg",
                         C.NAVY, ft.Icons.INVENTORY_2)
                ]),
                ft.Text("Détail des traversées", size=16,
                        weight=ft.FontWeight.BOLD, color=C.NAVY)
            ])

            if report["voyages"]:
                for _, v in report["voyages"]:
                    result.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                            color=C.NAVY),
                            title=ft.Text(v.get("route", "Route")),
                            subtitle=ft.Text(
                                f"{v.get('date','')} • "
                                f"{v.get('passagers_total',0)} passagers"
                            ),
                            trailing=ft.Text(
                                money(float(v.get("recette", 0) or 0)),
                                color=C.GREEN, weight=ft.FontWeight.BOLD
                            )
                        )
                    )
            else:
                result.controls.append(
                    ft.Text("Aucune traversée sur cette période.",
                            color=C.GRAY)
                )

            result.controls.append(
                ft.Text("Détail des dépenses", size=16,
                        weight=ft.FontWeight.BOLD, color=C.NAVY)
            )
            if report["depenses"]:
                for _, d in report["depenses"]:
                    result.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.RECEIPT, color=C.RED),
                            title=ft.Text(d.get("categorie", "Dépense")),
                            subtitle=ft.Text(
                                f"{d.get('date','')} • {d.get('description','')}"
                            ),
                            trailing=ft.Text(
                                "-" + money(float(d.get("montant", 0) or 0)),
                                color=C.RED, weight=ft.FontWeight.BOLD
                            )
                        )
                    )
            else:
                result.controls.append(
                    ft.Text("Aucune dépense sur cette période.",
                            color=C.GRAY)
                )

            result.controls.append(
                ft.ElevatedButton(
                    "TÉLÉCHARGER LE RAPPORT CSV",
                    icon=ft.Icons.DOWNLOAD,
                    bgcolor=C.YELLOW, color=C.NAVY, height=52,
                    on_click=lambda e: export_report(current_report["data"])
                )
            )
            page.update()

        period.on_change = render_report
        render_report()

        return ft.View(
            "/rapports",
            [
                header("RAPPORTS FINANCIERS",
                       "Journalier • Hebdomadaire • Mensuel"),
                ft.Container(
                    padding=14,
                    content=ft.Column([
                        period,
                        ft.ElevatedButton(
                            "ACTUALISER LE RAPPORT",
                            icon=ft.Icons.REFRESH,
                            bgcolor=C.NAVY, color=C.WHITE,
                            on_click=render_report
                        ),
                        result
                    ], spacing=12)
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- HISTORY ----------------

    def view_historique():
        voyages, _ = load_all()
        controls = []
        rows = sorted(
            [(k, v) for k, v in voyages.items() if isinstance(v, dict)],
            key=lambda x: x[1].get("date", ""), reverse=True
        )
        for _, v in rows:
            controls.append(
                ft.Container(
                    padding=13, bgcolor=C.WHITE, border_radius=10,
                    border=ft.border.all(1, C.BORDER),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=C.NAVY),
                            ft.Text(v.get("route", "Route"),
                                    weight=ft.FontWeight.BOLD,
                                    color=C.NAVY, expand=True),
                            ft.Text(money(float(v.get("recette", 0) or 0)),
                                    color=C.GREEN,
                                    weight=ft.FontWeight.BOLD)
                        ]),
                        ft.Text(
                            f"Date : {v.get('date','')} | "
                            f"Passagers : {v.get('passagers_total',0)} | "
                            f"Cargo : {v.get('cargo_kg',0)} kg",
                            size=11, color=C.GRAY
                        ),
                        ft.Text(f"Équipage : {v.get('equipage','N/A')}",
                                size=11, color=C.GRAY)
                    ], spacing=5)
                )
            )
        if not controls:
            controls.append(ft.Text("Aucun historique disponible.",
                                    color=C.GRAY))
        return ft.View(
            "/historique",
            [
                header("HISTORIQUE", "Toutes les traversées"),
                ft.Container(padding=14,
                             content=ft.Column(controls, spacing=9))
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- ROUTING ----------------

    def route_change(_):
        page.views.clear()
        route = page.route or "/"
        if route == "/route":
            page.views.append(view_route())
        elif route == "/embarquement":
            page.views.append(view_embarquement())
        elif route == "/patron":
            page.views.append(view_patron())
        elif route == "/depenses":
            page.views.append(view_depenses())
        elif route == "/rapports":
            page.views.append(view_rapports())
        elif route == "/historique":
            page.views.append(view_historique())
        else:
            page.views.append(view_login())
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = lambda e: page.go("/")
    page.go("/")


if __name__ == "__main__":
    ft.app(target=main)    ft.Container(height=25),
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                    size=76, color=C.NAVY),
                            ft.Text("K-HAIM BATEAU", size=28,
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            ft.Text("GESTION MARITIME • LAC TANGANYIKA",
                                    size=10, color=C.GRAY),
                            ft.Container(height=35),
                            ft.ElevatedButton(
                                "ESPACE ÉQUIPAGE", icon=ft.Icons.GROUPS,
                                width=280, height=52, bgcolor=C.YELLOW,
                                color=C.NAVY,
                                on_click=lambda e: page.go("/route")
                            ),
                            ft.Container(height=16),
                            ft.Text("ACCÈS ADMINISTRATEUR",
                                    size=11, color=C.GRAY,
                                    weight=ft.FontWeight.BOLD),
                            pin,
                            ft.ElevatedButton(
                                "ESPACE PATRON",
                                icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                                width=280, height=52, bgcolor=C.NAVY,
                                color=C.WHITE, on_click=patron
                            ),
                            ft.Container(height=25)
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10
                    )
                )
            ],
            bgcolor=C.BG, padding=18
        )

    # ---------------- EQUIPE / ROUTE ----------------

    def view_route():
        route = ft.Dropdown(
            label="Choisir la route",
            options=[ft.dropdown.Option(r) for r in ROUTES],
            width=320
        )
        nom = ft.TextField(label="Nom du chef d'équipage", width=320)

        def start(_):
            if not route.value or not (nom.value or "").strip():
                notify("Choisissez une route et entrez votre nom.", C.RED)
                return
            session["route"] = route.value
            session["equipage"] = nom.value.strip()
            page.go("/embarquement")

        return ft.View(
            "/route",
            [
                header("ESPACE ÉQUIPAGE", "Nouvelle traversée", "/"),
                ft.Container(
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                    size=58, color=C.NAVY),
                            ft.Text("Préparer une traversée", size=19,
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            route, nom,
                            ft.ElevatedButton(
                                "COMMENCER L'EMBARQUEMENT",
                                icon=ft.Icons.PLAY_ARROW,
                                bgcolor=C.YELLOW, color=C.NAVY,
                                width=320, height=52, on_click=start
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=18
                    )
                )
            ],
            bgcolor=C.BG, padding=0
        )

    # ---------------- EMBARQUEMENT ----------------

    def view_embarquement():
        if not session.get("route"):
            page.go("/route")
            return ft.View("/embarquement", [])

        eco = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        premiere = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        vip = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        kg = ft.Text("0", size=23, weight=ft.FontWeight.BOLD)
        total = ft.Text("0 passagers • 0 kg • 0.00 $",
                        color=C.WHITE, weight=ft.FontWeight.BOLD)

        def refresh():
            e = int(eco.value or 0)
            p = int(premiere.value or 0)
            v = int(vip.value or 0)
            k = int(kg.value or 0)
            total.value = (
                f"{e+p+v} passagers • {k} kg • "
                f"{money(e*PRIX_ECO+p*PRIX_1ERE+v*PRIX_VIP+k*PRIX_KG)}"
            )
            page.update()

        def counter(label, price, control):
            def change(delta):
                n = max(0, int(control.value or 0) + delta)
                control.value = str(n)
                refresh()
            return ft.Container(
                padding=12, bgcolor=C.WHITE, border_radius=12,
                border=ft.border.all(1, C.BORDER),
                content=ft.Row(
                    [
                        ft.Column([
                            ft.Text(label, weight=ft.FontWeight.BOLD,
                                    color=C.NAVY),
                            ft.Text(f"{price} $", size=11, color=C.GRAY)
                        ], expand=True, spacing=2),
                        ft.IconButton(ft.Icons.REMOVE,
                                      on_click=lambda e: change(-1)),
                        control,
                        ft.IconButton(ft.Icons.ADD,
                                      on_click=lambda e: change(1))
                    ]
                )
            )

        def cargo():
            def change(delta):
                kg.value = str(max(0, int(kg.value or 0) + delta))
                refresh()
            return ft.Container(
                padding=12, bgcolor=C.WHITE, border_radius=12,
                border=ft.border.all(1, C.BORDER),
                content=ft.Column([
                    ft.Text("MARCHANDISES / CARGO",
                            weight=ft.FontWeight.BOLD, color=C.NAVY),
                    ft.Text(f"{PRIX_KG} $ / kg", size=11, color=C.GRAY),
                    ft.Row([
                        ft.OutlinedButton("-1", on_click=lambda e: change(-1)),
                        kg,
                        ft.OutlinedButton("+1", on_click=lambda e: change(1)),
                        ft.OutlinedButton("+10", on_click=lambda e: change(10)),
                        ft.OutlinedButton("+50", on_click=lambda e: change(50))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ])
            )

        def finish(_):
            e = int(eco.value or 0)
            p = int(premiere.value or 0)
            v = int(vip.value or 0)
            k = int(kg.value or 0)
            passengers = e + p + v
            if passengers == 0 and k == 0:
                notify("Ajoutez au moins un passager ou du cargo.", C.RED)
                return
            revenue = e*PRIX_ECO + p*PRIX_1ERE + v*PRIX_VIP + k*PRIX_KG
            now = datetime.now(timezone.utc)
            data = {
                "route": session["route"],
                "date": now.strftime("%Y-%m-%d %H:%M:%S"),
                "passagers_eco": e, "passagers_1ere": p,
                "passagers_vip": v, "passagers_total": passengers,
                "cargo_kg": k, "recette": revenue,
                "equipage": session["equipage"], "statut": "Terminé"
            }
            key = fb_post("bateaux/traversees", data)
            if key:
                notify(f"Traversée enregistrée : {money(revenue)}")
                session["route"] = ""
                page.go("/route")
            else:
                notify("Envoi Firebase échoué. Vérifiez Internet.", C.RED)

        return ft.View(
            "/embarquement",
            [
                header(f"ROUTE : {session['route']}",
                       "Enregistrement de la traversée", "/route"),
                ft.Container(
                    padding=14,
                    content=ft.Column(
                        [
                            counter("ÉCO", PRIX_ECO, eco),
                            counter("1ÈRE CLASSE", PRIX_1ERE, premiere),
                            counter("VIP", PRIX_VIP, vip),
                            cargo(),
                            ft.Container(
                                padding=16, bgcolor=C.NAVY, border_radius=12,
                                content=total
                            ),
                            ft.ElevatedButton(
                                "TERMINER ET ENVOYER",
                                icon=ft.Icons.SEND, bgcolor=C.YELLOW,
                                color=C.NAVY, height=54, expand=True,
                                on_click=finish
                            )
                        ],
                        spacing=12, scroll=ft.ScrollMode.AUTO
                    )
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- PATRON DASHBOARD ----------------

     def view_patron():
        voyages, depenses = load_all()
        valid_v = [v for v in voyages.values() if isinstance(v, dict)]
        valid_d = [d for d in depenses.values() if isinstance(d, dict)]
        recettes = sum(float(v.get("recette", 0) or 0) for v in valid_v)
        couts = sum(float(d.get("montant", 0) or 0) for d in valid_d)
        passagers = sum(int(v.get("passagers_total", 0) or 0) for v in valid_v)

        recent = sorted(
            valid_v, key=lambda x: x.get("date", ""), reverse=True
        )[:5]

        recent_controls = []
        for v in recent:
            recent_controls.append(
                ft.Container(
                    padding=12, bgcolor=C.WHITE, border_radius=10,
                    border=ft.border.all(1, C.BORDER),
                    content=ft.Row([
                        ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=C.NAVY),
                        ft.Column([
                            ft.Text(v.get("route", "Route inconnue"),
                                    weight=ft.FontWeight.BOLD, color=C.NAVY),
                            ft.Text(str(v.get("date", "")), size=10,
                                    color=C.GRAY)
                        ], expand=True),
                        ft.Text(money(float(v.get("recette", 0) or 0)),
                                weight=ft.FontWeight.BOLD, color=C.GREEN)
                    ])
                )
            )

        if not recent_controls:
            recent_controls.append(ft.Text("Aucune traversée enregistrée.",
                                           color=C.GRAY))

        return ft.View(
            "/patron",
            [
                ft.Container(
                    bgcolor=C.NAVY,
                    padding=ft.padding.only(top=42, left=18, right=18, bottom=20),
                    content=ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text("K-HAIM BATEAU", size=20,
                                        color=C.WHITE,
                                        weight=ft.FontWeight.BOLD),
                                ft.Text("TABLEAU DE BORD PATRON",
                                        color=C.YELLOW, size=10)
                            ], expand=True),
                            ft.IconButton(ft.Icons.REFRESH,
                                          icon_color=C.WHITE,
                                          on_click=lambda e: page.go("/patron")),
                            ft.IconButton(ft.Icons.LOGOUT,
                                          icon_color=C.WHITE,
                                          on_click=lambda e: page.go("/"))
                        ])
                    ])
                ),
                ft.Container(
                    padding=14,
                    content=ft.Column([
                        ft.Text("Vue générale", size=17,
                                weight=ft.FontWeight.BOLD, color=C.NAVY),
                        ft.Row([
                            card("Recettes", money(recettes), C.GREEN,
                                 ft.Icons.PAYMENTS),
                            card("Dépenses", money(couts), C.RED,
                                 ft.Icons.RECEIPT_LONG)
                        ]),
                        ft.Row([
                            card("Bénéfice net", money(recettes-couts),
                                 C.NAVY, ft.Icons.ACCOUNT_BALANCE_WALLET),
                            card("Passagers", str(passagers),
                                 C.NAVY2, ft.Icons.GROUPS)
                        ]),
                        ft.Text("Gestion", size=17, weight=ft.FontWeight.BOLD,
                                color=C.NAVY),
                        ft.Row([
                            action_button("Rapports", ft.Icons.BAR_CHART,
                                          "/rapports", C.NAVY),
                            action_button("Dépenses", ft.Icons.RECEIPT,
                                          "/depenses", C.NAVY2)
                        ]),
                        ft.Row([
                            action_button("Historique", ft.Icons.HISTORY,
                                          "/historique", C.NAVY2),
                            action_button("Nouvelle traversée",
                                          ft.Icons.DIRECTIONS_BOAT,
                                          "/route", C.GREEN)
                        ]),
                        ft.Text("Dernières traversées", size=17,
                                weight=ft.FontWeight.BOLD, color=C.NAVY),
                        ft.Column(recent_controls, spacing=8)
                    ], spacing=12)
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- EXPENSE MANAGEMENT ----------------

    def view_depenses():
        category = ft.Dropdown(
            label="Catégorie",
            options=[ft.dropdown.Option(x) for x in DEPENSE_CATEGORIES],
            width=320
        )
        amount = ft.TextField(label="Montant en USD", width=320,
                              keyboard_type=ft.KeyboardType.NUMBER)
        description = ft.TextField(
            label="Description / justificatif", width=320,
            multiline=True, min_lines=2, max_lines=4
        )
        operator = ft.TextField(label="Enregistré par", width=320)

        expense_list = ft.Column(spacing=8)

        def refresh_expenses():
            _, all_expenses = load_all()
            expense_list.controls.clear()
            rows = sorted(
                [(k, v) for k, v in all_expenses.items()
                 if isinstance(v, dict)],
                key=lambda x: x[1].get("date", ""), reverse=True
            )
            for key, item in rows[:30]:
                expense_list.controls.append(
                    ft.Container(
                        padding=12, bgcolor=C.WHITE, border_radius=10,
                        border=ft.border.all(1, C.BORDER),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(item.get("categorie", "Autre"),
                                        weight=ft.FontWeight.BOLD,
                                        color=C.NAVY),
                                ft.Text(item.get("description", ""),
                                        size=11, color=C.GRAY),
                                ft.Text(item.get("date", ""), size=10,
                                        color=C.GRAY)
                            ], expand=True, spacing=3),
                            ft.Text("-" + money(float(item.get("montant", 0) or 0)),
                                    color=C.RED, weight=ft.FontWeight.BOLD)
                        ])
                    )
                )
            if not rows:
                expense_list.controls.append(
                    ft.Text("Aucune dépense enregistrée.", color=C.GRAY)
                )

        def save_expense(_):
            try:
                value = float((amount.value or "").replace(",", "."))
                if value <= 0:
                    raise ValueError()
            except ValueError:
                notify("Entrez un montant valide supérieur à zéro.", C.RED)
                return
            if not category.value:
                notify("Choisissez une catégorie.", C.RED)
                return
            if not (description.value or "").strip():
                notify("Ajoutez une description.", C.RED)
                return

            data = {
                "date": datetime.now(timezone.utc)
                        .strftime("%Y-%m-%d %H:%M:%S"),
                "categorie": category.value,
                "montant": value,
                "description": description.value.strip(),
                "enregistre_par": (operator.value or "Patron").strip()
            }
            if fb_post("bateaux/depenses", data):
                notify("Dépense enregistrée.")
                amount.value = ""
                description.value = ""
                category.value = None
                page.update()
                refresh_expenses()
            else:
                notify("Impossible d'enregistrer dans Firebase.", C.RED)

        refresh_expenses()
        return ft.View(
            "/depenses",
            [
                header("GESTION DES DÉPENSES",
                       "Enregistrer et consulter les dépenses"),
                ft.Container(
                    padding=14,
                    content=ft.Column([
                        ft.Container(
                            padding=14, bgcolor=C.WHITE, border_radius=12,
                            border=ft.border.all(1, C.BORDER),
                            content=ft.Column([
                                ft.Text("Nouvelle dépense", size=17,
                                        weight=ft.FontWeight.BOLD,
                                        color=C.NAVY),
                                category, amount, description, operator,
                                ft.ElevatedButton(
                                    "ENREGISTRER LA DÉPENSE",
                                    icon=ft.Icons.SAVE, bgcolor=C.YELLOW,
                                    color=C.NAVY, height=48,
                                    on_click=save_expense
                                )
                            ], spacing=10)
                        ),
                        ft.Text("Dépenses récentes", size=17,
                                weight=ft.FontWeight.BOLD, color=C.NAVY),
                        expense_list
                    ], spacing=14)
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- REPORTS ----------------

    def view_rapports():
        period = ft.Dropdown(
            label="Période du rapport",
            value="Journalier",
            options=[
                ft.dropdown.Option("Journalier"),
                ft.dropdown.Option("Hebdomadaire"),
                ft.dropdown.Option("Mensuel")
            ],
            width=320
        )
        result = ft.Column(spacing=10)
        current_report = {"data": None}

        def render_report(_=None):
            report = build_report(period.value or "Journalier")
            current_report["data"] = report
            result.controls.clear()

            result.controls.extend([
                ft.Text(
                    f"Période : {report['start'].strftime('%d/%m/%Y')} au "
                    f"{report['end'].strftime('%d/%m/%Y')}",
                    color=C.GRAY, size=12
                ),
                ft.Row([
                    card("Recettes", money(report["recettes"]),
                         C.GREEN, ft.Icons.PAYMENTS),
                    card("Dépenses", money(report["depenses_total"]),
                         C.RED, ft.Icons.RECEIPT_LONG)
                ]),
                ft.Row([
                    card("Bénéfice net", money(report["benefice"]),
                         C.NAVY, ft.Icons.ACCOUNT_BALANCE_WALLET),
                    card("Passagers", str(report["passagers"]),
                         C.NAVY2, ft.Icons.GROUPS)
                ]),
                ft.Row([
                    card("Traversées", str(len(report["voyages"])),
                         C.NAVY2, ft.Icons.DIRECTIONS_BOAT),
                    card("Cargo", f"{report['cargo']:,.0f} kg",
                         C.NAVY, ft.Icons.INVENTORY_2)
                ]),
                ft.Text("Détail des traversées", size=16,
                        weight=ft.FontWeight.BOLD, color=C.NAVY)
            ])

            if report["voyages"]:
                for _, v in report["voyages"]:
                    result.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.DIRECTIONS_BOAT,
                                            color=C.NAVY),
                            title=ft.Text(v.get("route", "Route")),
                            subtitle=ft.Text(
                                f"{v.get('date','')} • "
                                f"{v.get('passagers_total',0)} passagers"
                            ),
                            trailing=ft.Text(
                                money(float(v.get("recette", 0) or 0)),
                                color=C.GREEN, weight=ft.FontWeight.BOLD
                            )
                        )
                    )
            else:
                result.controls.append(
                    ft.Text("Aucune traversée sur cette période.",
                            color=C.GRAY)
                )

            result.controls.append(
                ft.Text("Détail des dépenses", size=16,
                        weight=ft.FontWeight.BOLD, color=C.NAVY)
            )
            if report["depenses"]:
                for _, d in report["depenses"]:
                    result.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.RECEIPT, color=C.RED),
                            title=ft.Text(d.get("categorie", "Dépense")),
                            subtitle=ft.Text(
                                f"{d.get('date','')} • {d.get('description','')}"
                            ),
                            trailing=ft.Text(
                                "-" + money(float(d.get("montant", 0) or 0)),
                                color=C.RED, weight=ft.FontWeight.BOLD
                            )
                        )
                    )
            else:
                result.controls.append(
                    ft.Text("Aucune dépense sur cette période.",
                            color=C.GRAY)
                )

            result.controls.append(
                ft.ElevatedButton(
                    "TÉLÉCHARGER LE RAPPORT CSV",
                    icon=ft.Icons.DOWNLOAD,
                    bgcolor=C.YELLOW, color=C.NAVY, height=52,
                    on_click=lambda e: export_report(current_report["data"])
                )
            )
            page.update()

        period.on_change = render_report
        render_report()

        return ft.View(
            "/rapports",
            [
                header("RAPPORTS FINANCIERS",
                       "Journalier • Hebdomadaire • Mensuel"),
                ft.Container(
                    padding=14,
                    content=ft.Column([
                        period,
                        ft.ElevatedButton(
                            "ACTUALISER LE RAPPORT",
                            icon=ft.Icons.REFRESH,
                            bgcolor=C.NAVY, color=C.WHITE,
                            on_click=render_report
                        ),
                        result
                    ], spacing=12)
                )
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- HISTORY ----------------

    def view_historique():
        voyages, _ = load_all()
        controls = []
        rows = sorted(
            [(k, v) for k, v in voyages.items() if isinstance(v, dict)],
            key=lambda x: x[1].get("date", ""), reverse=True
        )
        for _, v in rows:
            controls.append(
                ft.Container(
                    padding=13, bgcolor=C.WHITE, border_radius=10,
                    border=ft.border.all(1, C.BORDER),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=C.NAVY),
                            ft.Text(v.get("route", "Route"),
                                    weight=ft.FontWeight.BOLD,
                                    color=C.NAVY, expand=True),
                            ft.Text(money(float(v.get("recette", 0) or 0)),
                                    color=C.GREEN,
                                    weight=ft.FontWeight.BOLD)
                        ]),
                        ft.Text(
                            f"Date : {v.get('date','')} | "
                            f"Passagers : {v.get('passagers_total',0)} | "
                            f"Cargo : {v.get('cargo_kg',0)} kg",
                            size=11, color=C.GRAY
                        ),
                        ft.Text(f"Équipage : {v.get('equipage','N/A')}",
                                size=11, color=C.GRAY)
                    ], spacing=5)
                )
            )
        if not controls:
            controls.append(ft.Text("Aucun historique disponible.",
                                    color=C.GRAY))
        return ft.View(
            "/historique",
            [
                header("HISTORIQUE", "Toutes les traversées"),
                ft.Container(padding=14,
                             content=ft.Column(controls, spacing=9))
            ],
            bgcolor=C.BG, padding=0, scroll=ft.ScrollMode.AUTO
        )

    # ---------------- ROUTING ----------------

    def route_change(_):
        page.views.clear()
        route = page.route or "/"
        if route == "/route":
            page.views.append(view_route())
        elif route == "/embarquement":
            page.views.append(view_embarquement())
        elif route == "/patron":
            page.views.append(view_patron())
        elif route == "/depenses":
            page.views.append(view_depenses())
        elif route == "/rapports":
            page.views.append(view_rapports())
        elif route == "/historique":
            page.views.append(view_historique())
        else:
            page.views.append(view_login())
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = lambda e: page.go("/")
    page.go("/")


if __name__ == "__main__":
    ft.app(target=main)
