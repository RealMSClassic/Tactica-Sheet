from __future__ import annotations
from typing import List, Dict
from uuid import uuid4
from .base import SheetsBase


class LogsAcnAPI(SheetsBase):
    """
    Hoja: 'logsAcn'
    Columnas:
    data_ini_prox | RecID | ID_producto | ID_deposito | cantidad | movimiento | tipo_accion
    """

    TAB = "logsAcn"
    HEADERS = [
        "data_ini_prox", "RecID", "ID_producto", "ID_deposito",
        "cantidad", "movimiento", "tipo_accion"
    ]

    def list(self) -> List[Dict]:
        self._ensure_tab_and_headers(self.TAB, self.HEADERS)
        rng = f"{self.TAB}!A2:{self._col_letter(len(self.HEADERS))}"
        rows = self._get(rng)

        out = []
        for r in rows:
            r = (r + [""] * len(self.HEADERS))[:len(self.HEADERS)]
            rec = dict(zip(self.HEADERS, r))

            if rec.get("RecID"):
                out.append({
                    "RecID": rec["RecID"],
                    "ID_producto": rec["ID_producto"],
                    "ID_deposito": rec["ID_deposito"],
                    "cantidad": int(rec["cantidad"] or 0),
                    "movimiento": rec["movimiento"],
                    "tipo_accion": rec["tipo_accion"],
                })
        return out

    def delete_by_recid(self, recid: str) -> bool:
        self._ensure_tab_and_headers(self.TAB, self.HEADERS)
        row = self._find_row_by_col_value(self.TAB, 2, recid)  # columna B=RecID
        if not row:
            return False
        rng = f"{self.TAB}!A{row}:{self._col_letter(len(self.HEADERS))}{row}"
        self._clear(rng)
        return True
    def add(
        self,
        *,
        ID_producto: str,
        ID_deposito: str,
        cantidad: int,
        movimiento: str,
        tipo_accion: str
    ) -> str:
        """
        Inserta una fila nueva en logsAcn.
        """
        self._ensure_tab_and_headers(self.TAB, self.HEADERS)

        recid = uuid4().hex[:10]  
        cantidad = int(cantidad or 0)

        row = [
            "",              # data_ini_prox
            recid,
            ID_producto,
            ID_deposito,
            cantidad,
            movimiento,
            tipo_accion,
        ]

        self._append(f"{self.TAB}!A2", [row])
        return recid