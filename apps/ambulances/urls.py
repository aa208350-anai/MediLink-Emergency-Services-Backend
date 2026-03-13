# apps/ambulances/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProviderViewSet, AmbulanceViewSet

router = DefaultRouter()
router.register(r"providers",   ProviderViewSet,   basename="provider")
router.register(r"ambulances",  AmbulanceViewSet,  basename="ambulance")

urlpatterns = [
    path("", include(router.urls)),
]


# ======================================================================
# Generated URL patterns (for reference)
# ======================================================================
#
#  Method   URL                                     Action               Auth
#  -------  --------------------------------------  -------------------  ----------------
#
#  -- Providers --
#  GET      /providers/                             list                 Public
#  POST     /providers/                             create               Auth
#  GET      /providers/{id}/                        retrieve             Public
#  PATCH    /providers/{id}/                        partial_update       ProviderAdmin|Staff
#  DELETE   /providers/{id}/                        destroy (deactivate) Staff
#  POST     /providers/{id}/verify/                 verify               Staff
#  POST     /providers/{id}/deactivate/             deactivate           Staff
#  GET      /providers/{id}/ambulances/             list ambulances      Public
#
#  -- Ambulances --
#  GET      /ambulances/                            list                 Public
#  POST     /ambulances/                            create               ProviderAdmin
#  GET      /ambulances/available/                  available only       Public
#  GET      /ambulances/{id}/                       retrieve             Public
#  PATCH    /ambulances/{id}/                       partial_update       ProviderAdmin|Staff
#  DELETE   /ambulances/{id}/                       soft-delete          ProviderAdmin|Staff
#  PATCH    /ambulances/{id}/status/                set status           Driver|ProviderAdmin|Staff
#  PATCH    /ambulances/{id}/location/              update GPS           Driver|Staff
#  PATCH    /ambulances/{id}/assign-driver/         assign driver        ProviderAdmin|Staff
#  DELETE   /ambulances/{id}/unassign-driver/       unassign driver      ProviderAdmin|Staff
#
#  Query params supported:
#    GET /ambulances/?type=ALS               filter by ambulance_type
#    GET /ambulances/?provider={uuid}        filter by provider
#    GET /ambulances/available/?provider={}  available filtered by provider
