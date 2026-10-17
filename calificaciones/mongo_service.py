"""Acceso a MongoDB para los certificados asociados a cada calificacion.

PostgreSQL y MongoDB no comparten transaccion: cada funcion captura los errores
de MongoDB y informa el resultado para que la vista decida (y audite) que hacer.
"""
import logging
from datetime import datetime, timezone
from functools import lru_cache

from django.conf import settings
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _cliente():
    return MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)


def _coleccion():
    coleccion = _cliente()[settings.MONGO_DB][settings.MONGO_COLLECTION]
    coleccion.create_index([("calificacion_id", ASCENDING)], unique=True)
    return coleccion


def guardar_certificado(calificacion, empresa="", tipo_certificado="Calificación",
                        observaciones="", evaluador=""):
    """Crea o reemplaza el documento de la calificacion. Devuelve True si se guardo."""
    documento = {
        "calificacion_id": int(calificacion.pk),
        "rut": calificacion.rut_emisor,
        "empresa": empresa,
        "tipo_certificado": tipo_certificado,
        "detalle_no_estructurado": {
            "observaciones": observaciones,
            "evaluador": evaluador,
        },
        "fecha_registro": datetime.now(timezone.utc),
    }
    try:
        _coleccion().replace_one(
            {"calificacion_id": int(calificacion.pk)}, documento, upsert=True
        )
        return True
    except PyMongoError:
        logger.exception("No se pudo guardar el certificado en MongoDB")
        return False


def obtener_certificado(calificacion_id):
    """Devuelve (documento o None, hubo_error)."""
    try:
        documento = _coleccion().find_one(
            {"calificacion_id": int(calificacion_id)}, {"_id": 0}
        )
        return documento, False
    except PyMongoError:
        logger.exception("No se pudo consultar MongoDB")
        return None, True


def actualizar_rut(calificacion_id, rut):
    try:
        _coleccion().update_one(
            {"calificacion_id": int(calificacion_id)}, {"$set": {"rut": rut}}
        )
        return True
    except PyMongoError:
        logger.exception("No se pudo actualizar el RUT en MongoDB")
        return False


def eliminar_certificado(calificacion_id):
    try:
        _coleccion().delete_one({"calificacion_id": int(calificacion_id)})
        return True
    except PyMongoError:
        logger.exception("No se pudo eliminar el certificado en MongoDB")
        return False
