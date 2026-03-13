# apps/hospitals/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HospitalViewSet, ReviewModerationViewSet

router = DefaultRouter()
router.register(r"hospitals", HospitalViewSet,          basename="hospital")
router.register(r"reviews",   ReviewModerationViewSet,  basename="review-moderation")

urlpatterns = [
    path("", include(router.urls)),
]


# ======================================================================
# Generated URL patterns (for reference)
# ======================================================================
#
#  Method   URL                                       Action                Auth
#  -------  ----------------------------------------  --------------------  ----------------
#
#  -- Hospitals (public search & discovery) --
#  GET      /hospitals/                               list / search         Public
#  POST     /hospitals/                               register              Auth
#  GET      /hospitals/districts/                     unique districts      Public
#  GET      /hospitals/for-emergency/?emergency_type= recommended           Public
#
#  GET      /hospitals/{id}/                          detail                Public
#  PATCH    /hospitals/{id}/                          update own profile    HospitalAdmin|Staff
#  DELETE   /hospitals/{id}/                          deactivate            Staff
#
#  POST     /hospitals/{id}/verify/                   verify                Staff
#  POST     /hospitals/{id}/deactivate/               deactivate            Staff
#  PATCH    /hospitals/{id}/feature/                  toggle featured       Staff
#  PATCH    /hospitals/{id}/status/                   set status            HospitalAdmin|Staff
#  PATCH    /hospitals/{id}/beds/                     update bed count      HospitalAdmin|Staff
#
#  GET      /hospitals/{id}/reviews/                  approved reviews      Public
#  POST     /hospitals/{id}/reviews/                  submit review         Auth (client)
#
#  -- Review moderation (staff) --
#  GET      /reviews/pending/                         pending reviews       Staff
#  POST     /reviews/{id}/approve/                    approve               Staff
#  DELETE   /reviews/{id}/reject/                     reject & delete       Staff
#
# ======================================================================
#
#  Search query params for GET /hospitals/:
#    ?q=mulago                search name / description / address
#    ?district=Kampala        filter by district
#    ?speciality=cardiac      filter by speciality (see Speciality choices)
#    ?type=public             filter by hospital_type
#    ?accepting=true          only hospitals accepting patients (default: true)
#    ?is_24_hours=true        24-hour facilities only
#    ?has_icu=true            ICU facilities only
#    ?accepts_insurance=true  insurance-accepting only
# ======================================================================