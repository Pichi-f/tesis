import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cifra_negra.db"


def crear_base_datos():

    DATA_DIR.mkdir(exist_ok=True)

    conexion = sqlite3.connect(DB_PATH)

    # Activar llaves foráneas en SQLite
    conexion.execute("PRAGMA foreign_keys = ON")

    cursor = conexion.cursor()

    # =====================================================
    # TABLA: reporte_crudo
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reporte_crudo (

            id_reporte INTEGER PRIMARY KEY AUTOINCREMENT,

            id_publicacion_plataforma TEXT
                NOT NULL,

            plataforma TEXT
                NOT NULL
                CHECK(plataforma IN ('X', 'Facebook')),

            usuario_publico TEXT,

            texto_crudo TEXT
                NOT NULL,

            url_publicacion TEXT,

            referencia_espacial TEXT,

            fecha_publicacion DATETIME
                NOT NULL,

            fecha_extraccion DATETIME
                NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            estado_procesamiento TEXT
                NOT NULL
                DEFAULT 'pendiente'
                CHECK(
                    estado_procesamiento IN (
                        'pendiente',
                        'procesado',
                        'ruido',
                        'error'
                    )
                ),

            UNIQUE(plataforma, id_publicacion_plataforma)
        )
    """)

    # =====================================================
    # TABLA: indicio_procesado
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS indicio_procesado (

            id_indicio INTEGER PRIMARY KEY AUTOINCREMENT,

            id_reporte INTEGER
                NOT NULL
                UNIQUE,

            texto_procesado TEXT
                NOT NULL,

            categoria_delito TEXT
                NOT NULL
                CHECK(
                    categoria_delito IN (
                        'robo',
                        'extorsion',
                        'agresion',
                        'otro'
                    )
                ),

            score_clasificacion REAL
                NOT NULL
                CHECK(
                    score_clasificacion >= 0.0
                    AND
                    score_clasificacion <= 1.0
                ),

            latitud REAL
                NOT NULL,

            longitud REAL
                NOT NULL,

            fecha_publicacion DATETIME
                NOT NULL,

            FOREIGN KEY (id_reporte)
                REFERENCES reporte_crudo(id_reporte)
        )
    """)

    conexion.commit()
    conexion.close()

    print("Base de datos creada correctamente.")
    print(f"Ubicación: {DB_PATH}")


if __name__ == "__main__":
    crear_base_datos()