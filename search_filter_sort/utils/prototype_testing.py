import sys
import inspect


# class SearchableClass(object):
#     __metaclass__ = ABCMeta
#
#     @abstractmethod
#     def basic_search_list(self):
#         return NotImplemented
#
#     @abstractmethod
#     def special_search_list(self):
#         return NotImplemented
#
#     @abstractmethod
#     def object_dependencies(self):
#         return NotImplemented


def check_search_fields(modules):
    verify_search_fields(modules)


def verify_search_fields(modules, class_exclusions=None, variable_exclusions=None):
    for module in modules:
        for name, class_object in inspect.getmembers(sys.modules[module]):
            if inspect.isclass(class_object):
                all_class_items = vars(class_object)
                class_items = {}

                if "basic_search_list" not in all_class_items:
                    print(class_object.__name__ + " is missing basic_search_list() static method")

                if "special_search_list" not in all_class_items:
                    print(class_object.__name__ + " is missing special_search_list() static method")

                if "object_dependencies" not in all_class_items:
                    print(class_object.__name__ + " is missing object_dependencies() static method")

                try:
                    print(class_object._meta.fields)
                except:
                    pass

                for class_item in all_class_items:
                    # print type(all_class_items[class_item])
                    # some_types = ("function", "staticmethod",)
                    # if isinstance(all_class_items[class_item], "function") or isinstance(all_class_items[class_item], "staticmethod"):
                    #     print class_item
                    if not class_item.startswith("_") and not inspect.isclass(all_class_items[class_item])\
                       and class_item != "basic_search_list" and class_item != "special_search_list"\
                       and class_item != "object_dependencies" and class_item != "objects":
                            class_items[class_item] = all_class_items[class_item]

                # print class_object.__name__ + " " + str(class_items)