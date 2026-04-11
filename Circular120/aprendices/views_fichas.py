# aprendices/views_fichas.py
import os
import pandas as pd
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.utils.dateparse import parse_date
from django.db import transaction
from django.db.models import Count

from .models import (
    Ficha, Aprendiz, Inasistencia,
    ResultadoAprendizaje, AprendizResultado, Competencia,
)
from .forms import FichaForm, UploadFichaDataForm


class FichaListView(LoginRequiredMixin, ListView):
    model = Ficha
    template_name = "aprendices/ficha_list.html"
    paginate_by = 20
    ordering = ["-fecha_inicio"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = date.today()
        ctx["total_fichas"]     = Ficha.objects.count()
        ctx["total_aprendices"] = Aprendiz.objects.count()
        ctx["fichas_activas"]   = Ficha.objects.filter(fecha_fin__gte=hoy).count()
        ctx["fichas_vencidas"]  = Ficha.objects.filter(fecha_fin__lt=hoy).count()
        ctx["hoy"] = hoy
        return ctx


class FichaCreateView(LoginRequiredMixin, CreateView):
    model = Ficha
    form_class = FichaForm
    template_name = "aprendices/ficha_form.html"
    success_url = reverse_lazy("ficha_list")

    def form_valid(self, form):
        messages.success(self.request, f"Ficha {form.instance.numero} creada exitosamente.")
        return super().form_valid(form)


class FichaUpdateView(LoginRequiredMixin, UpdateView):
    model = Ficha
    form_class = FichaForm
    template_name = "aprendices/ficha_form.html"
    success_url = reverse_lazy("ficha_list")

    def form_valid(self, form):
        messages.success(self.request, f"Ficha {form.instance.numero} actualizada.")
        return super().form_valid(form)


class FichaDetailView(LoginRequiredMixin, DetailView):
    model = Ficha
    template_name = "aprendices/ficha_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ficha = self.object
        aprendices = ficha.aprendices.all()
        ctx["total_aprendices"]      = aprendices.count()
        ctx["aprendices_activos"]    = aprendices.exclude(
            estado_formacion__in=["CANCELADO", "DESERTADO", "CERTIFICADO"]
        ).count()
        ctx["aprendices_certificados"] = aprendices.filter(estado_formacion="CERTIFICADO").count()
        ctx["total_inasistencias"]   = Inasistencia.objects.filter(ficha=ficha).count()
        ctx["aprendices_por_estado"] = aprendices.values("estado_formacion").annotate(
            total=Count("documento")
        )
        ctx["hoy"] = date.today()
        return ctx


class FichaUploadDataView(LoginRequiredMixin, View):
    template_name = "aprendices/ficha_upload_data.html"
    form_class = UploadFichaDataForm

    def get(self, request, numero_ficha):
        ficha = get_object_or_404(Ficha, numero=numero_ficha)
        form = self.form_class(initial={"ficha": ficha})
        return render(request, self.template_name, {"form": form, "ficha": ficha})

    def post(self, request, numero_ficha):
        ficha = get_object_or_404(Ficha, numero=numero_ficha)
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            tipo_datos  = form.cleaned_data["tipo_datos"]
            archivo     = form.cleaned_data["archivo"]
            sobrescribir = form.cleaned_data["sobrescribir"]

            tmp_dir = os.path.join(getattr(settings, "MEDIA_ROOT", "/tmp"), "temp_uploads")
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, archivo.name)
            with open(tmp_path, "wb") as dest:
                for chunk in archivo.chunks():
                    dest.write(chunk)
            try:
                if tipo_datos == "inasistencias":
                    result = self.procesar_inasistencias(tmp_path, ficha, sobrescribir)
                elif tipo_datos == "juicios":
                    result = self.procesar_juicios(tmp_path, ficha, sobrescribir)
                elif tipo_datos == "aprendices":
                    result = self.procesar_aprendices(tmp_path, ficha, sobrescribir)
                else:
                    result = self.procesar_mixto(tmp_path, ficha, sobrescribir)
                messages.success(request, f"Archivo procesado: {result['mensaje']}")
            except Exception as e:
                messages.error(request, f"Error procesando archivo: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            return redirect("ficha_detail", pk=ficha.numero)
        return render(request, self.template_name, {"form": form, "ficha": ficha})

    # ── helpers ──────────────────────────────────────────────────
    def _find_column(self, df, candidates):
        cols = {c.lower(): c for c in df.columns}
        for c in candidates:
            if c.lower() in cols:
                return cols[c.lower()]
        return None

    def procesar_inasistencias(self, path, ficha, sobrescribir):
        df = pd.read_excel(path, dtype=str)
        col_doc  = self._find_column(df, ["documento", "cedula", "identificacion"])
        col_fecha = self._find_column(df, ["fecha", "fecha_inasistencia"])
        col_mot  = self._find_column(df, ["motivo", "observacion"])
        col_just = self._find_column(df, ["justificada", "justificado"])
        created = updated = skipped = 0
        with transaction.atomic():
            for _, row in df.iterrows():
                doc = str(row.get(col_doc, "")).strip()
                if not doc:
                    skipped += 1; continue
                aprendiz, _ = Aprendiz.objects.get_or_create(
                    documento=doc,
                    defaults={"nombre": "Desconocido", "apellido": "", "ficha": ficha},
                )
                if not aprendiz.ficha:
                    aprendiz.ficha = ficha; aprendiz.save()
                fecha_raw = row.get(col_fecha)
                fecha = None
                try:
                    if pd.notna(fecha_raw):
                        fecha = fecha_raw.date() if isinstance(fecha_raw, pd.Timestamp) else parse_date(str(fecha_raw))
                except Exception:
                    pass
                if not fecha:
                    skipped += 1; continue
                justificada = False
                if col_just:
                    justificada = str(row.get(col_just, "")).lower() in ["si", "sí", "yes", "true", "1"]
                motivo = str(row.get(col_mot, ""))[:1000] if col_mot else ""
                if sobrescribir:
                    _, c = Inasistencia.objects.update_or_create(
                        aprendiz=aprendiz, ficha=ficha, fecha=fecha,
                        defaults={"justificada": justificada, "motivo": motivo},
                    )
                    if c: created += 1
                    else: updated += 1
                else:
                    Inasistencia.objects.create(
                        aprendiz=aprendiz, ficha=ficha, fecha=fecha,
                        justificada=justificada, motivo=motivo,
                    )
                    created += 1
        return {"mensaje": f"{created} creadas, {updated} actualizadas, {skipped} omitidas"}

    def procesar_juicios(self, path, ficha, sobrescribir):
        df = pd.read_excel(path, dtype=str)
        col_doc   = self._find_column(df, ["documento", "cedula"])
        col_nombre= self._find_column(df, ["nombre"])
        col_comp  = self._find_column(df, ["competencia"])
        col_ra    = self._find_column(df, ["resultado", "ra"])
        col_estado= self._find_column(df, ["estado", "juicio"])
        created = updated = skipped = 0
        with transaction.atomic():
            for _, row in df.iterrows():
                doc = str(row.get(col_doc, "")).strip()
                if not doc:
                    skipped += 1; continue
                nombre = str(row.get(col_nombre, "Desconocido")).strip() if col_nombre else "Desconocido"
                aprendiz, _ = Aprendiz.objects.get_or_create(
                    documento=doc, defaults={"nombre": nombre, "apellido": "", "ficha": ficha}
                )
                if not aprendiz.ficha:
                    aprendiz.ficha = ficha; aprendiz.save()
                ra_code = str(row.get(col_ra, "")).strip() if col_ra else ""
                comp_code = str(row.get(col_comp, "")).strip() if col_comp else ""
                est = str(row.get(col_estado, "")).lower() if col_estado else ""
                if "aprob" in est or "satisf" in est:
                    estado_norm = "APROBADO"
                elif "no" in est:
                    estado_norm = "NO_APROBADO"
                else:
                    estado_norm = "PENDIENTE"
                if ra_code:
                    comp = None
                    if comp_code:
                        comp, _ = Competencia.objects.get_or_create(
                            codigo=comp_code, defaults={"nombre": comp_code}
                        )
                    ra_obj, _ = ResultadoAprendizaje.objects.get_or_create(
                        codigo=ra_code, defaults={"nombre": ra_code, "competencia": comp}
                    )
                    _, c = AprendizResultado.objects.update_or_create(
                        aprendiz=aprendiz, resultado=ra_obj,
                        defaults={"estado": estado_norm},
                    )
                    if c: created += 1
                    else: updated += 1
                else:
                    skipped += 1
        return {"mensaje": f"{created} creados, {updated} actualizados, {skipped} omitidos"}

    def procesar_aprendices(self, path, ficha, sobrescribir):
        df = pd.read_excel(path, dtype=str)
        col_doc  = self._find_column(df, ["documento", "cedula"])
        col_nom  = self._find_column(df, ["nombre"])
        col_ape  = self._find_column(df, ["apellido"])
        col_mail = self._find_column(df, ["email", "correo"])
        col_tel  = self._find_column(df, ["telefono", "tel"])
        col_est  = self._find_column(df, ["estado"])
        ESTADOS = {
            "en formacion": "EN_FORMACION", "formacion": "EN_FORMACION",
            "productiva": "ETAPA_PRODUCTIVA", "etapa productiva": "ETAPA_PRODUCTIVA",
            "por certificar": "POR_CERTIFICAR", "certificado": "CERTIFICADO",
        }
        created = updated = skipped = 0
        with transaction.atomic():
            for _, row in df.iterrows():
                doc = str(row.get(col_doc, "")).strip()
                if not doc:
                    skipped += 1; continue
                nombre   = str(row.get(col_nom, "Desconocido")).strip()
                apellido = str(row.get(col_ape, "")).strip() if col_ape else ""
                email    = str(row.get(col_mail, "")).strip() if col_mail else None
                telefono = str(row.get(col_tel, "")).strip() if col_tel else None
                estado   = str(row.get(col_est, "EN_FORMACION")).strip().lower() if col_est else "en formacion"
                estado_norm = ESTADOS.get(estado, "EN_FORMACION")
                _, c = Aprendiz.objects.update_or_create(
                    documento=doc,
                    defaults={"nombre": nombre, "apellido": apellido,
                                "email": email, "telefono": telefono,
                                "estado_formacion": estado_norm, "ficha": ficha},
                )
                if c: created += 1
                else: updated += 1
        return {"mensaje": f"{created} creados, {updated} actualizados, {skipped} omitidos"}

    def procesar_mixto(self, path, ficha, sobrescribir):
        df = pd.read_excel(path, dtype=str)
        cols = [c.lower() for c in df.columns]
        msgs = []
        if any(x in cols for x in ["fecha", "inasistencia"]):
            r = self.procesar_inasistencias(path, ficha, sobrescribir)
            msgs.append(r["mensaje"])
        if any(x in cols for x in ["resultado", "juicio", "competencia"]):
            r = self.procesar_juicios(path, ficha, sobrescribir)
            msgs.append(r["mensaje"])
        return {"mensaje": " | ".join(msgs) or "Sin datos reconocibles"}