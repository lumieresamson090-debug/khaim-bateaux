import flet as ft

def main(page: ft.Page):
    page.title = "K-HAIM BATEAU"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    page.add(
        ft.Icon(ft.Icons.DIRECTIONS_BOAT_ROUNDED, size=120, color=ft.Colors.BLUE_700),
        ft.Text("K-HAIM BATEAU", size=32, weight=ft.FontWeight.BOLD),
        ft.Text("Uvira - Kalemie - Moba", size=18),
        ft.ElevatedButton("Continuer", icon=ft.Icons.ARROW_FORWARD)
    )

ft.app(target=main)
