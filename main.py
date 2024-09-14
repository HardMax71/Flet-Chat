import flet as ft
from chat.app import ChatApp

def main(page: ft.Page):
    page.window.width = 400
    ChatApp(page)

ft.app(target=main, view=ft.AppView.FLET_APP)