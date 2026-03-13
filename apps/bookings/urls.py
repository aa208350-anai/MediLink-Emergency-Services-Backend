# apps/bookings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet

router = DefaultRouter()
router.register(r"bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("", include(router.urls)),
]



#
#  Method   URL                                  Action            Auth
#  -------  -----------------------------------  ----------------  ------
#  GET      /bookings/                           list              Auth
#  POST     /bookings/                           create            Auth
#  GET      /bookings/active/                    active (own)      Auth
#  GET      /bookings/history/                   history (own)     Auth
#
#  GET      /bookings/{id}/                      retrieve          Owner|Staff
#  PATCH    /bookings/{id}/                      partial_update    Owner|Staff
#  DELETE   /bookings/{id}/                      destroy           Staff
#
#  POST     /bookings/{id}/confirm/              confirm           Staff
#  POST     /bookings/{id}/dispatch/             dispatch          Staff
#  POST     /bookings/{id}/ongoing/              mark ongoing      Auth
#  POST     /bookings/{id}/arrived/              mark arrived      Auth
#  POST     /bookings/{id}/complete/             complete          Staff
#  POST     /bookings/{id}/cancel/               cancel            Owner|Staff
#
#  PATCH    /bookings/{id}/assign/               assign resources  Staff
#  PATCH    /bookings/{id}/fare/                 update fare       Staff
#  POST     /bookings/{id}/transition/           generic shift     Staff
#  GET      /bookings/{id}/logs/                 audit trail       Owner|Staff
#
# GET      /bookings/statuses/                  list statuses      Auth