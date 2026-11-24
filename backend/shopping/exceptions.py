from rest_framework.exceptions import APIException


class ConflictError(APIException):
    status_code = 409
    default_detail = "Operacja jest sprzeczna z aktualnym stanem zasobu."
    default_code = "conflict"


class GoneError(APIException):
    status_code = 410
    default_detail = "Zasób nie jest już dostępny."
    default_code = "gone"


class UnsupportedCurrency(APIException):
    status_code = 400
    default_detail = "Nieobsługiwana waluta."
    default_code = "unsupported_currency"


class ExternalServiceError(APIException):
    status_code = 503
    default_detail = "Zewnętrzna usługa kursów walut jest chwilowo niedostępna."
    default_code = "external_service_unavailable"
