# Tactica Sheet - Flet Inventory Management

Sistema de gestión de inventario construido con Flet y Google Sheets.

## Requisitos

- Python 3.12.0
- Entorno virtual (venv)

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/RealMSClassic/Tactica-Sheet-.git
cd Tactica-Sheet-
```

2. Crea y activa el entorno virtual:
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:
   - Copia `.env.example` a `.env`
   - Completa las credenciales de Google OAuth:
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`

## Ejecución

```bash
python main.py
```

## Estructura del Proyecto

```
├── back/                   # Backend y lógica de negocio
│   ├── api_auth.py        # Autenticación Google OAuth
│   ├── drive/             # Integraciones con Google Drive
│   ├── image/             # Gestión de imágenes
│   ├── integrations/      # Integraciones externas
│   └── sheet/             # Operaciones con Google Sheets
├── front/                 # Frontend (UI)
│   ├── assets/            # Recursos estáticos
│   └── stock/             # Módulos de inventario
├── .env                   # Variables de entorno (no versionado)
├── .env.example           # Plantilla de variables de entorno
├── requirements.txt       # Dependencias Python
└── main.py               # Punto de entrada

```

## Tecnologías

- **Flet**: Framework UI multiplataforma
- **Google Sheets API**: Almacenamiento de datos
- **Google Drive API**: Gestión de archivos
- **Google OAuth 2.0**: Autenticación

## Licencia

[Especifica tu licencia aquí]
