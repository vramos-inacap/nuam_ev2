import re

from django.core.exceptions import ValidationError

_PATRON_RUT = re.compile(r"^\d{7,8}-[\dK]$")


def calcular_dv(cuerpo: str) -> str:
    """Digito verificador del RUT chileno (modulo 11)."""
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def normalizar_rut(valor: str) -> str:
    """Devuelve el RUT como 12345678-5 o lanza ValidationError."""
    limpio = (valor or "").replace(".", "").replace(" ", "").upper()
    if "-" not in limpio and len(limpio) >= 2:
        limpio = limpio[:-1] + "-" + limpio[-1]
    if not _PATRON_RUT.match(limpio):
        raise ValidationError("RUT con formato inválido. Ejemplo: 12.345.678-5")
    cuerpo, dv = limpio.split("-")
    if calcular_dv(cuerpo) != dv:
        raise ValidationError("El dígito verificador del RUT no es válido.")
    return limpio


def validar_rut(valor):
    normalizar_rut(valor)
