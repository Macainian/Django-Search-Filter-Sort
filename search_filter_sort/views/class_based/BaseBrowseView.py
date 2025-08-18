import datetime
import operator
import logging
import json
import re
import pytz

from functools import reduce
from importlib import util

from dateutil import parser
from dateutil.tz import tz
from django.http import Http404, HttpResponse
from django.utils.timezone import now
from django.utils.translation import gettext
from django.db.models import Q
from django.http.response import HttpResponseRedirect
from django.views.generic import ListView
from django.conf import settings
from django.core.exceptions import FieldError

PSYCOPG_FOUND = util.find_spec("psycopg") is not None

if PSYCOPG_FOUND:
    from psycopg.types.range import TimestamptzRange, NumericRange

from search_filter_sort.utils.constants import RangeFilterTypes, PostgresRangeQueryFilterTypes
from search_filter_sort.utils.misc import class_strings_to_class, convert_age_to_date

logger = logging.getLogger(__name__)
USER_SEARCH_LIST_DEFAULT = ["username", "first_name", "last_name", "email"]

if hasattr(settings, "USER_SEARCH_LIST"):
    USER_SEARCH_LIST = settings.USER_SEARCH_LIST
else:
    USER_SEARCH_LIST = USER_SEARCH_LIST_DEFAULT


class BaseBrowseView(ListView):
    template_name = None
    model = None
    should_override_pagination = False
    searches = []
    filters = []
    filter_names = []
    sorts = []
    default_sort_by = ["-id"]
    default_pagination = 25
    deferments = []
    show_all_in_filter = True
    show_clear_sorts = True
    using_postgres = False
    postgres_filter_name_query_filter_type_map = {}

    search_by = None
    using_filters = None
    filtered_object_count = None

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(BaseBrowseView, self).dispatch(request, *args, **kwargs)
        except (ValueError, TypeError, FieldError) as e:
            # Related Field got invalid lookup: xxxx
            # This happens if get_queryset returns queryset that can't be evaluated by ListView
            # Implemented to make OpenVAS scanner happy (it thinks it is buffer overflow error, ha)

            # Call custom error handler (it can log additional info or call set_notification)
            self.get_queryset_error_handler()
            logger.error("BaseBrowseView: Incorrect filter name or value (%s)" % request.get_full_path())
            logger.error("BaseBrowseView: Exception %s" % e)

            # To avoid infinite redirection loop
            if request.path == request.get_full_path():
                raise

            return HttpResponseRedirect(request.path)
        # Error checking - returns JSON, but if this exception is not raised then HTML is usually the response content type
        except (Http404):
            url_args = request.GET.copy()
            invalid_page = url_args["page"]
            url_args["page"] = 1

            return HttpResponse(json.dumps({
                "message": gettext(
                    "<strong>Invalid Page:</strong> Page {invalid_page} does not exist.<br><em>You will be redirected back to page {page}.</em>"
                ).format(invalid_page=invalid_page, page=url_args["page"]),
                "status": "failed",
                "alert_status": "alert-info",
                "page": url_args["page"],
                "request_path": "{request_path}?{url_args}".format(request_path=request.path, url_args=url_args.urlencode())
            }), content_type="application/json")

    def get_context_data(self, **kwargs):
        context = super(BaseBrowseView, self).get_context_data(**kwargs)
        # check_search_fields()

        context["paginate_by"] = self.paginate_by
        context["search_by"] = self.search_by
        context["filters"] = self.filters
        context["filter_names"] = self.filter_names
        context["using_filters"] = self.using_filters
        context["default_pagination"] = self.default_pagination
        context["filtered_object_count"] = self.filtered_object_count
        context["total_object_count"] = self.model.objects.count()
        context["show_all_in_filter"] = self.show_all_in_filter
        context["show_clear_sorts"] = self.show_clear_sorts
        page_obj = context["page_obj"]
        context["pagination_page_navigation_range"] = list(range(page_obj.number - 3, page_obj.number + 4))

        return context

    def get_queryset_error_handler(self):
        # Called if filter provide in query string is incorrect. Can be modified by child classes.
        pass

    def get_queryset(self):
        self.searches = self.search_fields(self.model, [])

        if not self.should_override_pagination:
            try:
                self.paginate_by = int(self.request.GET.get("paginate_by", self.default_pagination))
            except:
                self.paginate_by = self.default_pagination

        should_return_empty = self.request.GET.get("__RETURN_EMPTY__", None)

        if should_return_empty:
            return self.model.objects.none()

        search_bys = self.request.GET.get("search_by", None)
        filter_names = self.request.GET.getlist("filter_name", None)
        filter_values = self.request.GET.getlist("filter_value", None)
        sort_bys = self.request.GET.getlist("sort_by", self.default_sort_by)

        if not sort_bys:
            raise ValueError("The default sort by is not in the view's sorts list")

        search_list = self.get_search_list(search_bys)
        filter_list = self.get_filter_list(filter_names, filter_values)
        sort_list = self.get_sort_list(sort_bys)

        # Search, filter, sort
        if search_list:
            list_of_search_bys_Q = [Q(**{key: value}) for key, value in search_list.items()]
            search_reduce = reduce(operator.or_, list_of_search_bys_Q)
        else:
            search_reduce = None

        if filter_list:
            list_of_filter_bys_Q = [[Q(**{key: value}) for value in array] for key, array in filter_list.items()]
            reduced_filters = []

            for array in list_of_filter_bys_Q:
                reduced_filters.append(reduce(operator.or_, array))

            filter_reduce = reduce(operator.and_, reduced_filters)
            self.using_filters = True
        else:
            filter_reduce = None
            self.using_filters = False

        if search_reduce and filter_reduce:
            queryset = self.model.objects.filter(search_reduce).filter(filter_reduce).defer(*self.deferments).distinct().order_by(*sort_list)
        elif search_reduce:
            queryset = self.model.objects.filter(search_reduce).defer(*self.deferments).distinct().order_by(*sort_list)
        elif filter_reduce:
            queryset = self.model.objects.filter(filter_reduce).defer(*self.deferments).distinct().order_by(*sort_list)
        else:
            queryset = self.model.objects.defer(*self.deferments).order_by(*sort_list)
            # queryset = sorted(self.model.objects.all(), key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split('(\d+)', x.name)])

        # TODO: Find a way to natural sort the queryset
        # SELECT * FROM job
        # ORDER BY(substring('name', '^[0-9]+'))::int -- cast to integer\
        #     , coalesce(substring('name', '[^0-9_].*$'), '')

        self.filtered_object_count = queryset.count()

        return queryset

    def get_search_list(self, search_bys):
        # Determine search_list
        search_list = {}

        if search_bys:
            self.search_by = search_bys

            for field in self.searches:
                field += "__icontains"
                search_list[field] = search_bys
        else:
            self.search_by = ""

        return search_list

    def get_filter_list(self, filter_names, filter_values):
        # Determine filter_list
        filter_list = {}
        self.define_filters()

        postgres_range_filter_dictionaries = {}
        datetime_range_filter_dictionaries = {}

        for i in range(len(filter_names)):
            filter_name = filter_names[i]

            # This is only false if there are more filter_names than filter_values. Should be equal.
            if i < len(filter_values):
                values = filter_values[i].split(",")
                split_regex = re.compile("__lte|__lt|__gte|__gt")
                split_filter_name = split_regex.split(filter_name)
                filter_type = next(iter(split_regex.findall(filter_name)), None)
                stripped_filter_name = split_filter_name[0]
                stripped_filter_info = None

                if len(split_filter_name) != 1:
                    stripped_filter_info = split_filter_name[1].replace("_", "", 1)

                if stripped_filter_info:
                    if RangeFilterTypes.DATETIME in stripped_filter_info:
                        dates_or_times = stripped_filter_info.split("_")[1] + "s"
                        new_filter_name = stripped_filter_name + filter_type

                        if not datetime_range_filter_dictionaries.get(new_filter_name, None):
                            datetime_range_filter_dictionaries[new_filter_name] = {
                                "times": [],
                                "dates": [],
                                "filter_type": filter_type
                            }

                        datetime_range_filter_dictionaries[new_filter_name][dates_or_times] = self.convert_values(values, stripped_filter_info.split("_")[1])
                        continue

                    if self.using_postgres:
                        self.create_or_edit_postgres_range_filter_dictionary(postgres_range_filter_dictionaries, stripped_filter_name, filter_type, stripped_filter_info, values)
                    else:
                        if stripped_filter_info == RangeFilterTypes.AGE:
                            values = [convert_age_to_date(int(filter_values[i]))]

                        if filter_type:
                            filter_name = stripped_filter_name + filter_type

                        filter_list[filter_name] = self.convert_values(values, stripped_filter_info)
                else:
                    if filter_type:
                        filter_name = stripped_filter_name + filter_type

                    filter_list[filter_name] = self.convert_values(values, stripped_filter_info)
            else:
                break

        for datetime_range_filter_name_and_type, datetime_range_filter_date_and_time_values in datetime_range_filter_dictionaries.items():
            filter_name = "__".join(datetime_range_filter_name_and_type.split("__")[0:-1])
            filter_type = datetime_range_filter_date_and_time_values["filter_type"]
            datetime_values = []
            dates = datetime_range_filter_date_and_time_values["dates"]
            times = datetime_range_filter_date_and_time_values["times"]

            if not dates:
                self.create_or_edit_postgres_range_filter_dictionary(postgres_range_filter_dictionaries, filter_name, filter_type, RangeFilterTypes.DATETIME, [])
                continue
            if not times:
                times = [date for date in dates]

            date_time_pairs = zip(dates, times)

            for date_time_pair in date_time_pairs:
                datetime_values.append(str(tz.resolve_imaginary(datetime.datetime.combine(date_time_pair[0].date(), date_time_pair[1].time())).replace(tzinfo=date_time_pair[0].tzinfo)))

            if self.using_postgres:
                self.create_or_edit_postgres_range_filter_dictionary(postgres_range_filter_dictionaries, filter_name, filter_type, RangeFilterTypes.DATETIME, datetime_values)
            else:
                filter_list[filter_name] = self.convert_values(datetime_values, RangeFilterTypes.DATETIME)

        for postgres_range_filter_name, postgres_range_filter_dictionary in postgres_range_filter_dictionaries.items():
            postgres_query_filter_type = self.postgres_filter_name_query_filter_type_map.get(postgres_range_filter_name, PostgresRangeQueryFilterTypes.CONTAINED_BY)
            query_filter_name = postgres_range_filter_name + postgres_query_filter_type
            lowers = postgres_range_filter_dictionary["lowers"]
            uppers = postgres_range_filter_dictionary["uppers"]
            range_type = postgres_range_filter_dictionary["range_type"]
            lower_bound = postgres_range_filter_dictionary.get("lower_bound", "[")
            upper_bound = postgres_range_filter_dictionary.get("upper_bound", "]")

            if not lower_bound:
                lower_bound = "["

            if not upper_bound:
                upper_bound = "]"

            bounds_string = lower_bound + upper_bound
            filter_list[query_filter_name] = self.create_psycopg2_range_object_list(lowers, uppers, range_type, bounds_string)

        return filter_list

    def get_sort_list(self, sort_bys):
        # Determine sort_list
        sort_list = list(sort_bys)
        count = 0

        for i in range(len(sort_bys)):
            if "-" in sort_bys[i]:
                base_sort = sort_bys[i].split("-")[1]
            else:
                base_sort = sort_bys[i]

            if base_sort not in self.sorts:
                sort_list.remove(sort_bys[i])
                logger.debug("Sort of " + base_sort + " is not in the sorts.")
                count -= 1
            elif "last_name" in sort_bys[i]:  # Special clause for last_names/first_names
                sort_list.insert(count, sort_bys[i].replace("last_name", "first_name"))
                count += 1
            elif base_sort == "birthday":  # Special clause for birthday/age. Need to reverse order because it is backwards for some reason.
                if sort_bys[i] == "birthday":
                    sort_list[count] = "-birthday"
                else:
                    sort_list[count] = "birthday"

            count += 1

        return sort_list

    def define_filters(self):
        self.filters = []
        self.filter_names = []

    def add_select_filter(self, html_name, filter_name, html_options_code):
        html_code = '<select class="multi-select form-control sfs-filter" id="' + filter_name + '_filter" name="' + filter_name + '_filter" autocomplete="off" multiple>'
        html_code += html_options_code + '</select>'

        self.filters.append(
            {
                "filter_name": filter_name,
                "html_name": html_name,
                "html_code": html_code
            }
        )

        self.filter_names.append(filter_name)

    def add_range_filter(self, html_name, filter_name, filter_type, step_size="1", bounds="[]", postgres_range_field_comparison_type=None):
        lower_bound = bounds[0]
        upper_bound = bounds[1]

        if lower_bound == "[":
            lower_bound_format = "__gte_"
        elif lower_bound == "(":
            lower_bound_format = "__gt_"
        else:
            raise Exception("Invalid lower bound of " + lower_bound)

        if upper_bound == "]":
            upper_bound_format = "__lte_"
        elif upper_bound == ")":
            upper_bound_format = "__lt_"
        else:
            raise Exception("Invalid upper bound of " + upper_bound)

        if self.using_postgres and postgres_range_field_comparison_type:
            self.postgres_filter_name_query_filter_type_map[filter_name] = postgres_range_field_comparison_type
        elif postgres_range_field_comparison_type:
            raise Exception("Datetime Tz Ranges are not supported unless you are using a postgres database. ")

        lower_filter_name = filter_name + lower_bound_format + filter_type
        upper_filter_name = filter_name + upper_bound_format + filter_type

        if filter_type == RangeFilterTypes.AGE:
            filter_type = RangeFilterTypes.NUMBER

        if filter_type == RangeFilterTypes.DATETIME:
            lower_filter_date_name = lower_filter_name + "_" + RangeFilterTypes.DATE
            lower_filter_time_name = lower_filter_name + "_" + RangeFilterTypes.TIME
            upper_filter_date_name = upper_filter_name + "_" + RangeFilterTypes.DATE
            upper_filter_time_name = upper_filter_name + "_" + RangeFilterTypes.TIME
            html_code = \
                '<input type="' + RangeFilterTypes.DATE + '" class="range-filter form-control" id="' + lower_filter_date_name + '_filter" ' + \
                'name="' + lower_filter_date_name + '" step="' + step_size + '" style="max-width:max-content" />' + \
                '<input type="' + RangeFilterTypes.TIME + '" class="range-filter form-control" id="' + lower_filter_time_name + '_filter" ' + \
                'name="' + lower_filter_time_name + '" step="' + step_size + '" style="max-width:max-content" />' + \
                '<strong> - </strong>' + \
                '<input type="' + RangeFilterTypes.DATE + '" class="range-filter form-control" id="' + upper_filter_date_name + '_filter" ' + \
                'name="' + upper_filter_date_name + '" step="' + step_size + '" style="max-width:max-content" />' + \
                '<input type="' + RangeFilterTypes.TIME + '" class="range-filter form-control" id="' + upper_filter_time_name + '_filter" ' + \
                'name="' + upper_filter_time_name + '" step="' + step_size + '" style="max-width:max-content" />'

            self.filter_names.append(lower_filter_date_name)
            self.filter_names.append(lower_filter_time_name)
            self.filter_names.append(upper_filter_date_name)
            self.filter_names.append(upper_filter_time_name)
        else:
            html_code = \
                '<input type="' + filter_type + '" class="range-filter form-control" id="' + lower_filter_name + '_filter" ' + \
                'name="' + lower_filter_name + '" step="' + step_size + '" style="max-width:max-content" />' + \
                '<strong> - </strong>' + \
                '<input type="' + filter_type + '" class="range-filter form-control" id="' + upper_filter_name + '_filter" ' + \
                'name="' + upper_filter_name + '" step="' + step_size + '" style="max-width: max-content" />'

            self.filter_names.append(lower_filter_name)
            self.filter_names.append(upper_filter_name)

        self.filters.append(
            {
                "html_name": html_name,
                "html_code": html_code
            }
        )

    def search_fields(self, class_object, list_of_used_classes):
        object_search_list = []

        if class_object in list_of_used_classes:
            return []
        else:
            list_of_used_classes.append(class_object)

        if class_object.__name__ == "User":
            search_list = [search_item for search_item in USER_SEARCH_LIST]
        else:
            object_dependencies = class_object.object_dependencies()

            for object_dependency in object_dependencies:
                if object_dependency[2] == "User":
                    object_search_list += [
                        str(object_dependency[0] + "__{0}").format(search_item) for search_item in USER_SEARCH_LIST
                    ]
                else:
                    other_class_object = class_strings_to_class(object_dependency[1], object_dependency[2])
                    other_object_search_list = self.search_fields(other_class_object, list_of_used_classes)
                    object_search_list += [
                        str(object_dependency[0] + "__{0}").format(search_item) for search_item in other_object_search_list
                    ]

            search_list = class_object.basic_search_list() + class_object.special_search_list() + object_search_list

        return search_list

    def convert_values(self, values, range_type):
        the_now = now()
        if settings.TIME_ZONE:
            timezone = pytz.timezone(settings.TIME_ZONE)
            the_now = the_now.astimezone(timezone)

        current_time_zone = the_now.strftime("%z")
        new_values = []

        for value in values:
            if value == "__NONE_OR_BLANK__":
                new_values.append("")
                value = None
            elif value == "__NONE__":
                value = None
            elif value == "__BLANK__":
                value = ""
            elif value == "__TRUE__":
                value = True
            elif value == "__FALSE__":
                value = False
            elif range_type == RangeFilterTypes.DATE:
                value = parser.parse(value + " 00:00:00" + current_time_zone)
            elif range_type == RangeFilterTypes.TIME:
                value = parser.parse(value)
            elif range_type in [RangeFilterTypes.NUMBER, RangeFilterTypes.AGE]:
                try:
                    value = int(value)
                except ValueError:
                    value = float(value)

            new_values.append(value)

        return new_values

    def create_psycopg2_range_object_list(self, lower_bounds, upper_bounds, range_type, bounds_string):
        bound_value_length = max(len(lower_bounds), len(upper_bounds))

        if not lower_bounds:
            lower_bounds = [None for i in range(0, bound_value_length)]

        if not upper_bounds:
            upper_bounds = [None for i in range(0, bound_value_length)]

        lower_and_upper_pairs = zip(lower_bounds, upper_bounds)
        if range_type in [RangeFilterTypes.DATETIME, RangeFilterTypes.DATE, RangeFilterTypes.TIME]:
            TZ_RANGE_OBJECT = TimestamptzRange
        elif range_type in [RangeFilterTypes.NUMBER, RangeFilterTypes.AGE]:
            TZ_RANGE_OBJECT = NumericRange
        else:
            raise Exception("Range Type of " + range_type + "does not map to any current psycopg2 range object")

        return [TZ_RANGE_OBJECT(lower_and_upper_pair[0], lower_and_upper_pair[1], bounds=bounds_string) for lower_and_upper_pair in lower_and_upper_pairs]

    def create_or_edit_postgres_range_filter_dictionary(self, postgres_range_filter_dictionaries, filter_name, filter_type, range_type, values):
        if not postgres_range_filter_dictionaries.get(filter_name, None):
            postgres_range_filter_dictionaries[filter_name] = {
                "lowers": [],
                "uppers": [],
                "range_type": range_type,
                "lower_bound": None,
                "upper_bound": None
            }

        if "g" in filter_type:
            upper_or_lower_bound = "lower"
            bound_character = "("

            if "te" in filter_type:
                bound_character = "["
        elif "l" in filter_type:
            upper_or_lower_bound = "upper"
            bound_character = ")"

            if "te" in filter_type:
                bound_character = "]"
        else:
            raise Exception("Invalid bound of " + filter_type)

        postgres_range_filter_dictionaries[filter_name][upper_or_lower_bound + "_bound"] = bound_character
        postgres_range_filter_dictionaries[filter_name][upper_or_lower_bound + "s"] = self.convert_values(values, range_type)
