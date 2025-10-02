from django.core.validators import RegexValidator

PHONE_NUMBER_REGEX = r'^\\+?996\\d{9}$|^\\(\\d{3}\\)\\s?\\d{3}-\\d{3}$|^\\d{9}$|^$'
PHONE_NUMBER_VALIDATOR = RegexValidator(
    regex=PHONE_NUMBER_REGEX,
    message='Неверный формат номера телефона.',
    code='invalid_phone'
)
