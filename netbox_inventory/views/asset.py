import logging

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect
from django.template import Template

from netbox.views import generic
from utilities.forms import ConfirmationForm, restrict_form_fields
from utilities.views import register_model_view

from .. import filtersets, forms, models, tables
from ..template_content import WARRANTY_PROGRESSBAR
from ..utils import (
    get_tags_and_edit_protected_asset_fields,
    get_tags_that_protect_asset_from_deletion,
)

__all__ = (
    'AssetView',
    'AssetListView',
    'AssetBulkCreateView',
    'AssetEditView',
    'AssetDeleteView',
    'AssetBulkImportView',
    'AssetBulkEditView',
    'AssetBulkDeleteView',
)


@register_model_view(models.Asset)
class AssetView(generic.ObjectView):
    queryset = models.Asset.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context['warranty_progressbar'] = Template(WARRANTY_PROGRESSBAR)
        return context


@register_model_view(models.Asset, 'list', path='', detail=False)
class AssetListView(generic.ObjectListView):
    queryset = models.Asset.objects.prefetch_related(
        'device_type__manufacturer',
        'module_type__manufacturer',
        'inventoryitem_type__manufacturer',
        'rack_type__manufacturer',
        'device__role',
        'module__module_bay',
        'module__module_type',
        'inventoryitem__role',
        'rack__role',
        'owner',
        'purchase__supplier',
        'delivery',
        'storage_location',
    )
    table = tables.AssetTable
    filterset = filtersets.AssetFilterSet
    filterset_form = forms.AssetFilterForm


@register_model_view(models.Asset, 'bulk_add', path='bulk-add', detail=False)
class AssetBulkCreateView(generic.BulkCreateView):
    queryset = models.Asset.objects.all()
    form = forms.AssetBulkAddForm
    model_form = forms.AssetBulkAddModelForm
    pattern_target = None
    template_name = 'netbox_inventory/asset_bulk_add.html'

    def _create_objects(self, form, request):
        new_objects = []
        for _ in range(form.cleaned_data['count']):
            # Reinstantiate the model form each time to avoid overwriting the same instance. Use a mutable
            # copy of the POST QueryDict so that we can update the target field value.
            model_form = self.model_form(request.POST.copy())
            del model_form.data['count']

            # Validate each new object independently.
            if model_form.is_valid():
                obj = model_form.save()
                new_objects.append(obj)
            else:
                # Raise an IntegrityError to break the for loop and abort the transaction.
                raise IntegrityError()

        return new_objects


@register_model_view(models.Asset, 'edit')
@register_model_view(models.Asset, 'add', detail=False)
class AssetEditView(generic.ObjectEditView):
    queryset = models.Asset.objects.all()
    form = forms.AssetForm
    template_name = 'netbox_inventory/asset_edit.html'


@register_model_view(models.Asset, 'delete')
class AssetDeleteView(generic.ObjectDeleteView):
    queryset = models.Asset.objects.all()

    def post(self, request, *args, **kwargs):
        """Override post method to check if asset is protected from deletion"""
        logger = logging.getLogger('netbox.netbox_inventory.views.AssetDeleteView')
        asset = self.get_object(**kwargs)
        protected_tags = get_tags_that_protect_asset_from_deletion()
        
        # Safety check: if no configuration is set, protected_tags might be None
        if not protected_tags:
            protected_tags = set()
        else:
            protected_tags = set(protected_tags)
            
        asset_tags = set(asset.tags.all().values_list('slug', flat=True))
        intersection_of_tags = set(asset_tags).intersection(protected_tags)

        if intersection_of_tags:
            error_msg = 'Cannot delete asset {} protected by tags: {}.'.format(
                asset,
                ', '.join(intersection_of_tags),
            )
            logger.info(error_msg)
            messages.warning(request, error_msg)

            form = ConfirmationForm(request.POST)
            if form.is_valid():
                return_url = form.cleaned_data.get('return_url')
                if return_url and return_url.startswith('/'):
                    return redirect(return_url)
                return redirect(self.get_return_url(request, asset))
            return redirect(asset.get_absolute_url())
        return super().post(request, *args, **kwargs)


@register_model_view(models.Asset, 'bulk_import', path='import', detail=False)
class AssetBulkImportView(generic.BulkImportView):
    queryset = models.Asset.objects.all()
    model_form = forms.AssetImportForm
    template_name = 'netbox_inventory/asset_bulk_import.html'


@register_model_view(models.Asset, 'bulk_edit', path='edit', detail=False)
class AssetBulkEditView(generic.BulkEditView):
    queryset = models.Asset.objects.all()
    filterset = filtersets.AssetFilterSet
    table = tables.AssetTable
    form = forms.AssetBulkEditForm

    def post(self, request, **kwargs):
        """Override post method to check if assets are protected from editing"""

        logger = logging.getLogger('netbox.views.BulkEditView')

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get('_all') and self.filterset is not None:
            pk_list = self.filterset(
                request.GET, self.queryset.values_list('pk', flat=True)
            ).qs
        else:
            pk_list = request.POST.getlist('pk')

        # Include the PK list as initial data for the form
        initial_data = {'pk': pk_list}
        protected_fields_by_tags = get_tags_and_edit_protected_asset_fields()
        
        # Safety check: if no configuration is set, protected_fields_by_tags might be None
        if not protected_fields_by_tags:
            protected_fields_by_tags = {}

        errors = []
        protected_assets = []

        if '_apply' in request.POST:
            form = self.form(request.POST, initial=initial_data)
            restrict_form_fields(form, request.user)

            if form.is_valid():
                nullified_fields = set(request.POST.getlist('_nullify'))

                queryset = self.queryset.filter(pk__in=pk_list)

                for asset in queryset:
                    asset_tags = set(asset.tags.all().values_list('slug', flat=True))
                    intersection_of_tags = set(asset_tags).intersection(
                        protected_fields_by_tags.keys()
                    )

                    # Check if asset is protected from editing
                    for tag in intersection_of_tags:
                        # TODO: Check if custom fields can be protected
                        protected_fields = set(protected_fields_by_tags[tag])

                        modified_fields = set(form.changed_data)
                        nullable = set(form.nullable_fields).intersection(
                            set(nullified_fields)
                        )

                        if modified_fields.intersection(
                            protected_fields
                        ) or nullable.intersection(protected_fields):
                            protected_assets.append(asset)

                            fields = modified_fields.intersection(
                                protected_fields
                            ).union(nullable.intersection(protected_fields))
                            errors.append(
                                'Cannot edit asset {} fields protected by tag {}: {}.'.format(
                                    asset,
                                    tag,
                                    ','.join(fields),
                                )
                            )
                if errors:
                    error_msg_protected_assets = f'Edit failed for all assets. Because of trying to modify protected fields on assets: {", ".join(map(str, set(protected_assets)))}.'
                    logger.info(errors + [error_msg_protected_assets])
                    messages.warning(request, ' '.join(errors))
                    messages.warning(request, error_msg_protected_assets)
                    return redirect(self.get_return_url(request))
        return super().post(request, **kwargs)


@register_model_view(models.Asset, 'bulk_delete', path='delete', detail=False)
class AssetBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Asset.objects.all()
    filterset = filtersets.AssetFilterSet
    table = tables.AssetTable

    def post(self, request, *args, **kwargs):
        """Override post method to check if assets are protected from deletion"""
        logger = logging.getLogger('netbox.views.BulkDeleteView')
        model = self.queryset.model
        if request.POST.get('_all'):
            qs = model.objects.all()
            if self.filterset is not None:
                qs = self.filterset(request.GET, qs).qs
            pk_list = qs.only('pk').values_list('pk', flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist('pk')]

        queryset = self.queryset.filter(pk__in=pk_list)

        protected_tags = get_tags_that_protect_asset_from_deletion()
        
        # Safety check: if no configuration is set, protected_tags might be None
        if not protected_tags:
            protected_tags = set()
        else:
            protected_tags = set(protected_tags)
            
        protected_assets = queryset.filter(tags__slug__in=protected_tags)

        if protected_assets:
            error_msg = "Cannot delete assets protected by tags: {}. Assets that can't be deleted: {}".format(
                ', '.join(protected_tags), ', '.join(map(str, protected_assets))
            )
            logger.info(error_msg)
            messages.warning(request, error_msg)
            return redirect(self.get_return_url(request))

        return super().post(request, *args, **kwargs)
