# back/sheet/tabGestor/tabStock/tabFrontStock.py
from __future__ import annotations
import flet as ft
from typing import Dict, List, Optional, Callable

# ===== Estilo base =====
ROW_HEIGHT = 88
ROW_SPACING = 8
MIN_ROWS_VISIBLE = 8
MIN_LIST_HEIGHT = ROW_HEIGHT * MIN_ROWS_VISIBLE + ROW_SPACING * (MIN_ROWS_VISIBLE - 1)

RED = "#E53935"
WHITE = ft.Colors.WHITE


# =============================================================
# ===================   ORDENAMIENTO     ======================
# =============================================================

def _apply_sort(grouped: List[Dict], mode: str, sort_mode: str, backend):
    def name_key(g: Dict):
        if mode == "stock":
            p = backend.prod_by_recid.get(g["ID_producto"], {})
            return (p.get("nombre_producto") or "").lower()
        else:
            d = backend.depo_by_recid.get(g["ID_deposito"], {})
            return (d.get("nombre_deposito") or "").lower()

    def qty_key(g: Dict):
        try:
            return int(g.get("total", 0))
        except:
            return 0

    if sort_mode == "name_asc":
        return sorted(grouped, key=name_key)
    if sort_mode == "name_desc":
        return sorted(grouped, key=name_key, reverse=True)
    if sort_mode == "qty_asc":
        return sorted(grouped, key=qty_key)
    if sort_mode == "qty_desc":
        return sorted(grouped, key=qty_key, reverse=True)
    return grouped


# =============================================================
# ==================   LISTA PRINCIPAL ========================
# =============================================================

def render_stock_list(
    *, page, backend, lv, status, query_text,
    view_mode_value, sort_mode_value,
    on_open_product, on_open_deposito, on_open_pending
):
    lv.controls.clear()
    q = (query_text or "").strip().lower()

    # -------- MODO STOCK ----------
    if view_mode_value == "stock":
        grouped = backend.filter_grouped_by_product(q)
        grouped = _apply_sort(grouped, "stock", sort_mode_value, backend)

        for g in grouped:
            pid = g["ID_producto"]
            prod = backend.prod_by_recid.get(pid, {})
            nombre = prod.get("nombre_producto", "(producto)")
            codigo = prod.get("codigo_producto", "-")

            def _open(_, _pid=pid):
                on_open_product(_pid)

            lv.controls.append(
                ft.Container(
                    on_click=_open,
                    ink=True,
                    bgcolor=WHITE,
                    border_radius=10,
                    padding=12,
                    height=ROW_HEIGHT,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column([
                                ft.Text(nombre, size=16, weight=ft.FontWeight.W_600),
                                ft.Text(f"Código: {codigo}", size=11, color=ft.Colors.GREY_600),
                            ]),
                            ft.Text(str(g["total"]), size=18, weight=ft.FontWeight.W_700),
                        ]
                    ),
                )
            )

        page.update()
        return

    # -------- MODO PENDIENTES ---------
    if view_mode_value == "pendientes":
        pending = backend.filter_pending(q) or []

        for r in pending:
            pid = r["ID_producto"]
            did = r["ID_deposito"]

            prod = backend.prod_by_recid.get(pid, {})
            depo = backend.depo_by_recid.get(did, {})

            pname = prod.get("nombre_producto", "(producto)")
            dname = depo.get("nombre_deposito", "(depósito)")
            qty = r.get("cantidad", 0)
            mov = r.get("movimiento", "-")

            def _open(_, _recid=r["RecID"]):
                on_open_pending(_recid)

            lv.controls.append(
                ft.Container(
                    on_click=_open,
                    ink=True,
                    bgcolor=WHITE,
                    border_radius=10,
                    padding=12,
                    height=ROW_HEIGHT,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column([
                                ft.Text(pname, size=16, weight=ft.FontWeight.W_600),
                                ft.Text(f"Depósito: {dname}", size=11, color=ft.Colors.GREY_600),
                                ft.Text(f"Mov: {mov}", size=11, color=ft.Colors.GREY_600),
                            ]),
                            ft.Text(str(qty), size=18, weight=ft.FontWeight.W_700)
                        ]
                    )
                )
            )

        page.update()
        return

    # ---------- MODO DEPÓSITO ----------
    grouped = backend.filter_grouped_by_deposito(q)
    grouped = _apply_sort(grouped, "deposito", sort_mode_value, backend)

    for g in grouped:
        did = g["ID_deposito"]
        d = backend.depo_by_recid.get(did, {})
        nombre = d.get("nombre_deposito", "(depósito)")
        idd = d.get("id_deposito", "-")

        def _open(_, _did=did):
            on_open_deposito(_did)

        lv.controls.append(
            ft.Container(
                on_click=_open,
                ink=True,
                bgcolor=WHITE,
                padding=12,
                border_radius=10,
                height=ROW_HEIGHT,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column([
                            ft.Text(nombre, size=16, weight=ft.FontWeight.W_600),
                            ft.Text(f"ID: {idd}", size=11, color=ft.Colors.GREY_600),
                        ]),
                        ft.Text(str(g["total"]), size=18, weight=ft.FontWeight.W_700)
                    ]
                )
            )
        )

    page.update()


# =============================================================
# ================== PANEL: PENDIENTE =========================
# =============================================================

def _open_pending_panel(page: ft.Page, backend, recid_log: str, on_after_ops):

    # buscar fila
    rows = backend.filter_pending("") or []
    row = next((r for r in rows if r["RecID"] == recid_log), None)
    if not row:
        return

    pid = row["ID_producto"]
    did = row["ID_deposito"]
    qty = row.get("cantidad", 0)
    mov = row.get("movimiento", "-")
    tipo = row.get("tipo_accion", "-")

    prod = backend.prod_by_recid.get(pid, {})
    depo = backend.depo_by_recid.get(did, {})

    producto = prod.get("nombre_producto", "(producto)")
    deposito_actual = depo.get("nombre_deposito", "(depósito)")
    recid_depo_actual = depo.get("RecID", "")

    # ----------------------------------------------------
    #   CAMPO DEPOSITO (DropDown)
    # ----------------------------------------------------
    dd_depo = ft.Dropdown(
        label="Restaurar al depósito",
        width=300,
        value=recid_depo_actual,
        options=[
            ft.dropdown.Option(
                key=d["RecID"],
                text=f"{d.get('id_deposito','')} — {d.get('nombre_deposito','')}"
            )
            for d in backend.depositos
        ]
    )

    # ----------------------------------------------------
    #   BOTONES
    # ----------------------------------------------------
    btn_restore = ft.FilledButton("Restaurar", icon=ft.Icons.RESTORE)
    btn_delete = ft.FilledButton("Descartar", icon=ft.Icons.DELETE, bgcolor=RED, color=WHITE)
    btn_close = ft.OutlinedButton("Cerrar")

    # ----------------------------------------------------
    #   CONFIRMACION DESCARTAR
    # ----------------------------------------------------
    motivos = ["Sin Solucion", "Perdidos", "Destruido", "Regalado", "Otros"]

    dd_motivo = ft.Dropdown(
        label="Motivo de descarte",
        width=300,
        visible=False,
        options=[ft.dropdown.Option(m) for m in motivos]
    )

    motivo_otro = ft.TextField(
        label="Especificar motivo",
        visible=False,
        width=300
    )

    btn_confirm_delete = ft.FilledButton(
        "Confirmar descarte",
        icon=ft.Icons.CHECK,
        bgcolor="#C62828",
        color=WHITE,
        visible=False
    )

    # ----------------------------------------------------
    #   HANDLERS
    # ----------------------------------------------------

    def close(_=None):
        page.close(bs)
        page.update()

    btn_close.on_click = close

    # ----- RESTAURAR -----
    def do_restore(_=None):
        dest_depo = dd_depo.value

        # actualizar stock
        if hasattr(backend, "restore_pending"):
            backend.restore_pending(recid_log, dest_depo)

        # registrar log
        user = page.session.get("user_name") or "User"
        accion = f'{user} Restauro {qty} de "{producto}" en el deposito: "{backend.depo_by_recid.get(dest_depo,{}).get("nombre_deposito","")}"'

        if backend.logger:
            backend.logger.append(accion)

        on_after_ops()
        close()

    btn_restore.on_click = do_restore

    # ----- DESPLEGAR MOTIVOS -----
    def start_delete(_):
        btn_delete.visible = False
        dd_motivo.visible = True
        btn_confirm_delete.visible = True
        page.update()

    btn_delete.on_click = start_delete

    # cuando motivo cambia
    def motivo_changed(_):
        motivo_otro.visible = (dd_motivo.value == "Otros")
        page.update()

    dd_motivo.on_change = motivo_changed

    # ----- DESCARTAR DEFINITIVO -----
    def do_confirm_delete(_=None):
        motivo = dd_motivo.value
        if motivo == "Otros":
            motivo = motivo_otro.value.strip() or "Sin especificar"

        # eliminar
        if hasattr(backend, "delete_pending"):
            backend.delete_pending(recid_log, motivo)

        # registrar log
        user = page.session.get("user_name") or "User"
        accion = (
            f'{user} Descarto {qty} de "{producto}" que estaban en estado "{mov}" '
            f'por el motivo de "{motivo}".'
        )

        if backend.logger:
            backend.logger.append(accion)

        on_after_ops()
        close()

    btn_confirm_delete.on_click = do_confirm_delete

    # ----------------------------------------------------
    #   PANEL VISUAL COMPLETO
    # ----------------------------------------------------
    content = ft.Container(
        padding=16,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[ft.Text("Pendiente", size=20, weight=ft.FontWeight.W_700), btn_close]
                ),
                ft.Divider(),
                ft.Text(f"Producto: {producto}"),
                ft.Text(f"Depósito actual: {deposito_actual}"),
                ft.Text(f"Cantidad: {qty}"),
                ft.Text(f"Movimiento: {mov}"),
                ft.Text(f"Tipo: {tipo}"),
                dd_depo,
                ft.Divider(),
                btn_restore,
                btn_delete,
                dd_motivo,
                motivo_otro,
                btn_confirm_delete
            ]
        )
    )

    bs = ft.BottomSheet(content=content, show_drag_handle=True, is_scroll_controlled=True)
    page.open(bs)


# =============================================================
# ============= PANELS DE PRODUCTO Y DEPÓSITO =================
# =============================================================

# Todo tu código original de los paneles queda igual:
# (NO lo reescribo aquí por espacio, pero ESTÁ COMPLETO
#  en tu versión previa y es totalmente compatible)

# =============================================================
# ==================  VISTA PRINCIPAL  ========================
# =============================================================

def build_stock_tab(page, backend, bus=None,
                    initial_view="stock", initial_sort="name_asc"):

    backend.refresh_all()

    view_mode = {"value": initial_view}
    sort_mode = {"value": initial_sort}

    lv = ft.ListView(spacing=ROW_SPACING, expand=True)

    # ----------------- Paint toggle -----------------
    def _segment(label, active):
        return ft.Container(
            bgcolor=RED if active else ft.Colors.TRANSPARENT,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=8,
            content=ft.Text(
                label,
                size=12,
                weight=ft.FontWeight.W_600,
                color=WHITE if active else ft.Colors.BLACK87,
            ),
        )

    def _paint_toggle():
        cur = view_mode["value"]
        return ft.Container(
            bgcolor=ft.Colors.GREY_100,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=999,
            padding=4,
            content=ft.Row(
                spacing=4,
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    ft.Container(
                        on_click=lambda _: _set_mode("stock"),
                        content=_segment("Stock", cur == "stock"),
                    ),
                    ft.Container(
                        on_click=lambda _: _set_mode("deposito"),
                        content=_segment("Depósito", cur == "deposito"),
                    ),
                    ft.Container(
                        on_click=lambda _: _set_mode("pendientes"),
                        content=_segment("Pendientes", cur == "pendientes"),
                    ),
                ],
            ),
        )

    def _set_mode(m):
        view_mode["value"] = m
        toggle_holder.content = _paint_toggle()
        _render()
        page.update()

    toggle_holder = ft.Container(content=_paint_toggle())

    # ----------------- Ordenamiento -----------------
    def _set_sort(m):
        sort_mode["value"] = m
        _render()

    filter_btn = ft.PopupMenuButton(
        icon=ft.Icons.FILTER_LIST,
        items=[
            ft.PopupMenuItem(text="Nombre A–Z", on_click=lambda _: _set_sort("name_asc")),
            ft.PopupMenuItem(text="Nombre Z–A", on_click=lambda _: _set_sort("name_desc")),
            ft.PopupMenuItem(text="Cantidad ↑", on_click=lambda _: _set_sort("qty_asc")),
            ft.PopupMenuItem(text="Cantidad ↓", on_click=lambda _: _set_sort("qty_desc")),
        ],
    )

    # ----------------- Buscador -----------------
    search = ft.TextField(
        hint_text="Buscar...",
        prefix_icon=ft.Icons.SEARCH,
        filled=True,
        bgcolor=WHITE,
        border_radius=12,
        border_color=RED,
        focused_border_color=RED,
        content_padding=10,
        on_change=lambda _: _render(),
        expand=True,
    )

    # ---------------- Aperturas ----------------
    def _open_product(pid):
        _open_product_panel(page, backend, pid, _render)

    def _open_deposito(did):
        _open_deposito_panel(page, backend, did, _render)

    def _open_pending(rid):
        _open_pending_panel(page, backend, rid, _render)

    # ---------------- Render final ----------------
    def _render():
        render_stock_list(
            page=page,
            backend=backend,
            lv=lv,
            status=None,
            query_text=search.value or "",
            view_mode_value=view_mode["value"],
            sort_mode_value=sort_mode["value"],
            on_open_product=_open_product,
            on_open_deposito=_open_deposito,
            on_open_pending=_open_pending,
        )

    # =====================================================
    #   FUNCIÓN PARA AGREGAR (+)
    # =====================================================
    def _open_add_global(_):
        from flet import Dropdown, dropdown, TextField, FilledButton, OutlinedButton, BottomSheet, Column, Container, Text, Row

        dd_prod = Dropdown(
            label="Producto",
            width=350,
            options=[
                dropdown.Option(
                    key=p["RecID"],
                    text=f'{p["codigo_producto"]} — {p["nombre_producto"]}'
                )
                for p in backend.productos
            ]
        )

        dd_depo = Dropdown(
            label="Depósito",
            width=350,
            options=[
                dropdown.Option(
                    key=d["RecID"],
                    text=f'{d["id_deposito"]} — {d["nombre_deposito"]}'
                )
                for d in backend.depositos
            ]
        )

        txt_qty = TextField(
            label="Cantidad",
            width=150,
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True, regex_string=r"[0-9]", replacement_string=""
            ),
        )

        btn_ok = FilledButton("Agregar", icon=ft.Icons.CHECK)
        btn_cancel = OutlinedButton("Cancelar")

        def close(_=None):
            page.close(bs)
            page.update()

        def do_add(_):
            pid = dd_prod.value
            did = dd_depo.value

            if not pid or not did:
                page.snack_bar = ft.SnackBar(ft.Text("Seleccione producto y depósito."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                qty = int(txt_qty.value)
            except:
                qty = 0

            if qty <= 0:
                page.snack_bar = ft.SnackBar(ft.Text("Cantidad inválida."))
                page.snack_bar.open = True
                page.update()
                return

            backend.add_new_stock(
                pid,
                did,
                qty,
                backend.prod_by_recid[pid]["nombre_producto"],
                backend.depo_by_recid[did]["nombre_deposito"],
            )

            backend.refresh_all()
            _render()
            close()

        btn_ok.on_click = do_add
        btn_cancel.on_click = close

        content = Container(
            padding=16,
            content=Column(
                spacing=12,
                controls=[
                    Text("Agregar nuevo stock", size=20, weight=ft.FontWeight.BOLD),
                    dd_prod,
                    dd_depo,
                    txt_qty,
                    Row(alignment=ft.MainAxisAlignment.END, controls=[btn_cancel, btn_ok]),
                ],
            ),
        )

        bs = BottomSheet(content=content, show_drag_handle=True, is_scroll_controlled=True)
        page.open(bs)

    # =====================================================
    #           HEADER FINAL con BOTÓN (+)
    # =====================================================
    add_btn = ft.IconButton(
        icon=ft.Icons.ADD_CIRCLE,
        icon_size=28,
        tooltip="Agregar nuevo stock",
        on_click=_open_add_global
    )

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            # IZQUIERDA: "Stock" + (+)
            ft.Row(
                spacing=8,   # ← separa un poquito, sin alejarlo demasiado
                controls=[
                    ft.Text("Stock", size=22, weight=ft.FontWeight.W_700),
                    add_btn
                ]
            ),

            # DERECHA: toggle
            toggle_holder
        ]
    )

    # =====================================================
    #           ROOT FINAL
    # =====================================================
    topbar = ft.Row(
    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    controls=[
        ft.Container(
            expand=True,
            content=search
        ),
        ft.Container(
            padding=ft.padding.only(left=10),
            content=filter_btn
        )
    ]
)

# ----------- ROOT FINAL -----------
    root = ft.Container(
        bgcolor=ft.Colors.GREY_50,
        content=ft.Column(
            spacing=4,
            controls=[
                header,     # Stock + (+) + toggle a la derecha
                topbar,     # buscador + filtro en la MISMA línea
                lv          # lista
            ]
        )
    )

    _render()
    return root
    # ----------- BUSCADOR + FILTRO (MISMA LÍNEA) -----------
    topbar = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Container(
                expand=True,
                content=search
            ),

            ft.Container(
                padding=ft.padding.only(left=10),
                content=filter_btn
            )
        ]
    )


def _open_product_panel(page: ft.Page, backend, prod_recid: str, on_after_ops: Callable[[], None]):
    """Panel por PRODUCTO: lista depósitos con ese producto y acciones dinámicas."""
    rows_prod = backend.rows_for_product(prod_recid)
    prod = backend.prod_by_recid.get(prod_recid, {}) or {}
    nombre_prod = prod.get("nombre_producto", "") or "(producto desconocido)"
    codigo_prod = prod.get("codigo_producto", "") or "-"

    selected_row: Dict | None = None
    list_col = ft.Column(spacing=8, expand=True)
    row_wrappers: List[ft.Container] = []

    # ---- Botones de acción (inicialmente ocultos) ----
    btn_add = ft.FilledButton(
        "Agregar",
        icon=ft.Icons.ADD,
        style=ft.ButtonStyle(bgcolor=RED, color=WHITE),
        visible=False,
    )
    btn_move = ft.FilledButton(
        "Mover",
        icon=ft.Icons.SWAP_HORIZ,
        style=ft.ButtonStyle(bgcolor=RED, color=WHITE),
        visible=False,
    )
    btn_out = ft.FilledButton(
        "Descargar",
        icon=ft.Icons.REMOVE,
        style=ft.ButtonStyle(bgcolor=RED, color=WHITE),
        visible=False,
    )

    # ---- Botón Cerrar modernizado ----
    btn_close = ft.OutlinedButton(
        text="Cerrar",
        icon=ft.Icons.CLOSE,
        on_click=lambda _: _close_bs(),
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=10),
            side=ft.BorderSide(width=2, color=ft.Colors.GREY_600),
            color=ft.Colors.BLACK87,
        ),
    )

    # ---- Función para seleccionar fila ----
    def make_row_item(row: Dict):
        d = backend.depo_by_recid.get(row.get("ID_deposito", ""), {}) or {}
        nom_depo = d.get("nombre_deposito", "") or "(depósito desconocido)"
        id_depo = d.get("id_deposito", "") or "-"
        qty = row.get("cantidad", "0") or "0"

        chip = ft.Container(
            bgcolor=ft.Colors.GREY_50,
            border_radius=8,
            padding=10,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(nom_depo, size=14, weight=ft.FontWeight.W_600),
                            ft.Text(f"ID: {id_depo}", size=11, color=ft.Colors.GREY_600),
                        ]
                    ),
                    ft.Text(str(qty), size=16, weight=ft.FontWeight.W_700),
                ],
            ),
        )

        wrapper = ft.Container(content=chip)
        wrapper.data = row
        row_wrappers.append(wrapper)

        def on_select(_):
            nonlocal selected_row
            selected_row = wrapper.data

            # limpiar selección previa
            for w in row_wrappers:
                w.border = None

            wrapper.border = ft.border.all(2, ft.Colors.BLUE_300)

            # mostrar botones recién ahora
            btn_add.visible = True
            btn_move.visible = True
            btn_out.visible = True
            page.update()

        wrapper.on_click = on_select
        return wrapper

    for rp in rows_prod:
        list_col.controls.append(make_row_item(rp))

    # ---- Layout completo del panel ----
    content = ft.Container(
        padding=16,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Column(
            spacing=12,
            controls=[
                # Título + botón cerrar alineados correctamente
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(nombre_prod, size=18, weight=ft.FontWeight.W_700),
                                ft.Text(f"Código: {codigo_prod}", size=12, color=ft.Colors.GREY_700),
                            ]
                        ),
                        btn_close,
                    ],
                ),

                # Separador solicitado
                ft.Divider(height=1, color=ft.Colors.GREY_300),

                ft.Text("Depósitos del producto", size=14, weight=ft.FontWeight.W_600),
                list_col,

                ft.Divider(),

                # Botones que aparecen dinámicamente
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    controls=[btn_add, btn_move, btn_out],
                ),
            ],
        ),
    )

    bs = ft.BottomSheet(content=content, show_drag_handle=True, is_scroll_controlled=True, elevation=8)
    page.open(bs)

    def _close_bs(_=None):
        try:
            page.close(bs)
        except Exception:
            bs.open = False
        page.update()

    # ---- Acciones ----
    def on_add(_=None):
        if not selected_row:
            return
        r = selected_row
        depo = backend.depo_by_recid.get(r.get("ID_deposito", ""), {}) or {}
        depo_name = depo.get("nombre_deposito", "(depósito)")

        def _do(n: int):
            backend.add_qty(r.get("RecID", ""), n, nombre_prod, depo_name)
            backend.refresh_all()
            on_after_ops()
            _close_bs()

        _open_qty_bs(page, "Agregar cantidad", "Agregar", _do)

    def on_out(_=None):
        if not selected_row:
            return
        r = selected_row
        depo = backend.depo_by_recid.get(r.get("ID_deposito", ""), {}) or {}

        def _do(n: int):
            backend.descargar(r.get("RecID", ""), n, nombre_prod, depo.get("nombre_deposito", "(depósito)"))
            backend.refresh_all()
            on_after_ops()
            _close_bs()

        _open_qty_bs(page, "Descargar cantidad", "Descargar", _do)

    def on_move(_=None):
        if not selected_row:
            return

        r = selected_row
        origin_recid = r.get("ID_deposito", "")
        recid_stock = r.get("RecID", "")
        available_qty = backend.safe_int(r.get("cantidad", 0))

        pdepo = backend.depo_by_recid.get(origin_recid, {}) or {}
        origin_name = pdepo.get("nombre_deposito", "(depósito)")

        def _do(dest_recid: str, n: int):
            dest_d = backend.depo_by_recid.get(dest_recid, {}) or {}
            backend.move_add_row(
                r.get("RecID", ""),
                dest_recid,
                n,
                nombre_prod,
                origin_name,
                dest_d.get("nombre_deposito", "(depósito)"),
            )
            backend.refresh_all()
            on_after_ops()
            _close_bs()
        # refrescar UI luego de cualquier movimiento
        def after_refresh():
            backend.refresh_all()
            on_after_ops()
            _close_bs()
        _open_move_bs(
            page=page,
            backend=backend,
            origin_recid=origin_recid,
            origin_name=origin_name,
            prod_name=nombre_prod,
            recid_stock=recid_stock,
            available_qty=available_qty,
            on_after_ops=after_refresh
        )
    btn_add.on_click = on_add
    btn_out.on_click = on_out
    btn_move.on_click = on_move


def _open_deposito_panel(page: ft.Page, backend, depo_recid: str, on_after_ops: Callable[[], None]):
    """Panel por DEPÓSITO: lista items en ese depósito y acciones dinámicas."""

    rows_depo = backend.rows_for_deposito(depo_recid)
    depo = backend.depo_by_recid.get(depo_recid, {}) or {}

    nombre_depo = depo.get("nombre_deposito", "") or "(depósito desconocido)"
    id_depo = depo.get("id_deposito", "") or "-"

    selected_row: Dict | None = None
    row_wrappers: List[ft.Container] = []

    # ==== BOTONES (inicialmente invisibles) ====
    btn_add = ft.FilledButton("Agregar", icon=ft.Icons.ADD,
                              style=ft.ButtonStyle(bgcolor=RED, color=WHITE),
                              visible=False)
    btn_move = ft.FilledButton("Mover", icon=ft.Icons.SWAP_HORIZ,
                               style=ft.ButtonStyle(bgcolor=RED, color=WHITE),
                               visible=False)
    btn_out = ft.FilledButton("Descargar", icon=ft.Icons.REMOVE,
                              style=ft.ButtonStyle(bgcolor=RED, color=WHITE),
                              visible=False)

    # ==== BOTÓN CERRAR ====
    def _close_bs(_=None):
        try:
            page.close(bs)
        except:
            bs.open = False
        page.update()

    btn_close = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.all(2, ft.Colors.GREY_400),
        border_radius=8,
        on_click=_close_bs,
        content=ft.Text("Cerrar", size=12, weight=ft.FontWeight.W_500),
    )

    # ==== LISTA ====
    list_col = ft.Column(spacing=8)

    def make_row_item(row: Dict):
        p = backend.prod_by_recid.get(row.get("ID_producto", ""), {}) or {}
        nom_prod = p.get("nombre_producto", "") or "(producto desconocido)"
        codigo_prod = p.get("codigo_producto", "") or "-"
        qty = row.get("cantidad", "0") or "0"

        chip = ft.Container(
            bgcolor=ft.Colors.GREY_50,
            border_radius=8,
            padding=10,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(nom_prod, size=14, weight=ft.FontWeight.W_600),
                            ft.Text(f"Código: {codigo_prod}", size=11, color=ft.Colors.GREY_600),
                        ]
                    ),
                    ft.Text(str(qty), size=16, weight=ft.FontWeight.W_700),
                ],
            ),
        )

        wrapper = ft.Container(content=chip)
        wrapper.data = row
        row_wrappers.append(wrapper)

        def on_select(_):
            nonlocal selected_row
            selected_row = wrapper.data

            # limpiar selección
            for w in row_wrappers:
                w.border = None

            wrapper.border = ft.border.all(2, ft.Colors.BLUE_300)

            # mostrar botones
            btn_add.visible = True
            btn_move.visible = True
            btn_out.visible = True

            page.update()

        wrapper.on_click = on_select
        return wrapper

    for rp in rows_depo:
        list_col.controls.append(make_row_item(rp))

    scroll_area = ft.Container(
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[list_col]
        ),
    )

    # ==== LAYOUT ====
    content = ft.Container(
        padding=16,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Column(
            spacing=12,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(nombre_depo, size=18, weight=ft.FontWeight.W_700),
                                ft.Text(f"ID: {id_depo}", size=12, color=ft.Colors.GREY_700),
                            ]
                        ),
                        btn_close,
                    ],
                ),
                ft.Divider(),
                ft.Text("Items en el depósito", size=14, weight=ft.FontWeight.W_600),
                scroll_area,
                ft.Divider(),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    controls=[btn_add, btn_move, btn_out],
                ),
            ],
        ),
    )

    bs = ft.BottomSheet(
        content=content,
        show_drag_handle=True,
        is_scroll_controlled=True,
        elevation=8,
    )
    page.open(bs)

    # ======================================================
    #     ACCIONES
    # ======================================================

    def on_add(_=None):
        if not selected_row:
            return

        r = selected_row

        def _do(n: int):
            backend.add_qty(r["RecID"], n, "", nombre_depo)
            backend.refresh_all()
            on_after_ops()
            _close_bs()

        _open_qty_bs(page, "Agregar cantidad", "Agregar", _do)

    def on_out(_=None):
        if not selected_row:
            return

        r = selected_row

        def _do(n: int):
            backend.descargar(r["RecID"], n, "", nombre_depo)
            backend.refresh_all()
            on_after_ops()
            _close_bs()

        _open_qty_bs(page, "Descargar cantidad", "Descargar", _do)

    def on_move(_=None):
        if not selected_row:
            return

        r = selected_row
        origin_name = nombre_depo
        origin_recid = r["ID_deposito"]

        p = backend.prod_by_recid.get(r["ID_producto"], {}) or {}
        prod_name = p.get("nombre_producto", "") or "(producto)"

        # callback correcto (sin parámetros)
        def after_refresh():
            backend.refresh_all()
            on_after_ops()
            _close_bs()

        _open_move_bs(
            page=page,
            backend=backend,
            origin_recid=origin_recid,
            origin_name=origin_name,
            prod_name=prod_name,
            recid_stock=r.get("RecID", ""),
            available_qty=backend.safe_int(r.get("cantidad", 0)),
            on_after_ops=after_refresh,
        )

    btn_add.on_click = on_add
    btn_out.on_click = on_out
    btn_move.on_click = on_move

def _open_qty_bs(page, title, ok_label, on_ok):
    t_qty = ft.TextField(
        label="Cantidad",
        width=220,
        value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(
            allow=True,
            regex_string=r"[0-9]",
            replacement_string=""
        ),
    )

    busy = ft.ProgressBar(visible=False, width=220)
    ok_btn = ft.FilledButton(ok_label, icon=ft.Icons.CHECK)
    cancel = ft.OutlinedButton("Cancelar")

    inner = ft.Container(
        padding=16,
        bgcolor=ft.Colors.WHITE,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text(title, size=18, weight=ft.FontWeight.W_700),
                t_qty,
                busy,
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[cancel, ok_btn]),
            ],
        ),
    )

    bs = ft.BottomSheet(content=inner, show_drag_handle=True)
    page.open(bs)

    def close(_=None):
        page.close(bs)
        page.update()

    def confirm(_=None):
        try:
            n = int(t_qty.value)
        except:
            n = 0

        if n <= 0:
            page.snack_bar = ft.SnackBar(ft.Text("Cantidad inválida."))
            page.snack_bar.open = True
            page.update()
            return

        on_ok(n)
        close()

    ok_btn.on_click = confirm
    cancel.on_click = close



def _open_move_bs(
    page: ft.Page,
    backend,
    *,
    origin_recid: str,     # RecID del depósito origen
    origin_name: str,      # nombre del depósito origen
    prod_name: str,        # nombre del producto
    recid_stock: str,      # RecID de la fila de stock origen
    available_qty: int,    # cantidad disponible
    on_after_ops=None,
):
    """Panel mover: depósito destino + opción Enviar Pendiente (logsAcn)."""

    # ======================================================
    #   ARMAR LISTA DE DESTINOS
    # ======================================================
    dest_options = [
        ft.dropdown.Option(
            key=d["RecID"],
            text=f'{d["id_deposito"]} — {d["nombre_deposito"]}'
        )
        for d in backend.depositos
        if d["RecID"] != origin_recid
    ]

    # -------- Opción extra --------
    OUT_KEY = "OUT_SYSTEM"
    OUT_LABEL = "--Enviar Pendiente--"

    dest_options.append(
        ft.dropdown.Option(key=OUT_KEY, text=OUT_LABEL)
    )

    dd_dest = ft.Dropdown(
        label="Mover a:",
        width=420,
        options=dest_options
    )

    # ======================================================
    #   CAMPOS PARA “Enviar Pendiente”
    # ======================================================
    motivos = ["Reparación", "Prestado", "Enviado", "Perdido", "Otros"]

    dd_motivo = ft.Dropdown(
        label="Motivo",
        width=420,
        visible=False,
        options=[ft.dropdown.Option(m) for m in motivos]
    )

    txt_otro = ft.TextField(
        label="Especifique motivo",
        width=420,
        visible=False
    )

    t_qty = ft.TextField(
        label=f"Cantidad (max {available_qty})",
        width=200,
        value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.InputFilter(
            allow=True,
            regex_string=r"[0-9]",
            replacement_string=""
        ),
    )

    btn_ok = ft.FilledButton("Mover", icon=ft.Icons.CHEVRON_RIGHT)
    btn_cancel = ft.OutlinedButton("Cancelar")

    # ======================================================
    #   DESTINO CAMBIADO
    # ======================================================
    def on_dest_change(_):
        if dd_dest.value == OUT_KEY:
            dd_motivo.visible = True
            txt_otro.visible = False
        else:
            dd_motivo.visible = False
            txt_otro.visible = False

        page.update()

    dd_dest.on_change = on_dest_change

    # ======================================================
    #   MOTIVO CAMBIADO
    # ======================================================
    def on_motivo_change(_):
        txt_otro.visible = (dd_motivo.value == "Otros")
        page.update()

    dd_motivo.on_change = on_motivo_change

    # ======================================================
    #   CONFIRMAR
    # ======================================================
    def do_confirm(_):
        dest = dd_dest.value
        if not dest:
            page.snack_bar = ft.SnackBar(ft.Text("Seleccione un destino."))
            page.snack_bar.open = True
            page.update()
            return

        # ---------- cantidad ----------
        try:
            n = int(t_qty.value)
        except:
            n = 0

        if n <= 0 or n > available_qty:
            page.snack_bar = ft.SnackBar(ft.Text(f"Cantidad inválida. Máximo: {available_qty}"))
            page.snack_bar.open = True
            page.update()
            return

        # ============================================================
        #   CASO 1 — MOVER ENTRE DEPÓSITOS NORMALES
        # ============================================================
        if dest != OUT_KEY:
            dest_name = backend.depo_by_recid.get(dest, {}).get("nombre_deposito", "(depósito)")
            backend.move_add_row(
                recid_stock,
                dest,
                n,
                prod_name,
                origin_name,
                dest_name
            )
            backend.refresh_all()
            if on_after_ops:
                on_after_ops()
            close()
            return

        # ============================================================
        #   CASO 2 — ENVIAR PENDIENTE (LogsAcn)
        # ============================================================
        motivo = dd_motivo.value
        if motivo == "Otros":
            motivo = txt_otro.value.strip() or "Sin especificar"

        # Registrar en logsAcn (universal)
        data = {
            "ID_producto": backend.stock_rows_by_recid[recid_stock]["ID_producto"],
            "ID_deposito": origin_recid,
            "cantidad": n,
            "movimiento": motivo,
            "tipo_accion": "pendiente",
        }

        api = backend.api_logsAcn

        if hasattr(api, "add"):
            api.add(**data)
        elif hasattr(api, "append"):
            api.append(**data)
        elif hasattr(api, "insert"):
            api.insert(data)
        elif hasattr(api, "create"):
            api.create(data)
        elif hasattr(api, "add_row"):
            api.add_row(data)
        else:
            print("[ERROR] logsAcn API sin método válido")
            page.snack_bar = ft.SnackBar(ft.Text("No se pudo guardar en logsAcn."))
            page.snack_bar.open = True
            page.update()
            return

        # descontar del depósito
        backend.descargar(recid_stock, n, prod_name, origin_name)

        backend.refresh_all()
        if on_after_ops:
            on_after_ops()
        close()

    btn_ok.on_click = do_confirm

    # ======================================================
    #   PANEL FINAL
    # ======================================================
    inner = ft.Container(
        padding=16,
        bgcolor=ft.Colors.WHITE,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text(f"Mover \"{prod_name}\"", size=18, weight=ft.FontWeight.W_700),
                ft.Text(f"Desde: {origin_name}", size=12, color=ft.Colors.GREY_700),

                dd_dest,
                dd_motivo,
                txt_otro,
                t_qty,

                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[btn_cancel, btn_ok],
                )
            ]
        )
    )

    bs = ft.BottomSheet(content=inner, show_drag_handle=True, is_scroll_controlled=True)
    page.open(bs)

    def close(_=None):
        try:
            page.close(bs)
        except:
            bs.open = False
        page.update()

    btn_cancel.on_click = close
