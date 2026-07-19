from django.urls import path



from .views import external_hub_update, external_hubs_list



urlpatterns = [

    path("hubs/", external_hubs_list, name="external-hubs-list"),

    path("hubs/<str:hub_type>/", external_hub_update, name="external-hub-update"),

]

