// EchoLeaf Version 1.5c
// EchoLeaf Version 1.4a
// EchoLeaf Version 1.5a
// FrameColRight 
//

var menuItems = ['System', 'LTFSLE', 'VirtualDrive', 'Logout', 'Login'];
var credentialed = false;
var adminName = "";
var adminPassword = "";
var rtnVal;
var dashboardRefresh;

// Added to fileSearchByDate functions -- Possibly will use at other places.


// site.js

$(document).ready(function() {

    // Define hideAllSections as a global function.
    window.hideAllSections = function() {
        console.log("hideAllSections called!"); // Keep for debugging
        $(".container.body-content > div").hide();
        console.log("hideAllSections finished.");
    };

    // Define showSection as a global function
    window.showSection = function (sectionId) {
      console.log("showSection called!"); // Keep for debugging
        hideAllSections(); // Hide all sections first
        $("#section" + sectionId).show(); // Then show the specified section
        console.log("showSection finished."); // Keep for debugging

    }

    // ... any other existing code in site.js ...
});







// For displayDashboard()
let fmCheckJsonInterval;

// displays login screen
function displayLogin() {
    credentialed = false;
    $('#adminName').val("");
    $('#adminPassword').val("");
    $('#login_error').html("");
    toggleMenubar();
    makeMenuActive('Login');
    showSection('Login')
}


function dbTapeMove() {
    this.fileList = [];
    this.lastFolder = new Object();
}

dbTapeMove.prototype.missingTapeTable = function () {
    var tableCol = 3;
    $('#modalHeader').html('<h4 class="modal-title">Tapes Not In Library</h4>');
    var strTable = [];
    var tapes = this.lastFolder["outlib"];
    var tapeAdd = tableCol - (tapes.length % tableCol);
    if (tapeAdd < tableCol)
        for (var i = 0; i < tapeAdd; i++)
            tapes.push("&nbsp;");
    strTable.push('<table class="table table-striped table-hover"><tbody>');
    for (var i = 0; i < tapes.length; i += tableCol) {
        strTable.push('<tr>');
        for (var j = 0; j < tableCol; j++)
            strTable.push('<td>' + tapes[i + j] + '</td>');
        strTable.push('</tr>');
    }
    strTable.push('<tbody></table>');
    $('#modalBody').html(strTable.join(""));
    $('#modalFooter').html('<button type="button" class="btn btn-default" data-dismiss="modal" onclick="moveList.clearFolder();">Cancel</button><button type="button" class="btn btn-primary"  data-dismiss="modal" onclick="setFolderRestoreLocation();">Continue</button>');
    $('#myModal').modal({ backdrop: "static" });
}



dbTapeMove.prototype.clearFolder = function (folder) {
    this.lastFolder = new Object();
}


dbTapeMove.prototype.setRestorLocation = function (row, item) {
    this.fileList[item][4] = $("#file" + row).prop("selectedIndex");
}

dbTapeMove.prototype.clear = function () {
    while (this.fileList.length) {
        this.fileList.pop();
    }
    this.createTable();
}

dbTapeMove.prototype.addFolder = function (location) {
    var found = false;
    var files = this.lastFolder['files'].length;
    for (var j = 0; j < files; j++) {
        if (this.lastFolder['files'][j][0] > -1) {
            fullName = this.lastFolder['dirName'][this.lastFolder['files'][j][4]] + '/' + this.lastFolder['files'][j][1];
            this.fileList.push([this.lastFolder['files'][j][0], fullName, this.lastFolder['files'][j][2], this.lastFolder['files'][j][3], location]);
            found = true;
        }
    }
    this.lastFolder = new Object();
    if (found)
        this.createTable();
}

dbTapeMove.prototype.newFolder = function (folder) {
    var validFiles = 0;
    var rows = this.fileList.length;
    var files = folder['files'].length;
    for (var j = 0; j < files; j++) {
        for (var i = 0; i < rows; i++)
            if (this.fileList[i][0] == folder['files'][j][0]) {
                folder['files'][j][0] = -1;
                break;
            }
        if (folder['files'][j][0] != -1)
            validFiles++;
    }
    if (validFiles > 0)
        this.lastFolder = folder;
    return validFiles;
}


dbTapeMove.prototype.add = function (fileInfo) {
    var notListed = true;
    var rows = this.fileList.length;
    for (var i = 0; i < rows; i++)
        if (this.fileList[i][0] == fileInfo[0]) {
            notListed = false;
            break;
        }
    if (notListed) {
        this.fileList.push(fileInfo);
        this.createTable();
    }
}
dbTapeMove.prototype.delete = function (row) {
    this.fileList.splice(row, 1);
    this.createTable();
}

dbTapeMove.prototype.createTable = function () {
    $('#SimpleTask').html('&nbsp;');
    var strTable = [];
    var header = ['Line #', 'File/Folder', 'Cartridge', 'In Library', 'Copy Location', '&nbsp'];
    var libraryStatus = ['no', 'yes'];
    var moveCount = 0;  // This will be used for both the select ID *and* the line number
    var passedInfo;
    var selected = [];
    strTable.push('<form id="files_move"  name="files_move">'); // Removed onsubmit
    strTable.push('<table class="table table-striped table-hover"><thead><tr>');
    for (var i = 0; i < header.length; i++)
        strTable.push('<th>' + header[i] + '</th>');
    strTable.push('</tr></thead><tbody>');
    var cols = this.fileList.length;
    for (var i = 0; i < cols; i++) {
        strTable.push('<tr>');
        strTable.push('<td>' + (moveCount + 1) + '</td>'); // Add line number, starting at 1
        strTable.push('<td>' + this.fileList[i][1] + '</td><td>' + this.fileList[i][2] + '</td><td>' + libraryStatus[this.fileList[i][3]] + '</td><td>');
        if (this.fileList[i][3] == 1) {
            passedInfo = this.fileList[i][0] + '|' + this.fileList[i][1] + '|' + this.fileList[i][2] + '|'; // fileID|fullPath|tapeUID|
            selected = [' ', ' '],
            selected[this.fileList[i][4]] = ' selected '
            strTable.push('<select id="file' + moveCount + '" name="file' + moveCount + '" onchange="frl(' + moveCount + ',' + i + ')"><option' + selected[0] + 'value="' + passedInfo + 'RestoreAlternate">Quarantine</option><option' + selected[1] + ' value="' + passedInfo + 'VDiskMountPoint">Cache</option></select>'); //CHANGED TEXT HERE
            moveCount++;
        }
        else
            strTable.push('&nbsp;');
        strTable.push('</td><td><a href="#" onclick="moveList.delete(' + i + ')">remove</a></td></tr>');
    }
    strTable.push('</tbody></table>');
    if (moveCount > 0) {
        strTable.push(hiddenObjectValue('rows', moveCount));
        strTable.push(addCredentials());
        strTable.push('<div id="dbTreeAction">');
		strTable.push('<button type="button" class="btn btn-primary" onclick="submitRestore(\'files_move\');">Submit</button>'); // Changed onclick
        strTable.push('</div');
    }
    strTable.push('</form>');
    $('#move_list').html(strTable.join(""));
}


function frl(row, item) {
    moveList.setRestorLocation(row, item)
}


var moveList = new dbTapeMove();


function showSection(currentSection, callback) {
    clearTimeout(dashboardRefresh);
    $.each(['Intro', 'Login', 'Dashboard', "VirtualDriveStartStop", "SimpleTask", "DBTree"], function (index, value) {
        if (value !== currentSection && $('#section' + value).is(':visible')) {
            $('#section' + value).hide(); // Hide other sections immediately
        }
    });

    // Use a callback with show() to ensure it's fully shown
    $('#section' + currentSection).show(0, function() { // 0ms for no animation, but still triggers the callback
        if (callback) {
            setTimeout(callback, 5000); // Delay the callback by 500 milliseconds
        }
    });
}



// show active menu based on section displayed
function makeMenuActive(currentMenu)
{
    $.each(menuItems, function (index, value) {
        if ($('#menu' + value).hasClass('active' ))
            $('#menu' + value).removeClass('active');
    });   
    if (currentMenu != '')
        $('#menu' + currentMenu).addClass('active');
}

// toggle menubar
function toggleMenubar() {
    var menuLength = menuItems.length - 1;
    $.each(menuItems, function (index, value) {
        if ($('#menu' + value).is(':visible'))
            $('#menu' + value).hide();
    });
    if (!credentialed) 
        $('#menuLogin').show();
    else
        for (var i=0; i < menuLength; i++)
            $('#menu' + menuItems[i]).show();
}


// display intro screen
function displayIntro() {
    credentialed = false;
    toggleMenubar();
    showSection('Intro')
    makeMenuActive('');
}


// update dashboard -- adds File Manager Timer fields

// In site.js
// let fmCheckJsonInterval; // Declare outside to have broader scope / declared at top of script

async function updateDashboard() {
    console.log("updateDashboard() called");

    // Initialize display and variables
    $('#fmCycleInterval').text("File Manager Not Active");
    $('#fmCountdownTimer').text("");

    let fmTimerOn = 0; // 0 = fmdat.json doesn't exist, 1 = fmdat.json exists
    let fmStack = 0;   // 0 = stack not running, 1 = stack running
    let pauseIntValue = ""; // Store the last known pauseInterval
    let processStatusInterval = null; // Interval for cycling log messages
    let refreshLogDataInterval = null; // Interval for refreshing log data
    let initialDelay = false; // Flag for initial 5-second delay
    let initialDelayTimeout = null; // Timeout for initial delay

    // Ensure the File Manager timer table and rows exist
    if ($('#fm-timer-table').length === 0) {
        console.log("Creating fm-timer-table");
        $('#dashboard_active').append('<table class="table" id="fm-timer-table"></table>');
    }

    if ($('#fmCycleInterval').length === 0) {
        console.log("Appending timer rows to fm-timer-table");
        $('#fm-timer-table').append(`
            <tr>
                <td class="text-left">File Manager Cycle Interval:</td>
                <td id="fmCycleInterval" class="text-right"></td>
            </tr>
            <tr>
                <td class="text-left">File Manager Countdown:</td>
                <td id="fmCountdownTimer" class="text-right"></td>
            </tr>
            <tr>
                <td></td>
                <td class="text-right"><button id="runFileManagerButton" class="btn btn-success">Cycle File Manager Now</button></td>
            </tr>
            <tr>
                <td class="text-left">Process Status:</td>
            </tr>
            <tr>
                <td colspan="2" id="fmProcessStatus" class="text-center"></td>
            </tr>`  // fmProcessStatus moved and colspan set
        );
    }

    // Function to update the Process Status display by cycling through messages
    function updateProcessStatusDisplay(logMessages) {
        clearInterval(processStatusInterval); // Clear any previous interval

        let counter = 0;
        processStatusInterval = setInterval(() => {
            $('#fmProcessStatus').text(logMessages[counter]);
            counter = (counter + 1) % logMessages.length; // Cycle through messages
        }, 1000); // Changed to 1000 milliseconds (1 second)
    }

    // Function to fetch and process fmlog.json data
    async function getFmLogData() {
        console.log("getFmLogData called");

        clearInterval(processStatusInterval); // Stop cycling before getting new data
        clearTimeout(initialDelayTimeout); // Clear the initial delay timeout

        try {
            // Use fetch to call /process_logs (POST request)
            const processLogsResponse = await fetch('/process_logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!processLogsResponse.ok) {
                throw new Error(`HTTP error! status: ${processLogsResponse.status}`);
            }

            const processLogsData = await processLogsResponse.json();

            // Check for success based on return_message
            if (processLogsData.error === 0 && processLogsData.return_message === "success") {
                // Use fetch to get fmlog.json
                const fmlogResponse = await fetch('/views/fmlog.json');

                if (!fmlogResponse.ok) {
                    throw new Error(`HTTP error! status: ${fmlogResponse.status}`);
                }

                const fmlogData = await fmlogResponse.json();
                console.log("getFmLogData: fmlog.json data:", fmlogData);

                if (Array.isArray(fmlogData)) {
                    const logMessages = fmlogData.map(entry => entry.message).reverse().slice(0, 20);
                    updateProcessStatusDisplay(logMessages);
                } else {
                    $('#fmProcessStatus').text("Error: Invalid fmlog.json format");
                }
            } else {
                // Handle specific error messages based on return_message
                console.error("getFmLogData: Error processing logs:", processLogsData.msg);
                switch (processLogsData.return_message) {
                    case "log_file_not_found":
                        $('#fmProcessStatus').text("Error: Log file not found.");
                        break;
                    case "error_reading_log":
                        $('#fmProcessStatus').text("Error: Could not read the log file.");
                        break;
                    case "error_parsing_log":
                        $('#fmProcessStatus').text("Error: Could not parse log entries.");
                        break;
                    case "error_writing_json":
                        $('#fmProcessStatus').text("Error: Could not write to JSON file.");
                        break;
                    case "error_creating_json":
                        $('#fmProcessStatus').text("Error: Could not create JSON file.");
                        break;
                    default:
                        $('#fmProcessStatus').text("Error: An unexpected error occurred.");
                }
            }

        } catch (error) {
            console.error("getFmLogData: Fetch request failed:", error);
            $('#fmProcessStatus').text("Error: Could not load log data.");
        }
    }

    // Function to check and update the timer display based on fmdat.json
    async function checkFmdat() {
        console.log("checkFmdat called");
        try {
            const data = await $.getJSON("views/fmdat.json");
            console.log("checkFmdat: fmdat.json data:", data);

            fmTimerOn = 1;
            fmStack = 0;

            if (data && data.pauseInterval !== undefined) {
                $('#fmCycleInterval').text(data.pauseInterval);
                pauseIntValue = data.pauseInterval;
            }

            if (data && data.timer !== undefined) {
                $('#fmCountdownTimer').text(data.timer);
            }
            $('#runFileManagerButton').text("Cycle File Manager Now").removeClass('btn-danger').addClass('btn-success');
            $('#fmProcessStatus').text("Waiting for Timer To Finish");

            clearInterval(processStatusInterval); // Stop cycling messages
            clearInterval(refreshLogDataInterval);
            refreshLogDataInterval = null;
        } catch (error) {
            console.log("checkFmdat: fmdat.json not found or invalid");
            fmTimerOn = 0;
            fmStack = 1;
            $('#fmCycleInterval').text("File Manager Cycle Running");
            $('#fmCountdownTimer').text("Please Wait");
            $('#runFileManagerButton').text("Cycle File Manager Now").removeClass('btn-success').addClass('btn-danger');

            if (initialDelay) {
                clearTimeout(initialDelayTimeout);
                $('#fmProcessStatus').text("Accessing Log Data");
                initialDelayTimeout = setTimeout(() => {
                    initialDelay = false;
                    getFmLogData();
                }, 5000); // 5-second delay before first data fetch
            } else if (!refreshLogDataInterval) {
                getFmLogData(); // Fetch data immediately if not the first time
                refreshLogDataInterval = setInterval(getFmLogData, 10000);
            }
        }
    }


    // Function to check the status of filemanager.py using alive()
    async function checkFileManagerStatus() {
        console.log("checkFileManagerStatus() called");

        $.ajaxSetup({ cache: false });
        $.getJSON("alive", function (result) {
            if (result && result.filemanager && result.filemanager[0] === 1) {
                // filemanager.py is running
                console.log("filemanager.py is running");
                checkFmdat(); 
            } else {
                // filemanager.py is not running
                console.log("filemanager.py is NOT running");
                $('#fmCycleInterval').text("File Manager Is Not Running");
                $('#fmCountdownTimer').text("");
                $('#runFileManagerButton').text("Cycle File Manager Now").removeClass('btn-success').addClass('btn-danger');
                $('#fmProcessStatus').text("");
                fmTimerOn = 0; 
                fmStack = 0; 
            }
        }).fail(function() {
            console.error("Error checking alive status");
            // Handle error appropriately, maybe set default values or retry
        }).always(function() {
            $.ajaxSetup({ cache: true });
        });
    }

    // Set up the button handler
    $('#runFileManagerButton').off('click').on('click', async function () {
        if ($('#fmCycleInterval').text() === "File Manager Is Not Running") {
            $('#fmCountdownTimer').text("Please Run File Manager");
        } else if (fmStack === 1) {
            $('#fmCountdownTimer').text("Waiting for Cycle to Complete");
        } else if (fmStack === 0) {
            try {
                const response = await $.ajax({
                    url: '/runFileManager',
                    method: 'POST',
                    dataType: 'json'
                });

                console.log("File Manager request successful:", response);
                // You can add further handling based on the response if needed

            } catch (error) {
                console.error("Error requesting File Manager:", error);
                $('#fmCountdownTimer').text("Error cycling File Manager");
            }
        }
        initialDelay = true;
    });

    // Call checkFileManagerStatus initially to set the display
    checkFileManagerStatus();

    // Start the interval timer
    setInterval(checkFileManagerStatus, 5000);
}




// display dashboard

async function displayDashBoard() {
    console.log("displayDashboard() started");
    showSection('Dashboard');
    makeMenuActive('System');

    // Clear the simpleTaskLog before fetching new data
    $('#simpleTaskLog').html('');

    // Use await to ensure operations complete in the correct order
    await alive('dashboard_active');
    await storageStats();
    await updateDashboard();

    // Display the file move log table after other operations are complete
    await filemovelogtable(); // Now awaits the Promise from filemovelogtable()

    // Set up the refresh interval after all other operations are done
    dashboardRefresh = setTimeout(displayDashboard, 300000);
}






// validate login
function validateLogin(objForm)
{
    $.ajaxSetup({ cache: false });
    $.post("login", $("#login_form").serialize())
    .done(function (data) {
        if (data["error"] == 0) {
            credentialed = true;
            toggleMenubar(); 
            displayDashBoard();
        }
        else  {
            $('#login_error').html("Invalid login site credentials!");
            $('#adminPassword').val("");
        }
    }, "json")
    .fail(function () {
        $('#login_error').html("Error while validating login credentials!");
        $('#adminPassword').val("");
    });
    $.ajaxSetup({ cache: true });
    return false;
}

function logout() {
    credentialed = null;
    displayIntro();
}

// add class
function addClass(strObj, strClass) {
    target = $('#' + strObj);
    if (!target.hasClass(strClass))
        target.addClass(strClass);
}

// remove class
function deleteClass(strObj, strClass) {
    target = $('#' + strObj);
    if (target.hasClass(strClass))
        target.removeClass(strClass);
}


// build table 
function simpleTask(objTask) {
    var strHTML =[];
    var rowOneStart = '<div class="row"><div class="col-sm-12">';
    var rowOneStop = '</div></div>';
    strHTML.push(rowOneStart + '<h2>' + objTask['title'] + '</h2>' + rowOneStop);
    strHTML.push(rowOneStart + '<p>' + objTask['info'] + '</p><br>' + rowOneStop);
    strHTML.push('<div class="row"><div class="col-sm-' + objTask['width'] + '">');
    strHTML.push('<table class="table"><tbody>');
    for (var i = 0; i < objTask['rows'].length; i++)
        strHTML.push('<tr><td>' + objTask['rows'][i][0] + '</td><td id="' + objTask['rows'][i][1] + '">&nbsp;</td></tr>');
    strHTML.push('<tr><td colspan="2"><p class="text-danger" id="taskError"></p></td></tr></tbody></table>');
    strHTML.push('</div>');
    if (objTask['width'] < 12)
        strHTML.push('<div class="col-sm-' + (12 - objTask['width']) + '"></div>');
    strHTML.push('</div>');
    $('#section' + objTask['section']).html(strHTML.join(''));
    showSection(objTask['section']);
}


// please wait notice when a use action is taken


function pleaseWait() {
    return '<p class="text-info"><img src="static/images/spin.gif" />&nbsp;Please wait...</p>';
}

// create table from a table information object
function displayTable(info) {
    var strHTML = [];
    strHTML.push('<h2>' + info['title'] + '</h2>');
    if (info['explain'] != '')
        strHTML.push('<p>' + info['explain'] + '</p>');
    strHTML.push('<div class="' + info['font'] + '" id="simpleInsert"></div>');
    $('#sectionSimpleTask').html(strHTML.join(''));
    $('#simpleInsert').html(pleaseWait());
    showSection('SimpleTask');
    $.ajaxSetup({ cache: false });
    $.getJSON(info['route'], function (result) {
        var strTable = [];
        if (result['error'] == 0) {
            var cols = result['header'].length;
            var rows = result['data'].length;
            strTable.push('<table class="table table-striped table-hover"><thead><tr>');
            for (var i=0; i < cols; i++)
                strTable.push('<th>' + result['header'][i] + '</th>');
            strTable.push('</tr></thead><tbody>');
            for (var j = 0; j < rows; j++) {
                strTable.push('<tr>');
                for (var i = 0; i < cols ; i++)
                    strTable.push(frameCol(result['data'][j][i]));
                strTable.push('</tr>');
            }
            strTable.push('</tbody></table>');
        }
        else {
            strTable.push(frameError(result['errormsg']));
        }
        $('#simpleInsert').html(strTable.join(''));
    })
    .error(function () {
        $('#simpleInsert').html(frameError('Error occured while retrieving information.'));
    });
    $.ajaxSetup({ cache: true });
}

// create async table from a table information object

// Asynchronous version of displayTableLog


function displayTableLogAsync(info) {
    return new Promise((resolve, reject) => {
        $('#simpleTaskLog').html(pleaseWait());
        $.ajaxSetup({ cache: false });
        $.getJSON(info['route'], function (result) {
            var strTable = [];
            strTable.push('<div class="panel panel-default"><div class="panel-heading" ><h5>' + info['title'] + '</h5></div>');
            if (result['error'] == 0) {
                var cols = result['header'].length;
                var rows = result['data'].length;
                strTable.push('<table class="table table-striped table-hover table-fixed small"><thead><tr>');
                for (var i = 0; i < cols; i++)
                    strTable.push('<th>' + result['header'][i] + '</th>');
                strTable.push('</tr></thead><tbody>');
                for (var j = 0; j < rows; j++) {
                    strTable.push('<tr>');
                    for (var i = 0; i < cols; i++)
                        strTable.push(frameCol(result['data'][j][i]));
                    strTable.push('</tr>');
                }
                strTable.push('</tbody></table>');
            }
            else {
                strTable.push(frameError(result['errormsg']));
            }
            strTable.push('</div>');
            $('#simpleTaskLog').html(strTable.join(''));
            resolve(); // Resolve after successful data fetch and DOM update
        })
        .fail(function (jqxhr, textStatus, error) {
            $('#simpleTaskLog').html(frameError('Error occurred while retrieving information.'));
            reject(new Error("Error fetching table data: " + error)); // Reject on AJAX error
        });
        $.ajaxSetup({ cache: true });
    });
}

// create table from a table information object



function displayTableLog(info) {
    $('#simpleTaskLog').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.getJSON(info['route'], function (result) {
        var strTable = [];
        strTable.push('<div class="panel panel-default"><div class="panel-heading" ><h5>' + info['title'] + '</h5></div>');
        if (result['error'] == 0) {
            var cols = result['header'].length;
            var rows = result['data'].length;
            strTable.push('<table class="table table-striped table-hover table-fixed small"><thead><tr>');
            for (var i = 0; i < cols; i++)
                strTable.push('<th>' + result['header'][i] + '</th>');
            strTable.push('</tr></thead><tbody>'); 
            for (var j = 0; j < rows; j++) {
                strTable.push('<tr>');
                for (var i = 0; i < cols; i++)
                    strTable.push(frameCol(result['data'][j][i]));
                strTable.push('</tr>');
            }
            strTable.push('</tbody></table>');
        }
        else {
            strTable.push(frameError(result['errormsg']));
        }
        strTable.push('</div>');
        $('#simpleTaskLog').html(strTable.join(''));
    })
    .error(function () {
        $('#simpleTaskLog').html(frameError('Error occured while retrieving information.'));
    });
    $.ajaxSetup({ cache: true });
}




// frame error
function frameError(strError) {
    return '<h5 class="text-danger">' + strError + '</h5>'

}

// frames a column in a table
function frameCol(strVal) {
    return '<td>' + ((strVal == '' || strVal == ' ') ? '&nbsp;' : strVal) + '</td>'
}

// New Test
//
// frames a column in a table right aligned
function frameColCenter(strVal) {
    return '<td align="center">' + ((strVal == '' || strVal == ' ') ? '&nbsp;' : strVal) + '</td>'
}

// New Above

// frames a column with id in a table
function frameColId(strVal, strId) {
    return '<td id="' + strId + '">' + strVal + '</td>'
}

// frame tool tip 
function addTip(label, info) {
    return '<a href="#" data-toggle="tooltip" title="' + info + '">' + label + '</a>';

}

// show update btn
function formBtn(strName) {
    return '<button type="submit" class="btn btn-primary btn-md">' + strName + '</button>';
}


// lfts old command options -- for historical purposes
function getOldLTSFCmds() {
    return { 'a': 'Add to Library', 'f': 'Format', '-f -- -f': 'Forced Format', 'r': 'Remove', 'm': 'Move to I/O Slot', 'i': 'Read Index', 'c': 'check' };
}


// ltfs new command options
function getLTSFCmds() {
    return { 'tape assign': 'Add to Library', 'tape format': 'Format', 'tape format -f': 'Forced Format', 'tape unassign': 'Unassign', 'tape move -L ieslot': 'Move to I/O Slot', 'tape sync': 'Read Index', 'tape recover': 'Recover' };
}


// build select statement for managing tapes
function buildSelect(strId, optionArray, trans, itemStatus) {
    var strSelect = [];
    var items = optionArray.length
    if (items == 0)
        strSelect[0] = '&nbsp';
    else {
            strSelect.push('<select id="' + strId + '" name="' + strId + '">');
            strSelect.push('<option value="">- select -</option>');
            for (var i = 0; i < items; i++)
                strSelect.push('<option value="' + optionArray[i] + '|' + itemStatus + '">' + trans[optionArray[i]] + '</option>');
            strSelect.push('</select>');
    }
    return strSelect.join('');
}

// set to format all tapes that are unformatted
function setToFormat(objArray) {
    $.each(objArray, function (index, value) {
        $('#tape' + value + ' option:eq(1)').prop('selected', true);
    });
}

// add credentials to form
function addCredentials() {
    return '<input id="adminName1"  name="adminName1" type="hidden"  value="' + $('#adminName').val() + '"/><input id="adminPassword1"  name="adminPassword1" type="hidden"  value="' + $('#adminPassword').val() + '"/>';
}

// add tape table properties
function tapeTableProperties(source, rows) {
    return '<input id="source"  name="source" type="hidden"  value="' + source + '"/><input id="tapes"  name="tapes" type="hidden"  value="' + rows + '"/>';
}

// add tape table properties
function blankHiddenObject(objectName) {
    return '<input id="' + objectName + '"  name="' + objectName + '" type="hidden"  value=""/>';
}

// add taoe table properties
function hiddenObjectValue(objectName, value) {
    return '<input id="' + objectName + '"  name="' + objectName + '" type="hidden"  value="' + value + '"/>';
}

// post management actions for tapes
function submitManageTapes(objForm) {
    $('#ManageTapesInfo').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post('submitManageTapes', $("#tape_edit").serialize())
    .done(function (result) {
//        var rtnFunction = (result['source'] == 'vd') ? 'vdManageTapes();' : 'ltfsManageTapes();';
        $('#ManageTapesInfo').html(frameError(result['errormsg'])) // + '<p><button type="button" class="btn btn-primary btn-md" onclick="' + rtnFunction + '">Reset</button>&nbsp;' +  btnTapeQueue('Queued') + '</p>');
        setTimeout("tapeQueue('Queued')", 2500);
    })
    .fail(function () { 
        $('#simpleInsert').html(frameError('Error occured while submitting request.'));
    });
    $.ajaxSetup({ cache: true });

    return false;
}

// create button for tape queue view
function btnTapeQueue(view) {
    return '<button type="button" class="btn btn-primary btn-md" onclick="tapeQueue(\'' + view + '\');">' + view + '</button>&nbsp;';
}

function btnRestoreQueue(view) {
    return '<button type="button" class="btn btn-primary btn-md" onclick="restoreQueue(\'' + view + '\');">' + view + '</button>&nbsp;';
}

// create table from a table information object
function tapeQueue(requestStatus) {
    var info = { font: 'small', route: 'tapequeue', title: 'Tape Management Queue', explain: 'Use the selections below the table to review the tape management queue based on the request status or to delete a request that has been queued.' };
    var strHTML = [];
    $('#extra').val(requestStatus)
    strHTML.push('<h2>' + info['title'] + '</h2>');
    if (info['explain'] != '')
        strHTML.push('<p>' + info['explain'] + '</p>');
    strHTML.push('<div class="' + info['font'] + '" id="simpleInsert"></div>');
    $('#sectionSimpleTask').html(strHTML.join(''));
    $('#simpleInsert').html(pleaseWait());
    showSection('SimpleTask');
    $.ajaxSetup({ cache: false });
    $.post(info['route'], $("#login_form").serialize())
    .done(function (result) {
        var strTable = [];
        if (result['error'] == 0) {
            var cols = result['header'].length;
            var rows = result['data'].length;
            var extra = result['extra'];
            if (extra != 'Completed' && extra != 'Cancelled')
                cols--;
            strTable.push('<form id="tape_cancel"  name="tape_cancel" onsubmit="return submitCancelTapes(this)">');
            strTable.push(addCredentials());
            strTable.push(hiddenObjectValue('row', rows));
            strTable.push('<table class="table table-striped table-hover"><thead><tr>');
            for (var i = 0; i < cols; i++)
                strTable.push('<th>' + result['header'][i] + '</th>');
            if (extra == 'Queued')
                strTable.push('<th>Delete Request</th>');
            strTable.push('</tr></thead><tbody>');
            for (var j = 0; j < rows; j++) {
                strTable.push('<tr>');
                for (var k = 0; k < cols; k++)
                    strTable.push(frameCol(result['data'][j][k]));
                if (extra == 'Queued')
                    if (result['data'][j][2] == 'Queued')
                        strTable.push(frameCol('<input name="id' + j + '" id="id' + j + '" value="' + result['data'][j][5] + '" type="checkbox" />'));
                    else
                        strTable.push(frameCol('&nbsp;'));
                strTable.push('</tr>');
            }
            strTable.push('</tbody></table>');
            strTable.push('<div id="ManageTapesInfo">');
            strTable.push(btnTapeQueue('Queued'));
            strTable.push(btnTapeQueue('Completed'));
            strTable.push(btnTapeQueue('Cancelled'));
            if (extra == 'Queued')
                strTable.push('&nbsp;&nbsp;&nbsp;&nbsp;' + formBtn('Submit'));
            strTable.push('</div>');
            strTable.push('</form>');
            $('#simpleInsert').html(strTable.join(''));
            $('[data-toggle="tooltip"]').tooltip();
        }
        else {
            strTable.push(frameError(result['errormsg']));
            $('#simpleInsert').html(strTable.join(''));
        }
    })
    .fail(function () {
        $('#simpleInsert').html(frameError('Error occured while retrieving information.'));
    });
    $.ajaxSetup({ cache: true });

}

// post management actions for tapes
function submitCancelTapes(objForm) {
    $('#ManageTapesInfo').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post('submitCancelTapes', $("#tape_cancel").serialize())
    .done(function (result) {
        $('#ManageTapesInfo').html(frameError(result['errormsg']));
        setTimeout("tapeQueue('Queued')", 2500);
    })
    .fail(function () {
        $('#simpleInsert').html(frameError('Error occured while submitting request.'));
    });
    $.ajaxSetup({ cache: true });

    return false;
}




