import flet as ft
import requests
from datetime import datetime

# ==========================================
# CONFIGURATION FIREBASE
# ==========================================
FIREBASE_URL = "https://k-haime-suivi-48bc4-default-rtdb.firebaseio.com"

class AppColors:
    DARK_BLUE = "#0A2342"
    YELLOW = "#FFD60A"
    WHITE = "#FFFFFF"
    GREEN = "#4CAF50"
    RED = "#E53935"
    TEXT_GRAY = "#6C757D"
    BG_GRAY = "#F5F7FB"
    LIGHT_BLUE = "#E0E7FF"

ROUTES = [
    "Kalemie → Kigoma", "Kigoma → Kalemie",
    "Kalemie → Uvira", "Uvira → Kalemie",
    "Kalemie → Moba", "Moba → Kalemie"
]

PRIX_ECO = 25
PRIX_1ERE = 50
PRIX_VIP = 80
PRIX_KG = 2

def main(page: ft.Page):
    page.title = "K-HAIM BATEAU"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = AppColors.BG_GRAY
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    # Dictionnaire pour stocker les infos de session
    donnees_session = {"equipage": "Non spécifié", "route": ""}

    # ==========================================
    # FONCTIONS FIREBASE
    # ==========================================
    def fb_get(path):
        try:
            r = requests.get(f"{FIREBASE_URL}/{path}.json", timeout=10)
            return r.json() if r.status_code == 200 and r.json() else {}
        except Exception:
            return {}

    def fb_put(path, data):
        try:
            r = requests.put(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def notifier(message, couleur=AppColors.GREEN):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=couleur)
        page.snack_bar.open = True
        page.update()

    def naviguer(route):
        page.go(route)

    # ==========================================
    # ÉTATS GLOBAUX (compteurs)
    # ==========================================
    selected_route = ft.Text(value="", visible=False)
    count_eco = ft.Text("0", size=28, weight=ft.FontWeight.BOLD)
    count_1ere = ft.Text("0", size=28, weight=ft.FontWeight.BOLD)
    count_vip = ft.Text("0", size=28, weight=ft.FontWeight.BOLD)
    count_kg = ft.Text("0 kg", size=24, weight=ft.FontWeight.BOLD)
    total_text = ft.Text("TOTAL: 0 pass | 0 kg | 0 $", size=15, weight=ft.FontWeight.BOLD, color=AppColors.WHITE)

    def update_total():
        e = int(count_eco.value)
        f = int(count_1ere.value)
        v = int(count_vip.value)
        kg_val = int(count_kg.value.split()[0])
        total_pass = e + f + v
        recette = e * PRIX_ECO + f * PRIX_1ERE + v * PRIX_VIP + kg_val * PRIX_KG
        total_text.value = f"TOTAL: {total_pass} pass | {kg_val} kg | {recette} $"
        page.update()

    def reset_compteurs():
        count_eco.value = "0"
        count_1ere.value = "0"
        count_vip.value = "0"
        count_kg.value = "0 kg"
        selected_route.value = ""

    # ==========================================
    # COMPOSANTS : COMPTEURS
    # ==========================================
    def counter_row(label, prix, counter_text):
        def inc(e):
            counter_text.value = str(int(counter_text.value) + 1)
            update_total()
        def dec(e):
            if int(counter_text.value) > 0:
                counter_text.value = str(int(counter_text.value) - 1)
                update_total()
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(label, weight=ft.FontWeight.BOLD, color=AppColors.DARK_BLUE),
                    ft.Text(f"{prix} $", color=AppColors.TEXT_GRAY, size=12)
                ]),
                ft.Container(expand=True),
                ft.IconButton(ft.icons.REMOVE, on_click=dec, bgcolor=AppColors.LIGHT_BLUE, icon_color=AppColors.DARK_BLUE),
                ft.Container(content=counter_text, padding=10, width=50, alignment=ft.alignment.center),
                ft.IconButton(ft.icons.ADD, on_click=inc, bgcolor=AppColors.YELLOW, icon_color=AppColors.DARK_BLUE),
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=15, bgcolor=AppColors.WHITE, border_radius=15,
            shadow=ft.BoxShadow(blur_radius=5, color=ft.colors.with_opacity(0.05, "black"))
        )

    def counter_kg():
        def inc(val):
            def handler(e):
                current = int(count_kg.value.split()[0])
                count_kg.value = f"{current + val} kg"
                update_total()
            return handler
        def dec(e):
            current = int(count_kg.value.split()[0])
            if current > 0:
                count_kg.value = f"{max(0, current - 1)} kg"
                update_total()
        return ft.Container(
            content=ft.Column([
                ft.Text("CARGO (kg)", weight=ft.FontWeight.BOLD, color=AppColors.DARK_BLUE),
                ft.Text(f"{PRIX_KG} $ / kg", color=AppColors.TEXT_GRAY, size=12),
                ft.Container(height=5),
                ft.Row([
                    ft.IconButton(ft.icons.REMOVE, on_click=dec, bgcolor=AppColors.LIGHT_BLUE, icon_color=AppColors.DARK_BLUE),
                    ft.Container(content=count_kg, padding=10, width=80, alignment=ft.alignment.center),
                    ft.IconButton(ft.icons.ADD, content=ft.Text("+1"), on_click=inc(1), bgcolor=AppColors.WHITE),
                    ft.IconButton(ft.icons.ADD, content=ft.Text("+10"), on_click=inc(10), bgcolor=AppColors.WHITE),
                    ft.IconButton(ft.icons.ADD, content=ft.Text("+50"), on_click=inc(50), bgcolor=AppColors.DARK_BLUE, icon_color=AppColors.WHITE),
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]),
            padding=15, bgcolor=AppColors.WHITE, border_radius=15,
            shadow=ft.BoxShadow(blur_radius=5, color=ft.colors.with_opacity(0.05, "black"))
        )

    # ==========================================
    # VUE PATRON
    # ==========================================
    def view_patron():
        liste_voyages = ft.Column()
        stats_row = ft.Row(spacing=10)

        def creer_stat_card(label, valeur, couleur):
            return ft.Container(
                expand=True, bgcolor=couleur, border_radius=10, padding=15,
                content=ft.Column([
                    ft.Text(valeur, size=20, weight=ft.FontWeight.BOLD,
                            color=AppColors.WHITE if couleur != AppColors.YELLOW else AppColors.DARK_BLUE),
                    ft.Text(label, size=11,
                            color=AppColors.WHITE if couleur != AppColors.YELLOW else AppColors.DARK_BLUE)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

        def charger_donnees(e=None):
            voyages = fb_get("bateaux/traversees")
            liste_voyages.controls.clear()
            stats_row.controls.clear()

            if not voyages:
                liste_voyages.controls.append(
                    ft.Text("Aucune traversée enregistrée pour le moment.", color=AppColors.TEXT_GRAY)
                )
                stats_row.controls.append(creer_stat_card("Voyages", "0", AppColors.DARK_BLUE))
                stats_row.controls.append(creer_stat_card("Passagers", "0", AppColors.YELLOW))
                stats_row.controls.append(creer_stat_card("Recette", "0 $", AppColors.GREEN))
            else:
                total_recette = 0
                total_passagers = 0
                voyages_tries = sorted(voyages.items(), key=lambda x: x[1].get("date", ""), reverse=True)

                for tid, v in voyages_tries:
                    total_recette += v.get("recette", 0)
                    total_passagers += v.get("passagers_total", 0)

                    liste_voyages.controls.append(
                        ft.Container(
                            bgcolor=AppColors.WHITE, border_radius=10, padding=15,
                            margin=ft.margin.only(bottom=10),
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.DIRECTIONS_BOAT, color=AppColors.DARK_BLUE, size=24),
                                    ft.Column([
                                        ft.Text(v.get("route", "N/A"), weight=ft.FontWeight.BOLD,
                                                color=AppColors.DARK_BLUE, size=15),
                                        ft.Text(f"Date : {v.get('date', 'N/A')}", size=11,
                                                color=AppColors.TEXT_GRAY),
                                    ], spacing=2, expand=True),
                                    ft.Container(
                                        content=ft.Text(v.get("statut", "Terminé"), size=10,
                                                        color=AppColors.WHITE, weight=ft.FontWeight.BOLD),
                                        bgcolor=AppColors.GREEN,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        border_radius=5
                                    )
                                ]),
                                ft.Divider(height=5),
                                ft.Row([
                                    ft.Text(f"👥 Passagers : {v.get('passagers_total', 0)}", size=12,
                                            color=AppColors.TEXT_GRAY),
                                    ft.Text(f"📦 Cargo : {v.get('cargo_kg', 0)} kg", size=12,
                                            color=AppColors.TEXT_GRAY),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Text(f"💰 Recette : {v.get('recette', 0)} $", size=13,
                                            weight=ft.FontWeight.BOLD, color=AppColors.GREEN),
                                    ft.Text(f"Équipage : {v.get('equipage', 'N/A')}", size=11,
                                            color=AppColors.TEXT_GRAY),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ])
                        )
                    )

                stats_row.controls.append(creer_stat_card("Voyages", str(len(voyages)), AppColors.DARK_BLUE))
                stats_row.controls.append(creer_stat_card("Passagers", str(total_passagers), AppColors.YELLOW))
                stats_row.controls.append(creer_stat_card("Recette", f"{total_recette} $", AppColors.GREEN))

            page.update()

        header = ft.Container(
            bgcolor=AppColors.DARK_BLUE,
            padding=ft.padding.only(top=50, left=20, right=20, bottom=20),
            content=ft.Row([
                ft.IconButton(ft.icons.ARROW_BACK, icon_color=AppColors.WHITE,
                              on_click=lambda _: naviguer("/")),
                ft.Column([
                    ft.Text("K-HAIM PATRON", color=AppColors.WHITE, size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Suivi des traversées", color=AppColors.YELLOW, size=12),
                ], spacing=2, expand=True),
                ft.IconButton(ft.icons.REFRESH, icon_color=AppColors.WHITE, on_click=charger_donnees)
            ])
        )

        vue = ft.Column([
            header,
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Tableau de bord", size=16, weight=ft.FontWeight.BOLD, color=AppColors.DARK_BLUE),
                    ft.Container(height=10),
                    stats_row,
                    ft.Container(height=20),
                    ft.Text("Historique des traversées", size=16, weight=ft.FontWeight.BOLD,
                            color=AppColors.DARK_BLUE),
                    ft.Container(height=10),
                    liste_voyages
                ])
            )
        ])

        charger_donnees()
        return vue

    # ==========================================
    # VUE ÉQUIPAGE : CHOISIR LA ROUTE
    # ==========================================
    def view_equipage_route():
        route_dropdown = ft.Dropdown(
            label="Choisir la route",
            options=[ft.dropdown.Option(r) for r in ROUTES],
            width=350,
            border_radius=10
        )
        nom_equipage = ft.TextField(
            label="Nom du chef d'équipage",
            width=350,
            border_radius=10
        )

        def start(e):
            if not route_dropdown.value:
                notifier("Veuillez choisir une route !", AppColors.RED)
                return
            if not nom_equipage.value:
                notifier("Veuillez entrer votre nom !", AppColors.RED)
                return
            selected_route.value = route_dropdown.value
            donnees_session["equipage"] = nom_equipage.value.strip()
            donnees_session["route"] = route_dropdown.value
            naviguer("/embarquement")

        return ft.Column([
            ft.Container(
                bgcolor=AppColors.DARK_BLUE,
                padding=ft.padding.only(top=50, left=20, right=20, bottom=20),
                content=ft.Row([
                    ft.IconButton(ft.icons.ARROW_BACK, icon_color=AppColors.WHITE,
                                  on_click=lambda _: naviguer("/")),
                    ft.Column([
                        ft.Text("K-HAIM ÉQUIPAGE", color=AppColors.WHITE, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Nouvelle traversée", color=AppColors.YELLOW, size=12),
                    ], spacing=2)
                ])
            ),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Icon(ft.icons.DIRECTIONS_BOAT, size=60, color=AppColors.DARK_BLUE),
                    ft.Text("Choisir la route", size=18, weight=ft.FontWeight.BOLD, color=AppColors.DARK_BLUE),
                    ft.Container(height=15),
                    route_dropdown,
                    ft.Container(height=10),
                    nom_equipage,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "COMMENCER L'EMBARQUEMENT",
                        icon=ft.icons.PLAY_ARROW,
                        bgcolor=AppColors.YELLOW, color=AppColors.DARK_BLUE,
                        width=350, height=55,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            text_style=ft.TextStyle(size=15, weight=ft.FontWeight.BOLD)
                        ),
                        on_click=start
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        ])

    # ==========================================
    # VUE ÉQUIPAGE : EMBARQUEMENT
    # ==========================================
    def view_embarquement():
        def terminer(e):
            e_count = int(count_eco.value)
            f_count = int(count_1ere.value)
            v_count = int(count_vip.value)
            kg_count = int(count_kg.value.split()[0])
            
            total_passagers = e_count + f_count + v_count
            recette = e_count * PRIX_ECO + f_count * PRIX_1ERE + v_count * PRIX_VIP + kg_count * PRIX_KG
            equipage_nom = donnees_session.get("equipage", "Non spécifié")
            
            date_actuelle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            traversee_id = f"traversee_{int(datetime.now().timestamp())}"
            
            data = {
                "route": selected_route.value,
                "date": date_actuelle,
                "passagers_eco": e_count,
                "passagers_1ere": f_count,
                "passagers_vip": v_count,
                "passagers_total": total_passagers,
                "cargo_kg": kg_count,
                "recette": recette,
                "equipage": equipage_nom,
                "statut": "Terminé"
            }
            
            if fb_put(f"bateaux/traversees/{traversee_id}", data):
                notifier(f"✅ Traversée envoyée ! Recette : {recette} $", AppColors.GREEN)
                reset_compteurs()
                update_total()
                naviguer("/")
            else:
                notifier("❌ Erreur d'envoi. Vérifiez votre connexion.", AppColors.RED)

        header = ft.Container(
            bgcolor=AppColors.DARK_BLUE,
            padding=ft.padding.only(top=50, left=20, right=20, bottom=20),
            content=ft.Row([
                ft.IconButton(ft.icons.ARROW_BACK, icon_color=AppColors.WHITE,
                              on_click=lambda _: naviguer("/route")),
                ft.Column([
                    ft.Text(f"Route : {selected_route.value}", color=AppColors.WHITE, size=14,
                            weight=ft.FontWeight.BOLD),
                    ft.Text("Enregistrement de la traversée", color=AppColors.YELLOW, size=11),
                ], spacing=2)
            ])
        )

        contenu_scrollable = ft.Column([
            counter_row("ÉCO (25$)", PRIX_ECO, count_eco),
            ft.Container(height=5),
            counter_row("1ère CLASSE (50$)", PRIX_1ERE, count_1ere),
            ft.Container(height=5),
            counter_row("VIP (80$)", PRIX_VIP, count_vip),
            ft.Container(height=5),
            counter_kg(),
            ft.Container(height=15),
            ft.Container(
                bgcolor=AppColors.DARK_BLUE, border_radius=10, padding=15,
                content=total_text
            ),
            ft.Container(height=15),
            ft.ElevatedButton(
                "TERMINER & ENVOYER AU PATRON",
                icon=ft.icons.SEND,
                bgcolor=AppColors.YELLOW, color=AppColors.DARK_BLUE,
                width=350, height=60,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD)
                ),
                on_click=terminer
            ),
            ft.Container(height=30),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

        return ft.Column([
            header,
            ft.Container(
                padding=15,
                expand=True,
                content=ft.ListView(
                    [contenu_scrollable],
                    expand=True,
                    auto_scroll=False,
                    spacing=0,
                )
            )
        ], expand=True)

    # ==========================================
    # VUE LOGIN
    # ==========================================
def view_login():
        pin_field = ft.TextField(label="Code d'accès Patron", password=True, width=250, border_radius=10)

        def go_equipage(e):
            naviguer("/route")

        def go_patron(e):
            if pin_field.value == "2404":
                naviguer("/patron")
            else:
                pin_field.error_text = "Code incorrect"
                page.update()

        return ft.Column([
            ft.Container(height=60),
            ft.Icon(ft.icons.DIRECTIONS_BOAT, size=80, color=AppColors.DARK_BLUE),
            ft.Text("K-HAIM BATEAU", size=28, weight=ft.FontWeight.BOLD, color=AppColors.DARK_BLUE),
            ft.Text("Lac Tanganyika", size=14, color=AppColors.TEXT_GRAY),
            ft.Container(height=40),
            ft.ElevatedButton(
                "JE SUIS ÉQUIPAGE",
                icon=ft.icons.GROUPS,
                bgcolor=AppColors.YELLOW, color=AppColors.DARK_BLUE,
                width=280, height=55,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                     text_style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                on_click=go_equipage
            ),
            ft.Container(height=20),
            ft.Text("— ou —", color=AppColors.TEXT_GRAY),
            ft.Container(height=20),
            pin_field,
            ft.Container(height=10),
            ft.ElevatedButton(
                "JE SUIS PATRON",
                icon=ft.icons.ADMIN_PANEL_SETTINGS,
                bgcolor=AppColors.DARK_BLUE, color=AppColors.WHITE,
                width=280, height=55,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                     text_style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                on_click=go_patron
            ),
            ft.Container(height=40)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # ==========================================
    # ROUTING
    # ==========================================
    def route_change(e):
        page.views.clear()
        if page.route == "/route":
            page.views.append(
                ft.View("/route", [view_equipage_route()], bgcolor=AppColors.BG_GRAY, padding=0)
            )
        elif page.route == "/embarquement":
            page.views.append(
                ft.View("/embarquement", [view_embarquement()], bgcolor=AppColors.BG_GRAY, padding=0)
            )
        elif page.route == "/patron":
            page.views.append(
                ft.View("/patron", [view_patron()], bgcolor=AppColors.BG_GRAY, padding=0)
            )
        else:
            page.views.append(
                ft.View("/", [view_login()], bgcolor=AppColors.BG_GRAY, padding=0)
            )
        page.update()

    page.on_route_change = route_change
    page.go("/")

ft.app(target=main)
