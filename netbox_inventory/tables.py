import django_tables2 as tables
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from dcim.tables import DeviceTypeTable, ModuleTypeTable, RackTypeTable
from netbox.tables import NetBoxTable, columns
from utilities.tables import register_table_column

from .models import (
    Asset,
    Contract,
    Delivery,
    InventoryItemGroup,
    InventoryItemType,
    Purchase,
    Supplier,
)
from .template_content import WARRANTY_PROGRESSBAR

__all__ = (
    'AssetTable',
    'ContractTable',
    'DeliveryTable',
    'InventoryItemGroupTable',
    'InventoryItemTypeTable',
    'PurchaseTable',
    'SupplierTable',
)


#
# Assets
#


class InventoryItemGroupTable(NetBoxTable):
    name = columns.MPTTColumn(
        linkify=True,
    )
    asset_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:asset_list',
        url_params={'inventoryitem_group_id': 'pk'},
        verbose_name='Assets',
    )
    inventoryitem_type_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:inventoryitemtype_list',
        url_params={'inventoryitem_group_id': 'pk'},
        verbose_name='Inventory Item Types',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = InventoryItemGroup
        fields = (
            'pk',
            'id',
            'name',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
            'actions',
            'asset_count',
            'inventoryitem_type_count',
        )
        default_columns = (
            'name',
            'asset_count',
            'inventoryitem_type_count',
        )


class InventoryItemTypeTable(NetBoxTable):
    manufacturer = tables.Column(
        linkify=True,
    )
    model = tables.Column(
        linkify=True,
    )
    inventoryitem_group = tables.Column(
        linkify=True,
    )
    asset_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:asset_list',
        url_params={'inventoryitem_type_id': 'pk'},
        verbose_name='Assets',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = InventoryItemType
        fields = (
            'pk',
            'id',
            'manufacturer',
            'model',
            'slug',
            'part_number',
            'inventoryitem_group',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
            'actions',
            'asset_count',
        )
        default_columns = (
            'manufacturer',
            'model',
            'asset_count',
        )


class AssetTable(NetBoxTable):
    name = tables.Column(
        linkify=True,
    )
    serial = tables.Column(
        linkify=True,
    )
    kind = tables.Column(
        accessor='get_kind_display',
        orderable=False,
    )
    manufacturer = tables.Column(
        accessor='hardware_type__manufacturer',
        linkify=True,
    )
    hardware_type = tables.Column(
        linkify=True,
        verbose_name='Hardware Type',
    )
    inventoryitem_group = tables.Column(
        accessor='inventoryitem_type__inventoryitem_group',
        linkify=True,
        verbose_name='Inventory Item Group',
    )
    status = columns.ChoiceFieldColumn()
    hardware = tables.Column(
        linkify=True,
        order_by=('device', 'module'),
    )
    hardware_role = tables.Column(
        accessor=columns.Accessor('hardware__role'),
        linkify=True,
        verbose_name='Hardware Role',
    )
    installed_site = tables.Column(
        linkify=True,
        verbose_name='Installed Site',
    )
    installed_location = tables.Column(
        linkify=True,
        verbose_name='Installed Location',
    )
    installed_rack = tables.Column(
        linkify=True,
        verbose_name='Installed Rack',
    )
    installed_device = tables.Column(
        linkify=True,
        verbose_name='Installed Device',
    )
    tenant = tables.Column(
        linkify=True,
    )
    contact = tables.Column(
        linkify=True,
    )
    storage_location = tables.Column(
        linkify=True,
    )
    owner = tables.Column(
        linkify=True,
    )
    supplier = tables.Column(
        accessor='purchase__supplier',
        linkify=True,
    )
    purchase = tables.Column(
        linkify=True,
    )
    delivery = tables.Column(
        linkify=True,
    )
    contract = columns.TemplateColumn(
        template_code='''
        {% for contract in record.contract.all %}
            <a href="{{ contract.get_absolute_url }}">{{ contract }}</a>{% if not forloop.last %}, {% endif %}
        {% empty %}
            —
        {% endfor %}
        ''',
        verbose_name='Contracts',
        orderable=False,
    )
    purchase_date = columns.DateColumn(
        accessor='purchase__date',
        verbose_name='Purchase Date',
    )
    delivery_date = columns.DateColumn(
        accessor='delivery__date',
        verbose_name='Delivery Date',
    )
    current_site = tables.Column(
        linkify=True,
        verbose_name='Current Site',
        orderable=False,
    )
    current_location = tables.Column(
        linkify=True,
        verbose_name='Current Location',
        orderable=False,
    )
    warranty_progress = columns.TemplateColumn(
        template_code=WARRANTY_PROGRESSBAR,
        order_by='warranty_end',
        # orderable=False,
        verbose_name='Warranty remaining',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()
    actions = columns.ActionsColumn(
        extra_buttons="""
            {% if record.hardware %}
            <a href="#" class="btn btn-sm btn-outline-dark disabled">
                <i class="mdi mdi-vector-difference-ba" aria-hidden="true"></i>
            </a>
            {% else %}
            <a href="{% url 'plugins:netbox_inventory:asset_'|add:record.kind|add:'_create' %}?asset_id={{ record.pk }}" class="btn btn-sm btn-green" title="Create hardware from asset">
                <i class="mdi mdi-vector-difference-ba"></i>
            </a>
            {% endif %}
            <a href="{% url 'plugins:netbox_inventory:asset_assign' record.pk %}" class="btn btn-sm btn-orange" title="Edit hardware assignment">
                <i class="mdi mdi-vector-link"></i>
            </a>
        """
    )

    def order_manufacturer(self, queryset, is_descending):
        queryset = queryset.annotate(
            manufacturer=Coalesce(
                'device_type__manufacturer',
                'module_type__manufacturer',
                'inventoryitem_type__manufacturer',
                'rack_type__manufacturer',
            )
        ).order_by(
            ('-' if is_descending else '') + 'manufacturer',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def order_hardware_type(self, queryset, is_descending):
        queryset, _ = self.order_manufacturer(queryset, is_descending)
        queryset = queryset.annotate(
            model=Coalesce(
                'device_type__model',
                'module_type__model',
                'inventoryitem_type__model',
                'rack_type__model',
            )
        ).order_by(
            ('-' if is_descending else '') + 'manufacturer',
            ('-' if is_descending else '') + 'model',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def order_hardware(self, queryset, is_descending):
        queryset = queryset.annotate(
            hw=Coalesce(
                'device__name',
                'module__device__name',
                'inventoryitem__device__name',
                'rack__name',
            )
        ).order_by(
            ('-' if is_descending else '') + 'hw',
            ('-' if is_descending else '') + 'module__module_bay',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def order_hardware_role(self, queryset, is_descending):
        queryset = queryset.annotate(
            role_name=Coalesce(
                'device__role__name',
                'inventoryitem__role__name',
                'rack__role__name',
            )
        ).order_by(
            ('-' if is_descending else '') + 'role_name',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def _order_annotate_installed(self, queryset):
        return queryset.annotate(
            site_name=Coalesce(
                'device__site__name',
                'module__device__site__name',
                'inventoryitem__device__site__name',
                'rack__site__name',
            ),
            location_name=Coalesce(
                'device__location__name',
                'module__device__location__name',
                'inventoryitem__device__location__name',
                'rack__location__name',
            ),
            rack_name=Coalesce(
                'device__rack__name',
                'module__device__rack__name',
                'inventoryitem__device__rack__name',
                'rack__name',
            ),
            device_name=Coalesce(
                'device__name', 'module__device__name', 'inventoryitem__device__name'
            ),
        )

    def order_installed_site(self, queryset, is_descending):
        queryset = self._order_annotate_installed(queryset).order_by(
            ('-' if is_descending else '') + 'site_name',
            ('-' if is_descending else '') + 'device_name',
            ('-' if is_descending else '') + 'module__module_bay',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def order_installed_location(self, queryset, is_descending):
        queryset = self._order_annotate_installed(queryset).order_by(
            ('-' if is_descending else '') + 'site_name',
            ('-' if is_descending else '') + 'location_name',
            ('-' if is_descending else '') + 'device_name',
            ('-' if is_descending else '') + 'module__module_bay',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def order_installed_rack(self, queryset, is_descending):
        queryset = self._order_annotate_installed(queryset).order_by(
            ('-' if is_descending else '') + 'site_name',
            ('-' if is_descending else '') + 'location_name',
            ('-' if is_descending else '') + 'rack_name',
            ('-' if is_descending else '') + 'device_name',
            ('-' if is_descending else '') + 'module__module_bay',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    def order_installed_device(self, queryset, is_descending):
        queryset = self._order_annotate_installed(queryset).order_by(
            ('-' if is_descending else '') + 'device_name',
            ('-' if is_descending else '') + 'module__module_bay',
            ('-' if is_descending else '') + 'serial',
        )
        return (queryset, True)

    class Meta(NetBoxTable.Meta):
        model = Asset
        fields = (
            'pk',
            'id',
            'name',
            'asset_tag',
            'serial',
            'status',
            'kind',
            'manufacturer',
            'hardware_type',
            'inventoryitem_group',
            'hardware',
            'hardware_role',
            'installed_site',
            'installed_location',
            'installed_rack',
            'installed_device',
            'tenant',
            'contact',
            'storage_site',
            'storage_location',
            'current_site',
            'current_location',
            'owner',
            'supplier',
            'purchase',
            'delivery',
            'contract',
            'purchase_date',
            'delivery_date',
            'warranty_start',
            'warranty_end',
            'warranty_progress',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'id',
            'name',
            'serial',
            'kind',
            'manufacturer',
            'hardware_type',
            'asset_tag',
            'status',
            'hardware',
            'contract',
            'tags',
        )


#
# Deliveries
#


class SupplierTable(NetBoxTable):
    name = tables.Column(
        linkify=True,
    )
    purchase_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:purchase_list',
        url_params={'supplier_id': 'pk'},
        verbose_name='Purchases',
    )
    delivery_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:delivery_list',
        url_params={'supplier_id': 'pk'},
        verbose_name='Deliveries',
    )
    asset_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:asset_list',
        url_params={'supplier_id': 'pk'},
        verbose_name='Assets',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = Supplier
        fields = (
            'pk',
            'id',
            'name',
            'slug',
            'description',
            'comments',
            'purchase_count',
            'delivery_count',
            'asset_count',
            'tags',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'name',
            'asset_count',
        )


class PurchaseTable(NetBoxTable):
    supplier = tables.Column(
        linkify=True,
    )
    name = tables.Column(
        linkify=True,
    )
    status = columns.ChoiceFieldColumn()
    delivery_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:delivery_list',
        url_params={'purchase_id': 'pk'},
        verbose_name='Deliveries',
    )
    asset_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:asset_list',
        url_params={'purchase_id': 'pk'},
        verbose_name='Assets',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = Purchase
        fields = (
            'pk',
            'id',
            'name',
            'supplier',
            'status',
            'date',
            'description',
            'comments',
            'delivery_count',
            'asset_count',
            'tags',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'name',
            'supplier',
            'date',
            'asset_count',
        )


class DeliveryTable(NetBoxTable):
    supplier = tables.Column(
        accessor=columns.Accessor('purchase__supplier'),
        linkify=True,
    )
    purchase = tables.Column(
        linkify=True,
    )
    date = columns.DateColumn(
        verbose_name='Delivery Date',
    )
    purchase_date = columns.DateColumn(
        accessor=columns.Accessor('purchase__date'),
        verbose_name='Purchase Date',
    )
    receiving_contact = tables.Column(
        linkify=True,
    )
    name = tables.Column(
        linkify=True,
    )
    asset_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:asset_list',
        url_params={'delivery_id': 'pk'},
        verbose_name='Assets',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        model = Delivery
        fields = (
            'pk',
            'id',
            'name',
            'purchase',
            'supplier',
            'date',
            'purchase_date',
            'receiving_contact',
            'description',
            'comments',
            'asset_count',
            'tags',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'name',
            'purchase',
            'date',
            'asset_count',
        )


# ========================
# DCIM model table columns
# ========================

asset_count = columns.LinkedCountColumn(
    viewname='plugins:netbox_inventory:asset_list',
    url_params={'device_type_id': 'pk'},
    verbose_name=_('Assets'),
    accessor='assets__count',
)

register_table_column(asset_count, 'assets', DeviceTypeTable)


asset_count = columns.LinkedCountColumn(
    viewname='plugins:netbox_inventory:asset_list',
    url_params={'module_type_id': 'pk'},
    verbose_name=_('Assets'),
    accessor='assets__count',
)

register_table_column(asset_count, 'assets', ModuleTypeTable)


asset_count = columns.LinkedCountColumn(
    viewname='plugins:netbox_inventory:asset_list',
    url_params={'rack_type_id': 'pk'},
    verbose_name=_('Assets'),
    accessor='assets__count',
)

register_table_column(asset_count, 'assets', RackTypeTable)


class ContractTable(NetBoxTable):
    name = tables.Column(
        linkify=True,
    )
    supplier = tables.Column(
        linkify=True,
    )
    contract_type = columns.ChoiceFieldColumn()
    status = columns.TemplateColumn(
        template_code='''
        {% load helpers %}
        {% if record.is_expired and record.status != 'expired' %}
            <span class="badge bg-danger" title="Contract expired on {{ record.end_date }}">
                <i class="mdi mdi-alert-circle"></i> {{ record.get_status_display }}
            </span>
        {% else %}
            {% badge record.get_status_display bg_color=record.get_status_color %}
        {% endif %}
        ''',
        verbose_name='Status',
    )
    start_date = columns.DateColumn()
    end_date = columns.DateColumn()
    renewal_date = columns.DateColumn()
    cost = tables.Column()
    currency = tables.Column()
    asset_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_inventory:asset_list',
        url_params={'contract_id': 'pk'},
        verbose_name='Assets',
    )
    is_active = columns.BooleanColumn(
        accessor='is_active',
        verbose_name='Active',
    )
    days_until_expiry = columns.TemplateColumn(
        template_code='''
        {% if record.is_expired %}
            <span class="text-danger">
                <i class="mdi mdi-alert-circle"></i> Expired
            </span>
        {% elif record.days_until_expiry <= 30 %}
            <span class="text-warning">
                <i class="mdi mdi-alert"></i> {{ record.days_until_expiry }} days
            </span>
        {% elif record.days_until_expiry <= 90 %}
            <span class="text-info">
                {{ record.days_until_expiry }} days
            </span>
        {% else %}
            {{ record.days_until_expiry }} days
        {% endif %}
        ''',
        accessor='days_until_expiry',
        verbose_name='Days Until Expiry',
    )
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn()

    def order_days_until_expiry(self, queryset, is_descending):
        """
        Custom ordering for days_until_expiry column.
        Orders by end_date (ascending = soonest expiry first, descending = latest expiry first)
        """
        direction = '-' if is_descending else ''
        return queryset.order_by(f'{direction}end_date'), True

    class Meta(NetBoxTable.Meta):
        model = Contract
        fields = (
            'pk',
            'id',
            'name',
            'contract_id',
            'supplier',
            'contract_type',
            'status',
            'start_date',
            'end_date',
            'renewal_date',
            'cost',
            'currency',
            'description',
            'asset_count',
            'is_active',
            'days_until_expiry',
            'comments',
            'tags',
            'created',
            'last_updated',
            'actions',
        )
        default_columns = (
            'name',
            'supplier',
            'contract_type',
            'status',
            'start_date',
            'end_date',
            'days_until_expiry',
            'asset_count',
            'is_active',
        )
