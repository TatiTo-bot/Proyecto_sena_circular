# aprendices/views_fichas.py
import os
import pandas as pd
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils.dateparse import parse_date
from django.db import transaction
from .models import Ficha, Aprendiz, Inasistencia, ResultadoAprendizaje, AprendizResultado, Competencia
from .forms import FichaForm, UploadFichaDataForm


# ============================================
# GESTIÓN DE FICHAS
# ============================================

class FichaListView(LoginRequiredMixin, ListView):
    model = Ficha
    template_name = 'aprendices/ficha_list.html'
    paginate_by = 20
    ordering = ['-fecha_inicio']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = date.today()
        
        context['total_fichas'] = Ficha.objects.count()
        context['total_aprendices'] = Aprendiz.objects.count()
        context['fichas_activas'] = Ficha.objects.filter(fecha_fin__gte=hoy).count()
        context['fichas_vencidas'] = Ficha.objects.filter(fecha_fin__lt=hoy).count()
        context['hoy'] = hoy
        
        return context


class FichaCreateView(LoginRequiredMixin, CreateView):
    model = Ficha
    form_class = FichaForm
    template_name = 'aprendices/ficha_form.html'
    success_url = reverse_lazy('ficha_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Ficha {form.instance.numero} creada exitosamente')
        return super().form_valid(form)


class FichaUpdateView(LoginRequiredMixin, UpdateView):
    model = Ficha
    form_class = FichaForm
    template_name = 'aprendices/ficha_form.html'
    success_url = reverse_lazy('ficha_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Ficha {form.instance.numero} actualizada exitosamente')
        return super().form_valid(form)


class FichaDetailView(LoginRequiredMixin, DetailView):
    model = Ficha
    template_name = 'aprendices/ficha_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ficha = self.object
        
        # Estadísticas de la ficha
        aprendices = ficha.aprendices.all()
        context['total_aprendices'] = aprendices.count()
        context['aprendices_activos'] = aprendices.exclude(
            estado_formacion__in=['CANCELADO', 'DESERTADO', 'CERTIFICADO']
        ).count()
        context['aprendices_certificados'] = aprendices.filter(estado_formacion='CERTIFICADO').count()
        context['total_inasistencias'] = Inasistencia.objects.filter(ficha=ficha).count()
        
        # Aprendices por estado
        context['aprendices_por_estado'] = aprendices.values('estado_formacion').annotate(
            total=Count('documento')
        )
        
        return context


# ============================================
# IMPORTACIÓN DE DATOS POR FICHA
# ============================================

class FichaUploadDataView(LoginRequiredMixin, View):
    template_name = 'aprendices/ficha_upload_data.html'
    form_class = UploadFichaDataForm
    
    def get(self, request, numero_ficha):
        ficha = get_object_or_404(Ficha, numero=numero_ficha)
        form = self.form_class(initial={'ficha': ficha})
        
        return render(request, self.template_name, {
            'form': form,
            'ficha': ficha
        })
    
    def post(self, request, numero_ficha):
        ficha = get_object_or_404(Ficha, numero=numero_ficha)
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            tipo_datos = form.cleaned_data['tipo_datos']
            archivo = form.cleaned_data['archivo']
            sobrescribir = form.cleaned_data['sobrescribir']
            
            # Guardar archivo temporalmente
            tmp_dir = getattr(settings, 'MEDIA_ROOT', None) or '/tmp'
            tmp_subdir = os.path.join(tmp_dir, 'temp_uploads')
            os.makedirs(tmp_subdir, exist_ok=True)
            tmp_path = os.path.join(tmp_subdir, archivo.name)
            
            with open(tmp_path, 'wb') as dest:
                for chunk in archivo.chunks():
                    dest.write(chunk)
            
            try:
                # Procesar según el tipo de datos
                if tipo_datos == 'inasistencias':
                    result = self.procesar_inasistencias(tmp_path, ficha, sobrescribir)
                elif tipo_datos == 'juicios':
                    result = self.procesar_juicios(tmp_path, ficha, sobrescribir)
                elif tipo_datos == 'aprendices':
                    result = self.procesar_aprendices(tmp_path, ficha, sobrescribir)
                elif tipo_datos == 'mixto':
                    result = self.procesar_mixto(tmp_path, ficha, sobrescribir)
                
                messages.success(request, f'Archivo procesado: {result["mensaje"]}')
                
            except Exception as e:
                messages.error(request, f'Error procesando archivo: {str(e)}')
            finally:
                # Eliminar archivo temporal
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            
            return redirect('ficha_detail', pk=ficha.numero)
        
        return render(request, self.template_name, {
            'form': form,
            'ficha': ficha
        })
    
    def procesar_inasistencias(self, archivo_path, ficha, sobrescribir):
        """Procesa archivo de inasistencias"""
        df = pd.read_excel(archivo_path, dtype=str)
        
        # Mapeo flexible de columnas
        col_doc = self._find_column(df, ['documento', 'cedula', 'identificacion', 'doc'])
        col_fecha = self._find_column(df, ['fecha', 'fecha_inasistencia', 'fecha inasistencia'])
        col_motivo = self._find_column(df, ['motivo', 'observacion', 'razon'])
        col_justificada = self._find_column(df, ['justificada', 'justificado'])
        
        created = 0
        updated = 0
        skipped = 0
        
        with transaction.atomic():
            for idx, row in df.iterrows():
                doc = str(row.get(col_doc, '')).strip()
                if not doc:
                    skipped += 1
                    continue
                
                # Obtener o crear aprendiz
                aprendiz, _ = Aprendiz.objects.get_or_create(
                    documento=doc,
                    defaults={'nombre': 'Desconocido', 'apellido': '', 'ficha': ficha}
                )
                
                # Si el aprendiz no tiene ficha, asignarle esta
                if not aprendiz.ficha:
                    aprendiz.ficha = ficha
                    aprendiz.save()
                
                # Procesar fecha
                fecha_raw = row.get(col_fecha)
                fecha = None
                try:
                    if pd.notna(fecha_raw):
                        if isinstance(fecha_raw, pd.Timestamp):
                            fecha = fecha_raw.date()
                        else:
                            fecha = parse_date(str(fecha_raw))
                except:
                    pass
                
                if not fecha:
                    skipped += 1
                    continue
                
                # Procesar justificada
                justificada = False
                if col_justificada:
                    val = str(row.get(col_justificada, '')).lower()
                    justificada = val in ['si', 'sí', 'yes', 'true', '1', 'justificada']
                
                motivo = str(row.get(col_motivo, ''))[:1000] if col_motivo else ''
                
                # Crear o actualizar inasistencia
                if sobrescribir:
                    obj, created_obj = Inasistencia.objects.update_or_create(
                        aprendiz=aprendiz,
                        ficha=ficha,
                        fecha=fecha,
                        defaults={
                            'justificada': justificada,
                            'motivo': motivo,
                            'reportado_por': self.request.user.username
                        }
                    )
                    if created_obj:
                        created += 1
                    else:
                        updated += 1
                else:
                    Inasistencia.objects.create(
                        aprendiz=aprendiz,
                        ficha=ficha,
                        fecha=fecha,
                        justificada=justificada,
                        motivo=motivo,
                        reportado_por=self.request.user.username
                    )
                    created += 1
        
        return {
            'mensaje': f'{created} inasistencias creadas, {updated} actualizadas, {skipped} omitidas',
            'created': created,
            'updated': updated,
            'skipped': skipped
        }
    
    def procesar_juicios(self, archivo_path, ficha, sobrescribir):
        """Procesa archivo de juicios evaluativos"""
        df = pd.read_excel(archivo_path, dtype=str)
        
        col_doc = self._find_column(df, ['documento', 'cedula', 'identificacion'])
        col_nombre = self._find_column(df, ['nombre', 'nombres'])
        col_comp = self._find_column(df, ['competencia', 'codigo_competencia', 'cod_comp'])
        col_ra = self._find_column(df, ['resultado', 'ra', 'resultado_aprendizaje'])
        col_estado = self._find_column(df, ['estado', 'juicio', 'resultado', 'calificacion'])
        
        created = 0
        updated = 0
        skipped = 0
        
        with transaction.atomic():
            for idx, row in df.iterrows():
                doc = str(row.get(col_doc, '')).strip()
                if not doc:
                    skipped += 1
                    continue
                
                nombre = str(row.get(col_nombre, 'Desconocido')).strip() if col_nombre else 'Desconocido'
                
                # Obtener o crear aprendiz
                aprendiz, _ = Aprendiz.objects.get_or_create(
                    documento=doc,
                    defaults={'nombre': nombre, 'apellido': '', 'ficha': ficha}
                )
                
                if not aprendiz.ficha:
                    aprendiz.ficha = ficha
                    aprendiz.save()
                
                # Procesar competencia y resultado
                comp_code = str(row.get(col_comp, '')).strip() if col_comp else ''
                ra_code = str(row.get(col_ra, '')).strip() if col_ra else ''
                estado_raw = str(row.get(col_estado, '')).strip().lower() if col_estado else ''
                
                # Normalizar estado
                if 'aprob' in estado_raw or 'satisfactorio' in estado_raw or 'apto' in estado_raw:
                    estado_norm = 'APROBADO'
                elif 'no' in estado_raw or 'rechaz' in estado_raw or 'no apto' in estado_raw:
                    estado_norm = 'NO_APROBADO'
                else:
                    estado_norm = 'PENDIENTE'
                
                if ra_code:
                    # Crear competencia si existe
                    competencia = None
                    if comp_code:
                        competencia, _ = Competencia.objects.get_or_create(
                            codigo=comp_code,
                            defaults={'nombre': comp_code}
                        )
                    
                    # Crear resultado de aprendizaje
                    ra_obj, _ = ResultadoAprendizaje.objects.get_or_create(
                        codigo=ra_code,
                        defaults={'nombre': ra_code, 'competencia': competencia}
                    )
                    
                    # Crear o actualizar AprendizResultado
                    obj, created_obj = AprendizResultado.objects.update_or_create(
                        aprendiz=aprendiz,
                        resultado=ra_obj,
                        defaults={'estado': estado_norm}
                    )
                    
                    if created_obj:
                        created += 1
                    else:
                        updated += 1
                else:
                    skipped += 1
        
        return {
            'mensaje': f'{created} resultados creados, {updated} actualizados, {skipped} omitidos',
            'created': created,
            'updated': updated,
            'skipped': skipped
        }
    
    def procesar_aprendices(self, archivo_path, ficha, sobrescribir):
        """Procesa archivo con lista de aprendices"""
        df = pd.read_excel(archivo_path, dtype=str)
        
        col_doc = self._find_column(df, ['documento', 'cedula', 'identificacion'])
        col_nombre = self._find_column(df, ['nombre', 'nombres'])
        col_apellido = self._find_column(df, ['apellido', 'apellidos'])
        col_email = self._find_column(df, ['email', 'correo', 'mail'])
        col_telefono = self._find_column(df, ['telefono', 'tel', 'celular'])
        col_estado = self._find_column(df, ['estado', 'estado_formacion'])
        
        created = 0
        updated = 0
        skipped = 0
        
        with transaction.atomic():
            for idx, row in df.iterrows():
                doc = str(row.get(col_doc, '')).strip()
                if not doc:
                    skipped += 1
                    continue
                
                nombre = str(row.get(col_nombre, 'Desconocido')).strip()
                apellido = str(row.get(col_apellido, '')).strip() if col_apellido else ''
                email = str(row.get(col_email, '')).strip() if col_email else None
                telefono = str(row.get(col_telefono, '')).strip() if col_telefono else None
                estado = str(row.get(col_estado, 'EN_FORMACION')).strip() if col_estado else 'EN_FORMACION'
                
                # Normalizar estado
                estado_map = {
                    'en formacion': 'EN_FORMACION',
                    'formacion': 'EN_FORMACION',
                    'productiva': 'ETAPA_PRODUCTIVA',
                    'etapa productiva': 'ETAPA_PRODUCTIVA',
                    'por certificar': 'POR_CERTIFICAR',
                    'certificado': 'CERTIFICADO',
                }
                estado_norm = estado_map.get(estado.lower(), estado)
                
                # Crear o actualizar aprendiz
                obj, created_obj = Aprendiz.objects.update_or_create(
                    documento=doc,
                    defaults={
                        'nombre': nombre,
                        'apellido': apellido,
                        'email': email,
                        'telefono': telefono,
                        'estado_formacion': estado_norm,
                        'ficha': ficha
                    }
                )
                
                if created_obj:
                    created += 1
                else:
                    updated += 1
        
        return {
            'mensaje': f'{created} aprendices creados, {updated} actualizados, {skipped} omitidos',
            'created': created,
            'updated': updated,
            'skipped': skipped
        }
    
    def procesar_mixto(self, archivo_path, ficha, sobrescribir):
        """Procesa archivo con datos mixtos"""
        # Detectar automáticamente qué tipo de datos contiene
        df = pd.read_excel(archivo_path, dtype=str)
        cols_lower = [c.lower() for c in df.columns]
        
        resultados = {}
        
        # Verificar si tiene inasistencias
        if any(x in cols_lower for x in ['fecha', 'inasistencia', 'fecha_inasistencia']):
            result_inas = self.procesar_inasistencias(archivo_path, ficha, sobrescribir)
            resultados['inasistencias'] = result_inas
        
        # Verificar si tiene juicios
        if any(x in cols_lower for x in ['resultado', 'juicio', 'competencia', 'ra']):
            result_juicios = self.procesar_juicios(archivo_path, ficha, sobrescribir)
            resultados['juicios'] = result_juicios
        
        mensaje_final = "Procesamiento mixto: "
        if 'inasistencias' in resultados:
            mensaje_final += resultados['inasistencias']['mensaje'] + ". "
        if 'juicios' in resultados:
            mensaje_final += resultados['juicios']['mensaje']
        
        return {'mensaje': mensaje_final, 'resultados': resultados}
    
    def _find_column(self, df, candidates):
        """Encuentra una columna de forma flexible"""
        cols_lower = {c.lower(): c for c in df.columns}
        for candidate in candidates:
            if candidate.lower() in cols_lower:
                return cols_lower[candidate.lower()]
        return None