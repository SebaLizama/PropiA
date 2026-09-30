import sqlite3
import json
from pathlib import Path

# Base de datos local de PropiA
DATABASE_PATH = Path(__file__).parent / "propiA.db"


def get_connection():
    """
    Crea una conexión con la base de datos.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    """
    Crea las tablas necesarias si no existen.
    """
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS property_profiles (
            user_id TEXT PRIMARY KEY,
            profile TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def get_property_profile(user_id):
    """
    Obtiene el perfil inmobiliario de un usuario.

    Retorna un diccionario o None si no existe.
    """
    connection = get_connection()

    row = connection.execute(
        """
        SELECT profile
        FROM property_profiles
        WHERE user_id = ?
        """,
        (str(user_id),)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return json.loads(row["profile"])


def save_property_profile(user_id, profile):
    """
    Guarda o actualiza el perfil inmobiliario de un usuario.
    """
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO property_profiles (user_id, profile)
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            profile = excluded.profile,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            str(user_id),
            json.dumps(profile, ensure_ascii=False)
        )
    )

    connection.commit()
    connection.close()


def delete_property_profile(user_id):
    """
    Elimina el perfil inmobiliario de un usuario.
    """
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM property_profiles
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    connection.commit()
    connection.close()
