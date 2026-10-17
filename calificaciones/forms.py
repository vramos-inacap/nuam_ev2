from django import forms
from django.conf import settings

from .models import CalificacionTributaria
from .validators import normalizar_rut


class EstiloBootstrapMixin:
    def _aplicar_estilo(self):
        for campo in self.fields.values():
            clase = "form-select" if isinstance(campo.widget, forms.Select) else "form-control"
            campo.widget.attrs.setdefault("class", clase)


class CalificacionForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = CalificacionTributaria
        fields = ["periodo_anual", "rut_emisor", "monto_tributario", "estado"]
        labels = {
            "periodo_anual": "Período anual",
            "rut_emisor": "RUT del emisor",
            "monto_tributario": "Monto tributario",
            "estado": "Estado",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()

    def clean_rut_emisor(self):
        return normalizar_rut(self.cleaned_data["rut_emisor"])


class CalificacionCrearForm(CalificacionForm):
    empresa = forms.CharField(label="Empresa emisora", max_length=120, required=False)
    tipo_certificado = forms.CharField(
        label="Tipo de certificado", max_length=60, required=False, initial="Calificación"
    )
    observaciones = forms.CharField(
        label="Observaciones del certificado",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class FiltroForm(EstiloBootstrapMixin, forms.Form):
    periodo = forms.IntegerField(label="Período", required=False, min_value=2000, max_value=2100)
    rut = forms.CharField(label="RUT", required=False, max_length=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()

    def clean_rut(self):
        valor = self.cleaned_data.get("rut")
        return normalizar_rut(valor) if valor else ""


class CargaMasivaForm(EstiloBootstrapMixin, forms.Form):
    archivo = forms.FileField(label="Archivo CSV")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".csv"):
            raise forms.ValidationError("Solo se aceptan archivos .csv")
        if archivo.size > settings.CARGA_MASIVA_MAX_BYTES:
            raise forms.ValidationError("El archivo supera el tamaño máximo permitido (1 MB).")
        return archivo
