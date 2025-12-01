# back/sheet/tabGestor/tabStock/tabBackStock.py
from __future__ import annotations
from typing import List, Dict, Optional

from back.sheet.logsAcn_api import LogsAcnAPI

try:
    # APIs reales
    from back.sheet.stock_api import StockAPI
    from back.sheet.producto_api import ProductoAPI
    from back.sheet.deposito_api import DepositoAPI
    from back.sheet.log_api import LogAPI, fmt_stock_move, fmt_stock_out, fmt_stock_add
except Exception:
    # fallback para desarrollo
    StockAPI = ProductoAPI = DepositoAPI = LogAPI = None
    def fmt_stock_move(n, p, o, d): return f"[MOVE] {n} {p} {o}->{d}"
    def fmt_stock_out(n, p, d):     return f"[OUT]  {n} {p} {d}"
    def fmt_stock_add(n, p, d):     return f"[ADD]  {n} {p} {d}"


class StockBackend:

    def __init__(
        self,
        page,
        bus: Optional[object] = None,
        depo_backend: Optional[object] = None,
        items_backend: Optional[object] = None,
    ):
        self.page = page
        self.bus = bus
        self.depo_backend = depo_backend
        self.items_backend = items_backend

        self.sheet_id = (
            page.client_storage.get("active_sheet_id")
            or getattr(getattr(page, "app_ctx", {}), "get", lambda *_: None)("sheet", {}).get("id", "")
        )

        self.api_stock = StockAPI(page, self.sheet_id) if StockAPI else None
        self.api_prod  = ProductoAPI(page, self.sheet_id) if ProductoAPI else None
        self.api_depo  = DepositoAPI(page, self.sheet_id) if DepositoAPI else None
        self.api_logsAcn = LogsAcnAPI(page, self.sheet_id)
        self.logger    = LogAPI(page, self.sheet_id) if LogAPI else None

        # caches
        self.productos: List[Dict] = []
        self.depositos: List[Dict] = []
        self.stock_rows: List[Dict] = []

        self.prod_by_recid: Dict[str, Dict] = {}
        self.depo_by_recid: Dict[str, Dict] = {}

        self.pending_rows: List[Dict] = []

    # -------------------------------------------------
    # UTILS
    # -------------------------------------------------
    @staticmethod
    def safe_int(v) -> int:
        try:
            return int(str(v).strip() or "0")
        except:
            return 0

    def attach_page(self, page):
        self.page = page

    # -------------------------------------------------
    # REFRESH
    # -------------------------------------------------
    def refresh_products(self):
        if self.items_backend and getattr(self.items_backend, "productos", None):
            self.productos = list(self.items_backend.productos or [])
            self.prod_by_recid = dict(self.items_backend.prod_by_recid or {})
            return

        if not self.api_prod:
            self.productos = []
            self.prod_by_recid = {}
            return

        self.productos = self.api_prod.list() or []
        self.prod_by_recid = {p["RecID"]: p for p in self.productos}

    def refresh_depositos(self):
        if self.depo_backend and getattr(self.depo_backend, "depositos", None):
            self.depositos = list(self.depo_backend.depositos or [])
            self.depo_by_recid = dict(self.depo_backend.depo_by_recid or {})
            return

        if not self.api_depo:
            self.depositos = []
            self.depo_by_recid = {}
            return

        self.depositos = self.api_depo.list() or []
        self.depo_by_recid = {d["RecID"]: d for d in self.depositos}

    def refresh_stock(self):
        if not self.api_stock:
            self.stock_rows = []
            self.stock_rows_by_recid = {}
            return

        self.stock_rows = self.api_stock.list() or []

        # 🔥 NUEVO → mapa por RecID
        self.stock_rows_by_recid = {
            r.get("RecID", ""): r
            for r in self.stock_rows
            if r.get("RecID")
        }

    def refresh_pending(self):
        """Carga todos los pendientes desde logsAcn_api."""
        try:
            rows = self.api_logsAcn.list()
            self.pending_rows = rows or []
        except Exception as e:
            print("[ERROR] refresh_pending:", e)
            self.pending_rows = []

    def refresh_all(self):
        self.refresh_products()
        self.refresh_depositos()
        self.refresh_stock()
        self.refresh_pending()

    # -------------------------------------------------
    # FILTROS
    # -------------------------------------------------
    def _aggregate_by_product(self, rows):
        agg = {}
        for r in rows:
            pid = r.get("ID_producto", "")
            if not pid:
                continue
            agg[pid] = agg.get(pid, 0) + self.safe_int(r.get("cantidad"))
        return [{"ID_producto": k, "total": v} for k, v in agg.items()]

    def _aggregate_by_deposito(self, rows):
        agg = {}
        for r in rows:
            did = r.get("ID_deposito", "")
            if not did:
                continue
            agg[did] = agg.get(did, 0) + self.safe_int(r.get("cantidad"))
        return [{"ID_deposito": k, "total": v} for k, v in agg.items()]

    def filter_grouped_by_product(self, q: str):
        grouped = self._aggregate_by_product(self.stock_rows)
        if not q:
            return grouped

        ql = q.lower()
        out = []
        for g in grouped:
            p = self.prod_by_recid.get(g["ID_producto"], {}) or {}
            if ql in (p.get("nombre_producto", "").lower() or "") or \
               ql in (p.get("codigo_producto", "").lower() or ""):
                out.append(g)
        return out

    def filter_grouped_by_deposito(self, q: str):
        grouped = self._aggregate_by_deposito(self.stock_rows)
        if not q:
            return grouped

        ql = q.lower()
        out = []
        for g in grouped:
            d = self.depo_by_recid.get(g["ID_deposito"], {}) or {}
            if ql in (d.get("nombre_deposito", "").lower()) or \
               ql in (d.get("id_deposito", "").lower()):
                out.append(g)
        return out

    def rows_for_product(self, pid: str):
        return [
            r for r in self.stock_rows
            if r.get("ID_producto") == pid and self.safe_int(r.get("cantidad")) > 0
        ]

    def rows_for_deposito(self, did: str):
        return [
            r for r in self.stock_rows
            if r.get("ID_deposito") == did and self.safe_int(r.get("cantidad")) > 0
        ]

    # -------------------------------------------------
    #  PUBLICAR EVENTO
    # -------------------------------------------------
    def _publish(self, topic: str, payload: Optional[dict] = None):
        if not self.bus:
            return
        try:
            self.bus.publish(topic, payload or {})
        except:
            pass

    # -------------------------------------------------
    # STOCK
    # -------------------------------------------------
    def add_new_stock(self, item_recid, depo_recid, qty, product_name="", depo_name=""):
        if not self.api_stock:
            return None

        recid = self.api_stock.add(ID_producto=item_recid, ID_deposito=depo_recid, cantidad=qty)

        if self.logger:
            self.logger.append(fmt_stock_add(qty, product_name, depo_name))

        self._publish("stock_changed", {"op": "add_new", "recid": recid})
        return recid

    def add_qty(self, recid_stock, delta, product_name="", depo_name=""):
        if not self.api_stock:
            return False

        ok = self.api_stock.add_qty(recid_stock, delta)
        if ok and self.logger:
            self.logger.append(fmt_stock_add(delta, product_name, depo_name))

        self._publish("stock_changed", {"op": "add_qty", "recid": recid_stock})
        return ok

    def descargar(self, recid_stock, n, product_name="", depo_name=""):
        if not self.api_stock:
            return False

        ok = self.api_stock.descargar(recid_stock, n)
        if ok and self.logger:
            self.logger.append(fmt_stock_out(n, product_name, depo_name))

        self._publish("stock_changed", {"op": "descargar", "recid": recid_stock})
        return ok

    def move_add_row(self, recid_stock_src, recid_deposito_dest, n,
                     product_name="", origin_name="", dest_name=""):
        if not self.api_stock:
            return False

        ok = self.api_stock.move_add_row(recid_stock_src, recid_deposito_dest, n)
        if ok and self.logger:
            self.logger.append(fmt_stock_move(n, product_name, origin_name, dest_name))

        self._publish("stock_changed", {"op": "move_add_row"})
        return ok

    # -------------------------------------------------
    # PENDIENTES
    # -------------------------------------------------
    def filter_pending(self, q: str):
        q = (q or "").lower()
        out = []

        for r in self.pending_rows:
            estado = r.get("estado", "").lower()
            if estado != "ok":  # cualquier cosa != ok es pendiente
                pname = self.prod_by_recid.get(r["ID_producto"], {}).get("nombre_producto", "").lower()
                if q in pname:
                    out.append(r)

        return out

    # -------------------------------------------------------
    # RESTAURAR PENDIENTE
    # -------------------------------------------------------
    def restore_pending(self, recid_log: str, depo_dest_recid: str):
        row = next((r for r in self.pending_rows if r["RecID"] == recid_log), None)
        if not row:
            return False

        pid = row["ID_producto"]
        qty = self.safe_int(row.get("cantidad", 0))

        # buscar stock existente
        existente = next(
            (s for s in self.stock_rows
             if s.get("ID_producto") == pid and s.get("ID_deposito") == depo_dest_recid),
            None
        )

        if existente:
            self.add_qty(existente["RecID"], qty)
        else:
            self.add_new_stock(pid, depo_dest_recid, qty)

        # borrar fila pendiente
        self.delete_pending(recid_log, motivo="Restaurado")

        self.refresh_all()
        return True

    # -------------------------------------------------------
    # BORRAR PENDIENTE CON MOTIVO
    # -------------------------------------------------------
    def delete_pending(self, recid_log: str, motivo: str):
        row = next((r for r in self.pending_rows if r["RecID"] == recid_log), None)
        if not row:
            return False

        try:
            self.api_logsAcn.delete_by_recid(recid_log)
        except Exception as e:
            print("[ERROR delete_pending]:", e)
            # fallback: eliminar en memoria
            self.pending_rows = [r for r in self.pending_rows if r["RecID"] != recid_log]

        self.refresh_all()
        self._publish("stock_changed", {"op": "delete_pending", "recid": recid_log, "motivo": motivo})
        return True
    # ============================
# FUNCIONES NECESARIAS SIEMPRE ARRIBA
# ============================

    def _open_qty_bs(page, title, ok_label, on_ok):
        import flet as ft

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


    def _open_move_bs(page, backend, *, origin_recid, origin_name, prod_name, on_move):
        import flet as ft

        # lista depósitos
        options = [
            ft.dropdown.Option(
                key=d["RecID"],
                text=f'{d["id_deposito"]} — {d["nombre_deposito"]}'
            )
            for d in backend.depositos
            if d["RecID"] != origin_recid
        ]

        dd = ft.Dropdown(label="Depósito destino", width=350, options=options)

        qty = ft.TextField(
            label="Cantidad",
            width=150,
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"[0-9]",
                replacement_string=""
            ),
        )

        ok_btn = ft.FilledButton("Mover", icon=ft.Icons.CHEVRON_RIGHT)
        cancel = ft.OutlinedButton("Cancelar")

        inner = ft.Container(
            padding=16,
            bgcolor=ft.Colors.WHITE,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text(f"Mover {prod_name}", size=18, weight=ft.FontWeight.W_700),
                    ft.Text(f"Desde: {origin_name}", size=12, color=ft.Colors.GREY_600),
                    dd, qty,
                    ft.Row(alignment=ft.MainAxisAlignment.END, controls=[cancel, ok_btn]),
                ],
            )
        )

        bs = ft.BottomSheet(content=inner, show_drag_handle=True)
        page.open(bs)

        def close(_=None):
            page.close(bs)
            page.update()

        def confirm(_=None):
            dest = dd.value
            if not dest:
                page.snack_bar = ft.SnackBar(ft.Text("Seleccione un depósito destino."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                n = int(qty.value)
            except:
                n = 0

            if n <= 0:
                page.snack_bar = ft.SnackBar(ft.Text("Cantidad inválida."))
                page.snack_bar.open = True
                page.update()
                return

            on_move(dest, n)
            close()

        ok_btn.on_click = confirm
        cancel.on_click = close
