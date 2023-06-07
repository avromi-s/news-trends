"use strict"

///////////////////// retrieval functions \\\\\\\\\\\\\\\\\\\\\

function getAndDisplayArticlesForTerm(params, term_number) {
    // Retrieve and display the news articles and results (the num of articles, num of term occurrences across pages, and the actual articles).
    // Function uses the specified parameters for the search, and displays the result in the specified term_number result (1 or 2)'s div.
    // Return a Promise with the number of articles for the search so that we can retrieve the value.
    return new Promise(function (resolve, reject) {
        let result_articles_div = $('#result_' + term_number + '_articles');
        let result_num_articles_div = $('#result_' + term_number + '_num_articles');
        let result_articles_header_div = $('#result_' + term_number + '_articles_header')
        let result_num_occurrences_div = $('#result_' + term_number + '_num_occurrences');
        let result_errors_div = $('#result_' + term_number + '_errors');

        result_articles_div.html('Loading...');

        // Get the news articles.
        $.get('/internal/get-articles', params).done(function (data) {
            let response = JSON.parse(data);
            if (response.succeeded) {
                let number_articles = response.results.values['num_articles'];
                let articles = response.results.values['articles'];

                // return the number of articles if succeeded
                resolve(number_articles);

                result_articles_div.html('');
                result_num_articles_div.html('<h1>' + params['q'] + '</h1><h2>Number of articles found: ' + number_articles + '</h2>');
                result_articles_header_div.html('<h4>Latest Articles from Search:</h4>');

                for (let article of articles) {
                    let link = $('<a>');
                    link.attr('href', article.url);
                    link.html(article.source.name + ': ' + article.title);
                    result_articles_div.append(link);
                    result_articles_div.append('<br>');
                }

                // After getting and display all articles, display how many times the term occurs across all pages.
                // This can be a VERY expensive operation because it makes an individual request to every single article url,
                // but this runs asynchronously so the result will load when we get it back. This way, the articles
                // that were just found above will display while this result is calculating
                result_num_occurrences_div.html('Loading the number of occurrences...');
                $.get('/internal/get-num-term-occurrences', params).done(function (data) {
                    let response = JSON.parse(data);
                    let num_occurrences = response.results.values.num_occurrences;
                    result_num_occurrences_div.html('<b>' + num_occurrences + '</b> matches found across all ' + number_articles + ' articles.');
                }).fail(function (data) {
                    result_num_occurrences_div.html('Error loading the number of occurrences. Please try again later.');
                    console.log('/internal/get-num-term-occurrences request failed:\n' + data.responseText);
                })
            } else {
                result_articles_div.html('');
                result_errors_div.html('Error loading result. Please try again later.');
                console.log('/internal/get-articles request failed:\n' + response.errors.error_source + ' error retrieving articles.\nMessage: ' + response.errors.message)
                reject(new Error('failed to retrieve number of articles'));  // if failed then reject
            }
        }).fail(function (data) {
            result_articles_div.html('');
            result_errors_div.html('Error loading result. Please try again later.');
            console.log('/internal/get-articles request failed:\n' + data.responseText);
            reject(new Error('failed to retrieve number of articles'));  // if failed then reject
        })
    })
}

////////////////////// page setup functions \\\\\\\\\\\\\\\\\\\\\\\\

function createDropdown(select_id, options_dict, default_option) {
    $.each(options_dict, function (value, html) {
        let option = document.createElement('option');
        option.value = value;
        option.innerHTML = html;
        if (value === default_option) {
            option.selected = true;
        }
        $('#' + select_id).append(option);
    })
}

function validateDates() {
    // Called when a date is changed. Makes sure the date_from date cannot be greater than the date_to date and vice versa.
    let date_from = $('#date_from');
    let date_to = $('#date_to');
    date_from.attr('max', date_to.val());
    date_to.attr('min', date_from.val());
}

///////////////////// utility functions \\\\\\\\\\\\\\\\\\\\\

function toggle_select_all_checkbox(source) {
    // Called when the 'select all' checkbox is selected. Will check or uncheck all the boxes in the group to match the select all checkbox.
    let checkboxes = $("input[name='search_in']");
    for (let i = 0, n = checkboxes.length; i < n; i++) {
        checkboxes[i].checked = source.checked;
    }
}

function toggle_checkbox() {
    // Called when any of the checkboxes except the 'select all' box is selected. Will update the select all checkbox in case all checkboxes
    // are now checked and the all box is not checked, or vice versa.
    let select_all_box = $('#search_in_select_all')[0];
    let all_other_boxes_are_checked = true;
    let checkboxes = $("input[name='search_in']");
    for (let i = 0, n = checkboxes.length; i < n; i++) {
        if (!checkboxes[i].checked) {
            all_other_boxes_are_checked = false;
            break;
        }
    }
    if (all_other_boxes_are_checked && !select_all_box.checked) {
        select_all_box.checked = true;
    } else if (!all_other_boxes_are_checked && select_all_box.checked) {
        select_all_box.checked = false;
    }
}

function getISOStringWithLocalOffset(date) {
    // Return the given date as an ISO string, with the SAME time, but with the local offset.
    let time_zone_offset = -date.getTimezoneOffset(),
        diff = time_zone_offset >= 0 ? '+' : '-',
        pad = function (num) {
            return (num < 10 ? '0' : '') + num;
        };
    let offset_str = diff + pad(Math.floor(Math.abs(time_zone_offset) / 60)) +
        ':' + pad(Math.abs(time_zone_offset) % 60);
    return date.toISOString().replace('Z', offset_str);
}

function getLocalDateTime() {
    // Return the local time as a date object
    let utcToday = new Date();
    let localTimeOffset = utcToday.getTimezoneOffset() * 60 * 1000;
    return new Date(utcToday - localTimeOffset);
}


