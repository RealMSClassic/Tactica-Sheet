# back/sheet/tabGestor/gestorMain.py
from __future__ import annotations
import flet as ft
import threading

from back.sheet.tabGestor.event_bus import EventBus

from back.sheet.tabGestor.tabDeposito.tabBackDeposito import DepositoBackend
from back.sheet.tabGestor.tabDeposito.tabFrontDeposito import build_deposito_tab

from back.sheet.tabGestor.tabItems.tabBackItems import ItemsBackend
from back.sheet.tabGestor.tabItems.tabFrontItems import build_items_tab

from back.sheet.tabGestor.tabStock.tabBackStock import StockBackend
from back.sheet.tabGestor.tabStock.tabFrontStock import build_stock_tab


PRIMARY = "#4B39EF"


def gestor_view(page: ft.Page) -> ft.Control:

    bus = EventBus()

    depo_backend = DepositoBackend(page, bus=bus)
    items_backend = ItemsBackend(page, bus=bus)
    stock_backend = StockBackend(page, bus=bus, depo_backend=depo_backend, items_backend=items_backend)

    # ==============================================================
    #   BARRA HORIZONTAL DE CARGA
    # ==============================================================
    loading_bar = ft.ProgressBar(
        visible=False,
        value=None,
        height=4,
        color=PRIMARY
    )

    # ==============================================================
    #   CONTENEDOR DE LAS PESTAÑAS
    # ==============================================================
    content_container = ft.Container(
        expand=True,
        padding=0,
        content=ft.Text("Cargando...", size=20)
    )

    # ==============================================================
    #   LOADERS
    # ==============================================================
    def load_stock():
        ui = build_stock_tab(page, stock_backend, bus=bus)
        ui.disabled = False
        ui.expand = True
        return ui

    def load_deposito():
        ui = build_deposito_tab(page, depo_backend, bus=bus)
        ui.disabled = False
        ui.expand = True
        return ui

    def load_items():
        ui = build_items_tab(page, items_backend, bus=bus)
        ui.disabled = False
        ui.expand = True
        return ui

    # ==============================================================
    #   MANEJO DE CARGA
    # ==============================================================
    def set_loading(state: bool):
        tabs_blocker.disabled = state
        content_container.disabled = state
        loading_bar.visible = state
        page.update()

    def async_load(loader):
        def run():
            try:
                new_ui = loader()
                content_container.content = new_ui
            except Exception as e:
                content_container.content = ft.Text(f"[ERROR] {e}", color=ft.Colors.RED_700)
            finally:
                set_loading(False)

        threading.Thread(target=run, daemon=True).start()

    # ==============================================================
    #   CAMBIO DE TAB
    # ==============================================================
    def on_tab_change(e):
        idx = tabs.selected_index
        set_loading(True)

        if idx == 0:
            async_load(load_stock)
        elif idx == 1:
            async_load(load_deposito)
        elif idx == 2:
            async_load(load_items)

    # ==============================================================
    #   TABS
    # ==============================================================
    tabs = ft.Tabs(
    selected_index=0,
    on_change=on_tab_change,
    height=55,
    tab_alignment=ft.TabAlignment.START,
    indicator_color=PRIMARY,
    tabs=[
        ft.Tab(text="Stock"),
        ft.Tab(text="Depósito"),
        ft.Tab(text="Items"),
    ]
)

    # CONTENEDOR QUE BLOQUEA CLICKS
    tabs_blocker = ft.Container(
        content=tabs,
        disabled=False   # ← Este se controla dinámicamente
    )

    # ==============================================================
    #   CARGA INICIAL
    # ==============================================================
    set_loading(True)
    async_load(load_stock)

    # ==============================================================
    #   LAYOUT FINAL
    # ==============================================================
    return ft.Container(
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[
                tabs_blocker,
                loading_bar,
                ft.Divider(height=1),
                content_container
            ]
        )
    )
