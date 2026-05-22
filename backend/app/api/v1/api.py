from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    roles,
    permissions,
    departments,
    stock_general,
    health,
    build_plans,
    build_plan_imports,
    pm_families,
    build_requests,
    shipping,
    shipping_imports,
    lookups,
    component_suppliers,
    dashboard,
    documentation,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])
api_router.include_router(departments.router, prefix="/departments", tags=["Departments"])

api_router.include_router(health.router)
api_router.include_router(stock_general.router)

api_router.include_router(build_plans.router)
api_router.include_router(build_plan_imports.router)
api_router.include_router(pm_families.router)
api_router.include_router(build_requests.router)
api_router.include_router(shipping.router)
api_router.include_router(shipping_imports.router)
api_router.include_router(dashboard.router)
api_router.include_router(documentation.router)

api_router.include_router(lookups.forwarders_router, prefix="/forwarders", tags=["Forwarders"])
api_router.include_router(lookups.build_notes_router, prefix="/build-notes", tags=["Build Notes"])
api_router.include_router(
    lookups.support_activities_router, prefix="/support-activities", tags=["Support Activities"]
)
api_router.include_router(lookups.form_factors_router, prefix="/form-factors", tags=["Form Factors"])
api_router.include_router(
    lookups.silicon_steppings_router, prefix="/silicon-steppings", tags=["Silicon Steppings"]
)
api_router.include_router(lookups.components_router, prefix="/components", tags=["Components"])
api_router.include_router(lookups.suppliers_router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(component_suppliers.router)
api_router.include_router(
    lookups.build_descriptions_router, prefix="/build-descriptions", tags=["Build Descriptions"]
)
api_router.include_router(lookups.addresses_router, prefix="/addresses", tags=["Addresses"])
api_router.include_router(lookups.warehouses_router, prefix="/warehouses", tags=["Warehouses"])