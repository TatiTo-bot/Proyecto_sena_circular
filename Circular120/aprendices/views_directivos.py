from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import CentroFormacion, Rol, PersonalDirectivo
from .forms import CentroFormacionForm, RolForm, PersonalDirectivoForm

# CENTROS DE FORMACIÓN

class CentroListView(LoginRequiredMixin, ListView):
    model = CentroFormacion
    template_name = "aprendices/centro_list.html"
    context_object_name = "centros"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total"] = CentroFormacion.objects.count()
        ctx["activos"] = CentroFormacion.objects.filter(activo=True).count()
        return ctx


class CentroCreateView(LoginRequiredMixin, CreateView):
    model = CentroFormacion
    form_class = CentroFormacionForm
    template_name = "aprendices/centro_form.html"
    success_url = reverse_lazy("centro_list")

    def form_valid(self, form):
        messages.success(self.request, "Centro de formación registrado correctamente.")
        return super().form_valid(form)


class CentroUpdateView(LoginRequiredMixin, UpdateView):
    model = CentroFormacion
    form_class = CentroFormacionForm
    template_name = "aprendices/centro_form.html"
    success_url = reverse_lazy("centro_list")

    def form_valid(self, form):
        messages.success(self.request, "Centro de formación actualizado.")
        return super().form_valid(form)

# ROLES

class RolListView(LoginRequiredMixin, ListView):
    model = Rol
    template_name = "aprendices/rol_list.html"
    context_object_name = "roles"


class RolCreateView(LoginRequiredMixin, CreateView):
    model = Rol
    form_class = RolForm
    template_name = "aprendices/rol_form.html"
    success_url = reverse_lazy("rol_list")

    def form_valid(self, form):
        messages.success(self.request, f"Rol '{form.instance.nombre}' creado.")
        return super().form_valid(form)


class RolUpdateView(LoginRequiredMixin, UpdateView):
    model = Rol
    form_class = RolForm
    template_name = "aprendices/rol_form.html"
    success_url = reverse_lazy("rol_list")

    def form_valid(self, form):
        messages.success(self.request, f"Rol '{form.instance.nombre}' actualizado.")
        return super().form_valid(form)

# PERSONAL DIRECTIVO

class PersonalListView(LoginRequiredMixin, ListView):
    model = PersonalDirectivo
    template_name = "aprendices/personal_list.html"
    context_object_name = "personal"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total"] = PersonalDirectivo.objects.count()
        ctx["activos"] = PersonalDirectivo.objects.filter(activo=True).count()
        ctx["inactivos"] = PersonalDirectivo.objects.filter(activo=False).count()
        return ctx


class PersonalCreateView(LoginRequiredMixin, CreateView):
    model = PersonalDirectivo
    form_class = PersonalDirectivoForm
    template_name = "aprendices/personal_form.html"
    success_url = reverse_lazy("personal_list")

    def form_valid(self, form):
        messages.success(
            self.request,
            f"{form.instance.nombre_completo()} registrado correctamente.",
        )
        return super().form_valid(form)


class PersonalUpdateView(LoginRequiredMixin, UpdateView):
    model = PersonalDirectivo
    form_class = PersonalDirectivoForm
    template_name = "aprendices/personal_form.html"
    success_url = reverse_lazy("personal_list")

    def form_valid(self, form):
        messages.success(self.request, "Personal directivo actualizado.")
        return super().form_valid(form)


@login_required
def personal_toggle_activo(request, pk):
    """Activa / desactiva sin eliminar."""
    persona = get_object_or_404(PersonalDirectivo, pk=pk)
    persona.activo = not persona.activo
    persona.save()
    estado = "activado" if persona.activo else "desactivado"
    messages.info(request, f"{persona.nombre_completo()} ha sido {estado}.")
    return redirect("personal_list")