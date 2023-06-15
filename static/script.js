"use strict"

///////////////////// retrieval functions \\\\\\\\\\\\\\\\\\\\\

function getAndDisplayArticlesForTerm(params, termNumber) {
    // Retrieve and display the news articles and results (the num of articles, num of term occurrences across pages, and the actual articles).
    // Function uses the specified parameters for the search, and displays the result in the specified termNumber result (1 or 2)'s div.
    // Return a Promise with the number of articles for the search so that we can retrieve the value.
    return new Promise(function (resolve, reject) {
        let resultArticlesDiv = $('#result_' + termNumber + '_articles');
        let resultNumArticlesDiv = $('#result_' + termNumber + '_num_articles');
        let resultArticlesHeaderDiv = $('#result_' + termNumber + '_articles_header')
        let resultErrorsDiv = $('#result_' + termNumber + '_errors');

        resultArticlesDiv.html('Loading...');

        // Get the news articles.
        $.get('/internal/get-articles', params).done(function (data) {
            let response = JSON.parse(data);
            if (response.succeeded) {
                let numberArticles = response.results.values['num_articles'];
                let articles = response.results.values['articles'];

                // return the number of articles if succeeded
                resolve(numberArticles);

                resultArticlesDiv.html('');
                resultNumArticlesDiv.html('<h1>' + params['q'] + '</h1><h2>Articles: ' + numberArticles + '</h2>');
                resultArticlesHeaderDiv.html('<h4>Latest Articles:</h4>');

                for (let article of articles) {
                    let link = $('<a>');
                    link.attr('href', article.url);
                    link.html(article.source.name + ': ' + article.title);
                    resultArticlesDiv.append(link);
                    resultArticlesDiv.append('<br>');
                }
            } else {
                resultArticlesDiv.html('');
                resultErrorsDiv.html('Error loading result. Please try again later.');
                console.log('/internal/get-articles request failed:\n' + response.errors.error_source + ' error retrieving articles.\nMessage: ' + response.errors.message)
                reject(new Error('failed to retrieve number of articles'));  // if failed then reject
            }
        }).fail(function (data) {
            resultArticlesDiv.html('');
            resultErrorsDiv.html('Error loading result. Please try again later.');
            console.log('/internal/get-articles request failed:\n' + data.responseText);
            reject(new Error('failed to retrieve number of articles'));  // if failed then reject
        })
    })
}

function getAndDisplayNumOccurencesForTerm(params, termNumber) {
    // After getting and display all articles, display how many times the term occurs across all pages.
    // This can be a VERY expensive operation because it makes an individual request to every single article url,
    // but this runs asynchronously so the result will load when we get it back. This way, the articles
    // that were just found above will display while this result is calculating
    let resultNumOccurrencesDiv = $('#result_' + termNumber + '_num_occurrences');
    resultNumOccurrencesDiv.html('Loading...');
    $.get('/internal/get-num-term-occurrences', params).done(function (data) {
        let response = JSON.parse(data);
        let numOccurrences = response.results.values.num_occurrences;
        let numArticles = response.results.values.num_articles;
        resultNumOccurrencesDiv.html('<b>' + numOccurrences + '</b> matches found across all ' + numArticles + ' articles.');
    }).fail(function (data) {
        resultNumOccurrencesDiv.html('Error loading the number of occurrences. Please try again later.');
        console.log('/internal/get-num-term-occurrences request failed:\n' + data.responseText);
    })
}

function clearTermResults(resultNum) {
    $('#result_' + resultNum + '_num_articles').html('');
    $('#result_' + resultNum + '_num_occurrences').html('');
    $('#result_' + resultNum + '_articles_header').html('');
    $('#result_' + resultNum + '_articles').html('');
    $('#result_' + resultNum + '_errors').html('');
    $('#result_comparison').html('');
}

////////////////////// page setup functions \\\\\\\\\\\\\\\\\\\\\\\\

function createDropdown(selectId, optionsDict, defaultOption) {
    $.each(optionsDict, function (value, html) {
        let option = document.createElement('option');
        option.value = value;
        option.innerHTML = html;
        if (value === defaultOption) {
            option.selected = true;
        }
        $('#' + selectId).append(option);
    })
}

function validateDates() {
    // Called when a date is changed. Makes sure the dateFrom date cannot be greater than the dateTo date and vice versa.
    let dateFrom = $('#date_from');
    let dateTo = $('#date_to');
    dateFrom.attr('max', dateTo.val());
    dateTo.attr('min', dateFrom.val());
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
    let selectAllBox = $('#search_in_select_all')[0];
    let allOtherBoxesAreChecked = true;
    let checkboxes = $("input[name='search_in']");
    for (let i = 0, n = checkboxes.length; i < n; i++) {
        if (!checkboxes[i].checked) {
            allOtherBoxesAreChecked = false;
            break;
        }
    }
    if (allOtherBoxesAreChecked && !selectAllBox.checked) {
        selectAllBox.checked = true;
    } else if (!allOtherBoxesAreChecked && selectAllBox.checked) {
        selectAllBox.checked = false;
    }
}

function getISOStringWithLocalOffset(date) {
    // Return the given date as an ISO string, with the SAME time, but with the local offset.
    let timeZoneOffset = -date.getTimezoneOffset(),
        diff = timeZoneOffset >= 0 ? '+' : '-',
        pad = function (num) {
            return (num < 10 ? '0' : '') + num;
        };
    let offset_str = diff + pad(Math.floor(Math.abs(timeZoneOffset) / 60)) +
        ':' + pad(Math.abs(timeZoneOffset) % 60);
    return date.toISOString().replace('Z', offset_str);
}

function getLocalDateTime() {
    // Return the local time as a date object
    let utcToday = new Date();
    let localTimeOffset = utcToday.getTimezoneOffset() * 60 * 1000;
    return new Date(utcToday - localTimeOffset);
}


