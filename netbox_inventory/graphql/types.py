from typing import Annotated

import strawberry
import strawberry_django

from dcim.graphql.types import (
    DeviceType,
    DeviceTypeType,
    LocationType,
    ManufacturerType,
    ModuleType,
    ModuleTypeType,
    RackType,
    RackTypeType,
)
from extras.graphql.mixins import ImageAttachmentsMixin
from netbox.graphql.types import NetBoxObjectType, OrganizationalObjectType
from tenancy.graphql.types import ContactType, TenantType

from .filters import (
    AssetFilter,
    ContractFilter,
    DeliveryFilter,
    InventoryItemGroupFilter,
    InventoryItemTypeFilter,
    PurchaseFilter,
    SupplierFilter,
)
from netbox_inventory.models import (
    Asset,
    Contract,
    Delivery,
    InventoryItemGroup,
    InventoryItemType,
    Purchase,
    Supplier,
)

__all__ = (
    'AssetType',
    'ContractType',
    'DeliveryType',
    'InventoryItemGroupType',
    'InventoryItemTypeType',
    'PurchaseType',
    'SupplierType',
)


@strawberry_django.type(Asset, fields='__all__', filters=AssetFilter)
class AssetType(ImageAttachmentsMixin, NetBoxObjectType):
    device_type: (
        Annotated['DeviceTypeType', strawberry.lazy('dcim.graphql.types')] | None
    )
    module_type: (
        Annotated['ModuleTypeType', strawberry.lazy('dcim.graphql.types')] | None
    )
    inventoryitem_type: (
        Annotated[
            'InventoryItemTypeType', strawberry.lazy('netbox_inventory.graphql.types')
        ]
        | None
    )
    rack_type: Annotated['RackTypeType', strawberry.lazy('dcim.graphql.types')] | None
    tenant: Annotated['TenantType', strawberry.lazy('tenancy.graphql.types')] | None
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None
    module: Annotated['ModuleType', strawberry.lazy('dcim.graphql.types')] | None
    contact: Annotated['ContactType', strawberry.lazy('tenancy.graphql.types')] | None
    inventoryitem: (
        Annotated['InventoryItemType', strawberry.lazy('dcim.graphql.types')] | None
    )
    rack: Annotated['RackType', strawberry.lazy('dcim.graphql.types')] | None
    storage_location: (
        Annotated['LocationType', strawberry.lazy('dcim.graphql.types')] | None
    )
    owner: Annotated['TenantType', strawberry.lazy('tenancy.graphql.types')] | None
    delivery: (
        Annotated['DeliveryType', strawberry.lazy('netbox_inventory.graphql.types')]
        | None
    )
    purchase: (
        Annotated['PurchaseType', strawberry.lazy('netbox_inventory.graphql.types')]
        | None
    )

    @strawberry.field
    def kind(self) -> str:
        """Asset kind (device, module, inventoryitem, or rack)"""
        return self.kind


@strawberry_django.type(Contract, fields='__all__', filters=ContractFilter)
class ContractType(NetBoxObjectType):
    pass


@strawberry_django.type(Delivery, fields='__all__', filters=DeliveryFilter)
class DeliveryType(NetBoxObjectType):
    pass


@strawberry_django.type(Purchase, fields='__all__', filters=PurchaseFilter)
class PurchaseType(NetBoxObjectType):
    pass


@strawberry_django.type(Supplier, fields='__all__', filters=SupplierFilter)
class SupplierType(NetBoxObjectType):
    pass


@strawberry_django.type(
    InventoryItemType, fields='__all__', filters=InventoryItemTypeFilter
)
class InventoryItemTypeType(ImageAttachmentsMixin, NetBoxObjectType):
    manufacturer: Annotated['ManufacturerType', strawberry.lazy('dcim.graphql.types')]
    inventoryitem_group: (
        Annotated[
            'InventoryItemGroupType', strawberry.lazy('netbox_inventory.graphql.types')
        ]
        | None
    )


@strawberry_django.type(
    InventoryItemGroup, fields='__all__', filters=InventoryItemGroupFilter
)
class InventoryItemGroupType(OrganizationalObjectType):
    parent: (
        Annotated[
            'InventoryItemGroupType', strawberry.lazy('netbox_inventory.graphql.types')
        ]
        | None
    )
    inventoryitem_types: list[
        Annotated[
            'InventoryItemTypeType', strawberry.lazy('netbox_inventory.graphql.types')
        ]
    ]
    children: list[
        Annotated[
            'InventoryItemGroupType', strawberry.lazy('netbox_inventory.graphql.types')
        ]
    ]
