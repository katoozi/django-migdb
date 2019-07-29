import json
import os

from django.apps import apps
from django.forms import formset_factory
from django.shortcuts import redirect, render
from django.views.generic import FormView, TemplateView

from .forms import ACTIONS, FieldForm
from .dump import DumpGenerator


class AppsList(TemplateView):
    template_name = 'migdb/apps.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["apps"] = apps.get_app_configs()
        return context

class ModelsList(FormView):
    template_name = 'migdb/models.html'

    def get(self, request, *args, **kwargs):
        app_name = request.GET.get("app_name", None)
        return render(request, self.template_name, {
            "app_name": app_name,
            'models': apps.all_models[app_name].items(),
        })

    def post(self, request, *args, **kwargs):
        app_name = request.GET.get("app_name", None)
        dump_thread = DumpGenerator(app_name)
        dump_thread.start()
        return render(request, self.template_name, {
            "app_name": app_name,
            'models': apps.all_models[app_name].items(),
            "start_dumping": "Dumping is started."
        })


class FieldsList(FormView):
    template_name = 'migdb/fields.html'
    form = formset_factory(FieldForm)

    def get(self, request, *args, **kwargs):
        app_name = request.GET.get("app_name", None)
        model_name = request.GET.get("model_name", None)
        new_app_name = request.GET.get("new_app_name", app_name)

        model = apps.get_model(app_label=app_name, model_name=model_name)

        context = {}
        context['app_name'] = app_name
        context['model_name'] = model_name
        context['new_app_name'] = new_app_name
        context["fields"] = model._meta.get_fields()
        context['actions'] = ACTIONS

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        formset = self.form(request.POST)
        if not formset.is_valid():
            print(formset.errors)
            return
        app_name = request.GET.get("app_name", None)
        model_name = request.GET.get("model_name", None)
        new_app_name = request.GET.get("new_app_name", app_name)

        new_model_name = request.POST.get("new_model_name", model_name)

        data = {}
        data['app_name'] = app_name
        data['new_app_name'] = new_app_name
        model_structure = {
            'current_name': model_name,
            'new_name': new_model_name,
            'fields': []
        }
        for form in formset:
            field_data = {k: v for k, v in form.cleaned_data.items() if v}
            model_structure['fields'].append(field_data)
        data['models'] = []
        data['models'].append(model_structure)

        file_name = "%s_structure.json" % app_name

        if os.path.isfile(file_name):
            with open(file_name, 'r') as the_file:
                content = the_file.read()
                try:
                    content = json.loads(content)
                    data = content
                    if 'models' not in data:
                        data['models'] = []
                    for index in range(len(data['models'])):
                        if data['models'][index]['current_name'] == model_name:
                            del data['models'][index]
                    data['models'].append(model_structure)
                    data['app_name'] = app_name
                    data['new_app_name'] = new_app_name
                except ValueError:
                    pass
        with open(file_name, 'w') as the_file:
            the_file.write(json.dumps(data))

        return redirect("migdb:apps_list")
