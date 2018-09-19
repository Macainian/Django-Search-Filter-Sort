var can_do_enter_button_form_submissions = true;  // Used to override base.js in website
var search_bys = [];
var filter_bys = {};
var original_filter_bys = {};
var range_filters = {};
var sort_bys = [];
var paginate_by = [];
var page_number = 1;

// default_pagination comes in via django and must be set before including this file
function initialize_search_filter_sort() {
    paginate_by = [default_pagination];

    var page_number_text = $("#page_number_text");
    var select_all_pages_checkbox = $("#select_all_pages_checkbox");
    var object_list_checkbox = $(".object-list-checkbox");
    var delete_btn = $("#sfs_del_btn");
    var select_all_on_page = $("#select_all_objects_checkbox");

    $("#paginate_by_select").change(function() {
        paginate_by = [$(this).val()];
        goto_new_url(true, true, true);
    });

    if(page_number_text.val()) {
        page_num_input_form_size(page_number_text)
    }

    page_num_input_form_size(page_number_text);

    page_number_text.on('input', function() {
        page_num_input_form_size(page_number_text);
    });

    $(window).keydown(function(e) {
        if(e.key === 13 && $("#search_text").is(":focus")) {
            search();
        }

        if(e.key === 13 && page_number_text.is(":focus")) {
            goto_page(page_number_text.val());
        }
    });

    select_all_pages_checkbox.change(function() {
        var disable_state = $(this).prop("checked");

        $("#select_all_objects_checkbox").attr("disabled", disable_state);

        object_list_checkbox.each(function() {
            $(this).prop('checked', false);
            $(this).attr("disabled", disable_state);
        });
    });

    set_filter_mousedown_functions();
    set_filter_keydown_functions();
    get_url_parameters(search_bys, "search_by");
    get_filter_by_parameters();  // Also sets original_filter_bys
    get_url_parameters(sort_bys, "sort_by");
    get_url_parameters(paginate_by, "paginate_by");
    set_filters();
    set_sort_symbols();
    set_pagination();
    fix_range_filters();

    if(search_bys.length > 0) {
        $("#clear_search_button").prop("disabled", false);
    }

    set_filter_button_states();

    if(sort_bys.length > 0) {
        $("#clear_sorts_button").prop("disabled", false);
    }

    if(delete_btn.length){
        select_all_on_page.change(function() {
            if(object_list_checkbox.length > 0) {
                delete_btn.attr("disabled", !this.checked);
            }
        });

        select_all_pages_checkbox.change(function() {
            if(object_list_checkbox.length > 0) {
                delete_btn.attr("disabled", !this.checked);
            }
        });

        object_list_checkbox.change(function() {
            if(select_all_on_page.is(":not(:checked)")) {
                if(!$("table").find($(".object-list-checkbox:checked")).length > 0) {
                    delete_btn.attr("disabled", "disabled");
                } else {
                    delete_btn.removeAttr("disabled");
                }
            }
        });
    }
}

// Page number input form size
function page_num_input_form_size(page_number_text) {
    if(page_number_text.val()) {
        var page_number_text_size = page_number_text.val().length * 10 + 25;
        var page_number_width = page_number_text_size + "px";

        page_number_text.css({width: page_number_width, "max-width": "125px"});
    }
}

function set_filter_mousedown_functions() {
    var split_filters;
    var filter_name;
    var filter_quantity_span;
    var select = null;

    // Fixes selection bugs when you click on the slider or empty space.
    $("select.multi-select.sfs-filter").mousedown(function(e) {
        e.preventDefault();
        select = this;
        $(select).focus();
        // This is necessary to fix "click and drag scrolling on the options" bug in Chrome
    }).mousemove(function(e) {e.preventDefault();});

    var options = $("select.multi-select.sfs-filter option");

    options.click(function() {
        var scroll = select.scrollTop;
        filter_name = $(this).parent().attr("name").split("_filter")[0];
        filter_quantity_span = $("#" + filter_name + "_quantity_span");

        if($(this).prop("selected")) {
            $(this).prop("selected", false);
            split_filters = filter_bys[filter_name].split(",");
            split_filters.splice(split_filters.indexOf($(this).val()), 1);

            filter_bys[filter_name] = split_filters.join(",");

            if(filter_bys[filter_name].length === 0) {
                filter_quantity_span.text("");
                delete filter_bys[filter_name];
            } else {
                filter_quantity_span.text("(" + filter_bys[filter_name].split(",").length + ")");
            }
        } else {
            $(this).prop("selected", true);

            if(!filter_bys[filter_name]) {
                filter_bys[filter_name] = $(this).val();
            } else {
                filter_bys[filter_name] += "," + $(this).val();
            }

            filter_quantity_span.text("(" + filter_bys[filter_name].split(",").length + ")");
        }

        // This is necessary to fix "click and drag scrolling on the options" bug in Chrome
        setTimeout(function() {select.scrollTop = scroll;}, 0);

        set_filter_button_states();

        return false;
    });
}

function set_filter_keydown_functions() {
    var input_length;
    var filter_name;

    $("input.range-filter").on("input", function() {
        input_length = $(this).val().length;
        filter_name = $(this).attr("name").split("-filter")[0];

        if(input_length > 0) { // If not in the list already and there is input
            range_filters[filter_name] = $(this).val();  // Add/Update it in the list
        } else if(range_filters[filter_name] && input_length === 0) {
            delete range_filters[filter_name];
        }

        set_filter_button_states();
    });
}

function get_url_parameters(array, string) {
    var parameters = decodeURIComponent(window.location.href).split("?");
    var KEY = 0;
    var VALUE = 1;
    var i;
    var parameter;

    if(parameters.length === 2) { // Url has parameters
        parameters = parameters[1].split("&");
    } else {
        return;
    }

    for (i = 0; i < parameters.length; i++) {
        parameter = parameters[i].split("=");

        if(parameter[KEY] === string) {
            array.push(parameter[VALUE]);
        }
    }
}

function get_filter_by_parameters() {
    var parameters = decodeURIComponent(window.location.href).split("?");
    var KEY = 0;
    var VALUE = 1;
    var i;
    var filter_names = [];
    var filter_values = [];
    var parameter;
    var filter_name;

    if(parameters.length === 2) { // Url has parameters
        parameters = parameters[1].split("&");
    } else {
        return;
    }

    for (i = 0; i < parameters.length; i++) {
        parameter = parameters[i].split("=");

        if(parameter[KEY] === "filter_name") {
            filter_names.push(parameter[VALUE]);
        }
    }

    for (i = 0; i < parameters.length; i++) {
        parameter = parameters[i].split("=");

        if(parameter[KEY] === "filter_value") {
            filter_values.push(parameter[VALUE]);
        }
    }

    for (i = 0; i < filter_names.length; i++) {
        filter_bys[filter_names[i]] = filter_values[i];
    }

    original_filter_bys = $.extend(true, {}, filter_bys);
}

function set_filters() {
    var i;
    var filter_name;
    var filter_quantity_span;
    var hidden_filters = $.extend({}, filter_bys);  // Initialize with all the filters that were sent, then remove them as we go. Then we will be left with the hidden ones.

    // This needs to be added to all browse views at some point
    // console.log(filter_names);  // This is intentionally here to raise an error if it is not defined.

    if(typeof filter_names !== typeof undefined) { // If there are actually filters for this page even if they are not used
        for (i = 0; i < filter_names.length; i++) { // Go through all of them and see if any are being used

            filter_name = filter_names[i];
            filter_quantity_span = $("#" + filter_name + "_quantity_span");

            if(filter_bys[filter_name]) { // If this filter is being used
                $("#" + filter_name + "_filter").val(filter_bys[filter_name].split(","));
                filter_quantity_span.text("(" + filter_bys[filter_name].split(",").length + ")");
                delete hidden_filters[filter_name];
            }
        }
    }

    if(Object.keys(hidden_filters).length > 0) {
        $("#hidden_filters_message_div").css("display", "");
    }
}

function set_sort_symbols() {
    var i;
    var sort_by_split;
    var sort_text;

    for (i = 0; i < sort_bys.length; i++) {
        sort_by_split = sort_bys[i].split("-");

        if(sort_by_split.length === 2) { // Is using -
            change_sorting_symbol(sort_by_split[1], "sorting-desc");
            sort_text = $("#" + sort_by_split[1] + "_number");
        } else {
            change_sorting_symbol(sort_bys[i], "sorting-asc");
            sort_text = $("#" + sort_bys[i] + "_number");
        }

        sort_text.text(i+1);
        sort_text.show();
    }
}

function set_pagination() {
    $("#paginate_by_select").val(paginate_by[paginate_by.length - 1]);
}

function fix_range_filters() {
    var filter_name;

    // Need to remove the range filters to prevent duplicates later, but it has to be after original_filter_bys has
    // been set so that we can still clear filters and apply blank filters (aka clear) even after removing the range
    $("input.range-filter").each(function() {
        filter_name = $(this).attr("name").split("-filter")[0];

        if(typeof filter_bys[filter_name] !== typeof undefined) {
            range_filters[filter_name] = filter_bys[filter_name];
            delete filter_bys[filter_name];
        }
    });
}

function add_sort_by(sort_by) {
    var index = sort_bys.indexOf(sort_by);
    var sort_text = $("#" + sort_by + "_number");

    sort_text.hide();

    if(index === -1) { // If index is -1, it might still be in the list with a -
        index = sort_bys.indexOf("-" + sort_by);
    }

    if(index === -1) { // Not yet in the list, so tack it on the end
        sort_bys.push(sort_by);
        change_sorting_symbol(sort_by, "sorting-asc");
    } else if(index === sort_bys.length - 1) { // If it is currently at the end
        if(sort_bys[index].split("-").length === 2) { // Is using -

            sort_bys.splice(index, 1);
            change_sorting_symbol(sort_by, "sorting-none");
            sort_text.hide();
        } else {
            sort_bys[index] = "-" + sort_by;
            change_sorting_symbol(sort_by, "sorting-desc");
        }
    } else { // In the list, but not at the end. Move it to the end in ascending order
        sort_bys.splice(index, 1);
        //sort_bys.push(sort_by);
        change_sorting_symbol(sort_by, "sorting-none");
    }

    goto_new_url(true, true, true);
}

function goto_new_url(should_include_searches, should_include_filters, should_include_sorts) {
    var i;
    var filter;
    var url_suffix = "?";

    add_spinner();

    if(paginate_by[paginate_by.length - 1] !== default_pagination) {
        url_suffix += "paginate_by=" + paginate_by[paginate_by.length - 1] + "&";
    }

    if(page_number !== 1) {
        url_suffix += "page=" + page_number + "&";
    }

    if(should_include_searches) {
        for (i = 0; i < search_bys.length; i++)
        {
            url_suffix += "search_by=" + search_bys[i] + "&";
        }
    }

    if(should_include_filters) {
        for (filter in filter_bys) {
            url_suffix += "filter_name=" + filter + "&filter_value=" + filter_bys[filter] + "&";
        }

        for (filter in range_filters) {
            url_suffix += "filter_name=" + filter + "&filter_value=" + range_filters[filter] + "&";
        }
    }

    if(should_include_sorts) {
        for (i = 0; i < sort_bys.length; i++) {
            url_suffix += "sort_by=" + sort_bys[i] + "&";
        }
    }

    if(url_suffix === "?") { // There was nothing added, so just leave it blank.
        url_suffix = "";
    } else if(url_suffix.charAt(url_suffix.length - 1) === "&") { // If the last character is an &
        url_suffix = url_suffix.slice(0, -1);  // Get rid of the extra &
    }

    window.location.href = window.location.href.split("?")[0] + url_suffix;
}

function change_sorting_symbol(base_id, new_class) {
    var sort_to_set = $("#" + base_id + "_header").find(".sort-controls");

    sort_to_set.removeClass("sorting-none");
    sort_to_set.removeClass("sorting-asc");
    sort_to_set.removeClass("sorting-desc");

    sort_to_set.addClass(new_class);
}

function set_filter_button_states() {
    var clear_filters_button = $("#clear_filters_button");
    var apply_filters_button = $("#apply_filters_button");

    // If there weren't any filters coming onto the page and if there aren't any new ones and if there aren't any range_filters
    if(Object.keys(original_filter_bys).length === 0 && Object.keys(filter_bys).length === 0 && Object.keys(range_filters).length === 0) {
        // Disable the clear and apply buttons
        clear_filters_button.prop("disabled", true);
        apply_filters_button.prop("disabled", true);
    } else {
        // Enable the clear and apply buttons
        clear_filters_button.prop("disabled", false);
        apply_filters_button.prop("disabled", false);

        $("#collapse_one").collapse("show");
    }
}

function goto_page(new_page_number) {
    // If int
    if(!isNaN(new_page_number)) {
        if(Math.floor(+new_page_number) === +new_page_number && $.isNumeric(+new_page_number)) {
            page_number = new_page_number;

            goto_new_url(true, true, true);
        }
    }
}

function clear_search() {
    goto_new_url(false, true, true);
}

function clear_filters() {
    goto_new_url(true, false, true);
}

function clear_sorts() {
    goto_new_url(true, true, false);
}

function clear_all() {
    window.location.href = window.location.href.split("?")[0];
}

function search() {
    var search_text = $("#search_text");

    if(search_text.val() !== "") {
        search_bys = [search_text.val()];
    } else {
        search_bys = [];
    }

    goto_new_url(true, true, true);
}

function apply_filters() {
    goto_new_url(true, true, true);
}

function toggle_select_all_objects() {
    var object_list_checkboxes = $(".object-list-checkbox");

    if($("#select_all_objects_checkbox").is(":checked")) { // Turn everything on
        object_list_checkboxes.each(function() {
            $(this).prop("checked", true);
        });
    } else { // Turn everything off
        object_list_checkboxes.each(function() {
            $(this).prop("checked", false);
        });
    }
}

function get_new_url_via_checkboxes(base_url) {
    var object_list_checkboxes = $(".object-list-checkbox");
    var url = base_url + "?";
    var query_string;
    var at_least_one_box_is_checked = false;
    var all_pages_checkbox_is_checked = $("#select_all_pages_checkbox").is(":checked");

    if(all_pages_checkbox_is_checked) {
        query_string = decodeURIComponent(window.location.href).split("?");

        if(query_string.length === 2) { // Url has parameters
            url += query_string[1];
        }

        return url;
    } else {
        // Check if everything is either on or everything is off
        object_list_checkboxes.each(function() {
            if(at_least_one_box_is_checked) {
                return;
            }

            if($(this).is(":checked")) {
                at_least_one_box_is_checked = true;
            }
        });
    }

    if(at_least_one_box_is_checked) {
        url += "filter_name=id&filter_value=";
    } else {
        query_string = decodeURIComponent(window.location.href).split("?");

        if(query_string.length === 2) { // Url has parameters
            url += query_string[1] + "&";
        }

        url += "__RETURN_EMPTY__=1";

        return url;
    }

    // This section is only used if "All Pages" isn't checked
    object_list_checkboxes.each(function() {
        if($(this).is(":checked") === true) {
            url += $(this).val() + ",";
        }
    });

    if(url.charAt(url.length - 1) === ",") { // If the last character is a ,
        url = url.slice(0, -1);  // Get rid of the extra ,
    }

    return url;
}

function goto_new_url_via_checkboxes(base_url) {
    window.location.href = get_new_url_via_checkboxes(base_url);
}