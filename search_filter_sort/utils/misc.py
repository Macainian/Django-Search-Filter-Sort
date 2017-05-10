import importlib
import pytz

from django.utils.timezone import datetime


def class_strings_to_class(module_path, class_name):
    try:
        module = importlib.import_module(module_path)
    except:
        raise ImportError("Error: Import failed. Check module path of " + module_path)

    try:
        class_object = getattr(module, class_name)
    except:
        raise ImportError(
            "Error: Import failed. Check module path of " + module_path + " and class name of " + class_name
        )

    return class_object


def convert_age_to_date(age):
    today = datetime.today()
    year = today.year - age

    return datetime(year, today.month, today.day, tzinfo=pytz.utc)