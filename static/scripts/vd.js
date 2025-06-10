// EL20Beta+
// EchoLeaf Version 1.5a / 1.5c
// vd tape status
// Adds GB Remaining to Manage Tapes

function vdTapeStatus() {
    return {
        'rogue': 'New LTO tape added to library which has not been inventoried',
        'new': 'LTO tape with a  Valid LTFS status which has been inventoried by the EchoLeaf system',
        'used': 'LTO tape that has been inventoried by the EchoLead system but is not currently in the tape library.',
        'active': 'LTO tape that is currently used as the active tape for archiving files.',
        'full': 'LTO tape that has been inventoried by the EchoLeaf system but is out of space for archiving.'};
}

// MoveFile Log

// MoveFile Log


// File Move Log (using displayTableLogAsync)

function filemovelogtable() {
    return new Promise((resolve, reject) => {
        var tableInfo = { font: 'small', route: 'fileMoveLog', title: 'Files Moved Between Disk and Tape', explain: '' };
        displayTableLogAsync(tableInfo)
            .then(() => resolve()) // Resolve when displayTableLogAsync is done
            .catch(reject);        // Reject if displayTableLogAsync fails
    });
}



//to tape queue table
function totapequeuetable() {
    var tableInfo = { font: 'small', route: 'totapequeue', title: 'Files Queued for Tape Archive', explain: 'Listing of newly writen files to disk cache that are scheduled to be archived to tape.' };
    displayTable(tableInfo);
}

//clear disk queue table
function cleardiskqueuetable() {
    var tableInfo = { font: 'small', route: 'cleardiskqueue', title: 'Files Queued for Cache Removal', explain: 'Listing of disk cache files retreived from tape scheduled to be re-stubbed to reclaim disk space.' };
    displayTable(tableInfo);
}

// display property table
function properytable() {
    var tableInfo = { font: 'small', route: 'properytable', title: 'Virtual Drive &amp; File Manager Properties', explain: 'Listing of current Virtual Drive and File Manager properties. To edit these properties the Virtual Disk and File Manager need to be stopped.' };
    displayTable(tableInfo);
}


// build and display property update form
function buildPropertyForm() {
    var strHTML = [];
    strHTML.push('<h2>Update EchoLeaf Properties</h2>');
    strHTML.push('<p>Review and update the list of system properties below. <span class="text-danger">WARNING:</span>Changing any of the values below could result in disabling your system.</p>');
    strHTML.push('<div class="" id="simpleInsert"></div>');
    $('#sectionSimpleTask').html(strHTML.join(''));
    $('#simpleInsert').html(pleaseWait());
    showSection('SimpleTask');
    $.ajaxSetup({ cache: false });
    $.post("editproperties", $("#login_form").serialize())
        .done(function (result) {
            var strForm = [];
            if (result['error'] == 0) {
                var rows = result['data'].length;
                strForm.push('<form class="form-horizontal" role="form" id="property_edit" onsubmit="return validateProperties(this)">');
                strForm.push(addCredentials());
                for (var i = 0; i < rows; i++) {
                    strForm.push('<div class="form-group"><label class="control-label col-sm-3 nobold" for="' + result['data'][i][0] + '">' + addTip(result['data'][i][1], result['data'][i][3]) + ':</label>');
                    strForm.push('<div class="col-sm-9"><input type="text" class="form-control" id="' + result['data'][i][0] + '"  name="' + result['data'][i][0] + '"  value="' + result['data'][i][2] + '">');
                    strForm.push('</div></div>');
                }
                strForm.push('<div class="form-group"><div class="col-sm-offset-3 col-sm-9" id="update_btn">' + formBtn('Update') + '</div></div></form>');
                strForm.push('<div class="col-sm-offset-3 col-sm-9" id="update_error"></p>');
                $('#simpleInsert').html(strForm.join(''));
                $('[data-toggle="tooltip"]').tooltip();
            }
            else {
                strForm.push('<p>' + result['errormsg'] + '</div>');
                $('#simpleInsert').html(strForm.join(''));
            }
        }, "json")
        .fail(function () {
            $('#simpleInsert').html('<p class=" small text-danger">Error occured while retrieving information.</p>');
        });
    $.ajaxSetup({ cache: true });

}

// vaidate and post property changes
function validateProperties() {
    $('#update_error').html('&nbsp;');
    $('#update_btn').html(pleaseWait());

    $.ajaxSetup({ cache: false });
    $.post("updateproperties", $("#property_edit").serialize())
        .done(function (data) {
            $('#update_btn').html(formBtn('Update'));
            $('#update_error').html(frameError(data['errormsg']))

        }, "json")
        .fail(function () {
            $('#update_btn').html(formBtn('Update'));
            $('#update_error').html(frameError('Problem occurred while updating property information.'))
        });
    $.ajaxSetup({ cache: true });
    return false;
}

// check if system functions are alive, return table of process status


function alive(strDiv) {
    $.ajaxSetup({ cache: false });
    $.getJSON("alive", function (result) {
        var mountName = mountprogram();
        var classes = ["danger ", "success", "warning"];
        var process = [mountName, "filemanager"];
        var processName = ["Virtual Drive", "File Manager"];
        var strHTML = '<table class="table table-hover "><thead><tr><th>EchoLeaf Process</th><th>Status</th><th>Run Time</th></tr></thead><tbody>';
        var maxRows = process.length;
        for (var i = 0; i < maxRows; i++) {
            strHTML += '<tbody><tr class="' + classes[result[process[i]][0]] + '"><td>' + processName[i] + '</td><td id="' + process[i] + 'Status" class="text-right">' + result[process[i]][1] + '</td><td id="' + process[i] + 'Uptime" class="text-right">' + result[process[i]][2] + '</td></tr>';
        }
        strHTML += '</tbody></table>';
        $('#' + strDiv).html(strHTML);
    });
    $.ajaxSetup({ cache: true });
}





// find mount program name
function mountprogram() {
    var programName;
    $.ajax({
        url: 'mountprogram',
        async: false,
        dataType: 'json',
        success: function (result) {
            programName = result.name;
        }
    });
    return programName;
}

// Fast track files to tape
function vdFastTrack() {
    var objTask = { rows: [["Files Fast Tracked:", "filesTracked"], ["&nbsp;", "taskButton"]], section: 'SimpleTask', title: 'Fast Track Cache', info: 'When files are written to cache there is a set delay before they are moved to tape based on the EchoLeaf Write Delay property.  This option allows the administrator to remove the delay for all files in cache.  All existing cache files will be immediately written to tape on the next cycle of the File Manager.', width: 5 };
    simpleTask(objTask);
    $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="vdFastTrackNow();">Fast Track</button>');
}

function vdFastTrackNow() {
    $('#taskButton').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post("fasttracknow", $("#login_form").serialize())
        .done(function (data) {
            if (data["error"] == 0) {
                $('#filesTracked').html(data["filesTracked"]);
            }
            else {
                $('#taskError').html("Fast Track failed! " + data["errormsg"]);
            }
            $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="vdFastTrackNow();">Fast Track</button>');
        }, "json")
        .fail(function () {
            $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="vdFastTrackNow();">Fast Track</button>');
            $('#taskError').html("Error occured in attempting to Fast Track cache files");;
        });
    $.ajaxSetup({ cache: true });
}


function vdStart() {
    $('#taskButton').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post("vdstart", $("#login_form").serialize())
        .done(function (data) {
            if (data["error"] == 0) {
                window.setTimeout("vdStartStop()", 2000);
            }
            else {
                $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="vdStart();">Start</button>');
                $('#taskError').html("Start failed! " + data["errormsg"]);
            }
        }, "json")
        .fail(function () {
            $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="vdStart();">Start</button>');
            $('#taskError').html("Error occured in attempting to start the Virtual Drive");;
        });
    $.ajaxSetup({ cache: true });

}

// Test for EL20Beta -- adding filemanager status to UI
// Virtual Drive Start/Stop


// In vd.js

function vdStartStop() {
    var objTask = {
        rows: [
            ["Status:", "taskStatus"],
            ["Run Time:", "taskStarted"],
            ["&nbsp;", "taskButton"]
        ],
        section: 'SimpleTask',
        title: 'Virtual Drive Start/Stop',
        info: 'The Virtual Drive is the location where applications read and write their data.  If the Virtual Drive is stopped and an attempt is made to read or write to mount point, the application will experience errors.',
        width: 5
    };
    var mountName = mountprogram();
    simpleTask(objTask);
    $.ajaxSetup({
        cache: false
    });
    $.getJSON("alive/" + mountName, function (result) {
        if (result['error'] == 0) {
            $('#taskStatus').html(result[mountName][1]);
            $('#taskStarted').html(result[mountName][2]);
            $('#taskError').html("&nbsp;");

            // Update vdStatus and vdUptime fields
            $('#vdStatus').html(result[mountName][1]);
            $('#vdUptime').html(result[mountName][2]);

            switch (result[mountName][0]) {
                case 0:
                    $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="vdStart();">Start</button>');
                    break;
                case 1:
                    $('#taskButton').html('<button type="button" class="btn  btn-danger btn-md" onclick="vdStop();">Stop</button>');
                    break;
            }
        } else {
            $('#taskButton').html('&nbsp;');
            $('#taskError').html(result['errormsg'])
        }
    })
    .error(function () {
        $('#taskError').html("Error occured while trying to status the Virtual Drive");
        // You might want to clear vdStatus and vdUptime here or display an error message
        $('#vdStatus').html("Error");
        $('#vdUptime').html("Error");
    });
    $.ajaxSetup({
        cache: true
    });
}




// stop virtual drive
function vdStop() {
    $('#taskButton').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post("vdstop", $("#login_form").serialize())
        .done(function (data) {
            if (data["error"] == 0) {
                window.setTimeout("vdStartStop()", 2000);
            }
            else {
                $('#taskButton').html('<button type="button" class="btn  btn-danger btn-md" onclick="vdStop();">Stop</button>');
                $('#taskError').html("Stop failed! " + data["errormsg"]);
            }
        }, "json")
        .fail(function () {
            $('#taskButton').html('<button type="button" class="btn  btn-danger btn-md" onclick="vdStop();">Stop</button>');
            $('#taskError').html("Error occured in attempting to stop the virtual drive");
        });
    $.ajaxSetup({ cache: true });
}

// start/stop file manager management

// start/stop file manager management New with more fm data and button to start fm

// Helper functions

function decrementTime(timeString) {
  var timeParts = timeString.split(':');
  var hours = parseInt(timeParts[0]);
  var minutes = parseInt(timeParts[1]);
  var seconds = parseInt(timeParts[2]);

  if (seconds > 0) {
    seconds--;
  } else {
    seconds = 59;
    if (minutes > 0) {
      minutes--;
    } else {
      minutes = 59;
      if (hours > 0) {
        hours--;
      } else {
        return "00:00:00"; // Time reached zero
      }
    }
  }

  return padZero(hours) + ":" + padZero(minutes) + ":" + padZero(seconds);
}

function padZero(number) {
  return (number < 10 ? '0' : '') + number;
}



function runFileManagerNow() {
    // Send AJAX request to runFileManager route
    $.post("runFileManager", function (data) {
        // ... handle the response ...
    });
}

// startfile manager management
function fmStart() {
    $('#taskButton').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post("fmstart", $("#login_form").serialize())
        .done(function (data) {
            if (data["error"] == 0) {
                window.setTimeout("fmStartStop()", 2000);
            }
            else {
                $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="fmStart();">Start</button>');
                $('#taskError').html("Start failed! " + data["errormsg"]);
            }
        }, "json")
        .fail(function () {
            $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="fmStart();">Start</button>');
            $('#taskError').html("Error occured in attempting to start the File Manager");
        });
    $.ajaxSetup({ cache: true });
}


// fmStartStop Function

function fmStartStop() {
    var objTask = {
        rows: [
            ["Status:", "taskStatus"],
            ["Run Time:", "taskStarted"],
            ["&nbsp;", "taskButton"]
        ],
        section: 'SimpleTask',
        title: 'File Manager Drive Start/Stop',
        info: 'The File Manager handles the archiving of files from disk to tape.  If the File Manager is stopped the EchoLeaf will no longer archive files to tape.',
        width: 5
    };
    simpleTask(objTask);
    $.ajaxSetup({
        cache: false
    });
    $.getJSON("alive/filemanager", function(result) {
        if (result['error'] == 0 || result['error'] == 99) {
            $('#taskStatus').html(result['filemanager'][1]);
            $('#taskStarted').html(result['filemanager'][2]);
            $('#taskError').html("&nbsp;");

            // Update fmStatus and fmUptime fields
            $('#fmStatus').html(result['filemanager'][1]);
            $('#fmUptime').html(result['filemanager'][2]);
        }
        if (result['error'] == 0)
            switch (result["filemanager"][0]) {
                case 0:
                    $('#taskButton').html('<button type="button" class="btn btn-success btn-md" onclick="fmStart();">Start</button>');
                    break;
                case 1:
                    $('#taskButton').html('<button type="button" class="btn  btn-danger btn-md" onclick="fmStop();">Stop</button>');
                    break;
            } else {
            $('#taskButton').html('&nbsp;');
            $('#taskError').html(result['errormsg'])
            if (result['error'] == 99)
                $('#taskButton').html('<button type="button" class="btn  btn-primary btn-md" onclick="fmStartStop();">Refresh</button>')
        }

        // REMOVE OR COMMENT OUT THESE LINES:
        // setTimeout(function() {
        //     $('#fmCycleInterval').text("10 minutes");
        // }, 100);
    })
    .error(function() {
        $('#taskError').html("Error occured while trying to status the File Manager");
        // Clear or display an error in fmStatus and fmUptime
        $('#fmStatus').html("Error");
        $('#fmUptime').html("Error");
    });
    $.ajaxSetup({
        cache: true
    });
}



// stop file manager
function fmStop() {
    $('#taskButton').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post("fmstop", $("#login_form").serialize())
        .done(function (data) {
            if (data["error"] == 0) {
                window.setTimeout("fmStartStop()", 2000);
            }
            else {
                $('#taskButton').html('<button type="button" class="btn  btn-danger btn-md" onclick="vdStop();">Stop</button>');
                $('#taskError').html("Stop failed! " + data["errormsg"]);
            }
        }, "json")
        .fail(function () {
            $('#taskButton').html('<button type="button" class="btn  btn-danger btn-md" onclick="vdStop();">Stop</button>');
            $('#taskError').html("Error occured in attempting to stop the virtual drive");
        });
    $.ajaxSetup({ cache: true });
}

function vdStatusTapes() {
    var tableInfo = { font: 'small', route: 'vdtapes', title: 'EchoLeaf Tape Information', explain: 'LTO tapes currently registered with the virtual drive system.' };
    displayTable(tableInfo);
}

// virtual drive table management
function vdManageTapes() {
    var info = { font: 'small', route: 'vdmanagetapes', title: 'EchoLeaf Tape Management', explain: 'Make sure File Manager is running. Select the management option for each cartridge. To select "Format" on all unformated cartridge click "Format All Unformated". Click "Submit" when finished.' };
    var strHTML = [];
    strHTML.push('<h2>' + info['title'] + '</h2>');
    if (info['explain'] != '')
        strHTML.push('<p>' + info['explain'] + '</p>');
    strHTML.push('<div class="' + info['font'] + '" id="simpleInsert"></div>');
    $('#sectionSimpleTask').html(strHTML.join(''));
    showSection('SimpleTask');
    $('#simpleInsert').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post(info['route'], $("#login_form").serialize())
    .done(function (result) {
        var strTable = [];
        if (result['error'] == 0) {
            var ltfsCmds = getLTSFCmds();
            var ltfsInfo = getLTFSInfo();
            var vdInfo = vdTapeStatus();
            var cols = result['header'].length;
            var rows = result['data'].length;
            var gbremaining = [];
            var tapesToFormat = [];
            var noCommand = [];
            strTable.push('<form id="tape_edit" name="tape_edit" onsubmit="return submitManageTapes(this)">');
            strTable.push('<table class="table table-striped table-hover"><thead><tr>');
            strTable.push(addCredentials());
            strTable.push(tapeTableProperties('vd', rows));
            for (var i = 0; i < 2; i++)
                strTable.push('<th>' + result['header'][i] + '</th>');
            strTable.push('<th align="right">GB Remaining</th>');               
            strTable.push('<th>EchoLeaf Status</th>');
            strTable.push('<th>Management Options</th>');
            strTable.push('</tr></thead><tbody>');
            for (var j = 0; j < rows; j++) {
                strTable.push('<tr>');
                strTable.push(frameCol(result['data'][j][0]));
//new                
                gbremaining = ((result['data'][j][26])/1000);
//new                
                if (result['data'][j][1] in ltfsInfo) {
                    strTable.push(frameCol(addTip(result['data'][j][1], ltfsInfo[result['data'][j][1]]['info'])));
//                    strTable.push(frameCol(result['data'][j][26]));
// new
                    strTable.push(frameColCenter(gbremaining));
// new                    
                    strTable.push(frameCol(addTip(result['data'][j][cols].toLowerCase(), vdInfo[result['data'][j][cols].toLowerCase()])));
                    strTable.push(frameCol(buildSelect('tape' + j, ltfsInfo[result['data'][j][1]]['select'], ltfsCmds, result['data'][j][0] + '|' + result['data'][j][1] + '|' + result['data'][j][cols].toLowerCase())));
                    if (result['data'][j][1] == 'NEED_FORMAT')
                        tapesToFormat[tapesToFormat.length] = j;
                }
                else {
                    strTable.push(frameCol(result['data'][j][1]));
//                    strTable.push(frameCol(result['data'][j][26]));
// new
                    strTable.push(frameColCenter(gbremaining));
// new                    
                    strTable.push(frameCol(addTip(result['data'][j][cols].toLowerCase(), vdInfo[result['data'][j][cols].toLowerCase()])));
                    strTable.push(frameCol('&nbsp;'));
                    noCommand[noCommand.length] = j;
                }
                strTable.push('</tr>');
            }
            strTable.push('</tbody></table>');
            strTable.push('<div id="ManageTapesInfo">');
            strTable.push('<button type="button" class="btn btn-primary btn-md" onclick="vdManageTapes();">Reset</button>&nbsp;');
            if (tapesToFormat.length > 0)
                strTable.push('<button type="button" class="btn btn-primary btn-md" onclick="setToFormat(' + JSON.stringify(tapesToFormat) + ');">Format All Unformatted</button>&nbsp;');
            strTable.push('&nbsp;&nbsp;&nbsp;&nbsp;' + formBtn('Submit'));
            strTable.push('</div>');
            for (var i = 0; i < noCommand.length; i++)
                blankHiddenObject('tape' + i);
            strTable.push('</form>');
            $('#simpleInsert').html(strTable.join(''));
            $('[data-toggle="tooltip"]').tooltip();
        }
        else {
            strTable.push(frameError(result['errormsg']));
            $('#simpleInsert').html(strTable.join(''));
        }
    }, "json")
    .fail(function () {
        $('#simpleInsert').html(frameError('Error occured while retrieving information.'));
    });
    $.ajaxSetup({ cache: true });

}

//transform json diretory object
function transform(response) {
    var bloat = ['<ul class="jqueryFileTree" style="display: none;">'];
    if (response["error"] == 0) {
        var count = response["data"].length;
        for (var i = 0; i < count; i++)
            bloat.push(response["data"][i][0] == 0 ? '<li class="directory collapsed"><a href="#" rel="' + response["data"][i][1] + '">' + response["data"][i][2] + "</a></li>" : '<li class="file ext_' + response["data"][i][2] + '"><a href="#" rel="' + response["data"][i][1] + '">' + response["data"][i][3] + '</a></li>');
    }
    else
        bloat.push('Error: ' + response['errormsg']);
    bloat.push('</ul>');
    return bloat.join("");
}

//storage stats

function storageStats() {
    return new Promise((resolve, reject) => {
        $.ajaxSetup({ cache: false });
        $.getJSON('storagestats', function (result) {
            if (result['error'] == 0) {
                var rows = result['data'].length;
                var formattedTapes = 0;
                var tapeAvailable = 0;
                var tapeUsed = 0;
                var tapeTotal = 0;

                for (var j = 0; j < rows; j++) {
                    if (result['data'][j][1] == 'WRITABLE') {
                        formattedTapes++;
                        tapeUsed += parseInt(result['data'][j][25]) - parseInt(result['data'][j][26]);
                        tapeAvailable += parseInt(result['data'][j][26]);
                        tapeTotal += parseInt(result['data'][j][25]);
                    } else if (result['data'][j][1] == 'METADATA_WRITABLE') {
                        formattedTapes++;
                        tapeUsed += parseInt(result['data'][j][25]) - parseInt(result['data'][j][26]);
                        tapeAvailable += parseInt(result['data'][j][26]);
                        tapeTotal += parseInt(result['data'][j][25]);
                    }
                }

                $('#formattedTapes').html(formattedTapes.toLocaleString());
                $('#tapeTotalSpace').html(Math.round(tapeTotal / 1000).toLocaleString());
                $('#tapeUsed').html(Math.round(tapeUsed / 1000).toLocaleString());
                $('#tapePercentUsed').html(Math.round(100 * tapeUsed / tapeTotal).toLocaleString() + '%');
                if (result['diskfree'] != -1) {
                    $('#cachefreespace').html(Math.round(result['diskfree'] / 1000).toLocaleString());
                } else {
                    $('#cachefreespace').html('unknown');
                }
                resolve(); // Resolve the promise after DOM updates
            } else {
                // Handle the error (e.g., display an error message)
                reject(new Error(result['errormsg'])); // Reject with the error message
            }
        })
        .fail(function (jqxhr, textStatus, error) {
            // Handle the AJAX error (e.g., display an error message)
            reject(new Error("Error fetching storage stats: " + error)); // Reject with the error message
        });
        $.ajaxSetup({ cache: true });
    });
}



// get directory
function dbdirectory() {
    $('#db_directory').fileTree();
    moveList.clear();
    showSection("DBTree");
}

// get file info
function filecopyinfo(fileId) {
    $.ajaxSetup({ cache: false });
    $.post("filecopyinfo", { "adminName": $('#adminName').val(), "adminPassword": $('#adminPassword').val(), "fileId": fileId })
        .done(function (result) {
            if (result["error"] == 0) {
                moveList.add(result['data']);
            }
            else 
                alert("Error: " + result["errormsg"]);
        }, "json")
        .fail(function () {
            alert('Error of file information lookup;')
        });
    $.ajaxSetup({ cache: true });
}



// create restore table queue
function restoreQueue(requestStatus) {
    var info = { font: 'small', route: 'restorequeue', title: 'Restore To Disk Management Queue', explain: 'Use the selections below the table to review the restore to disk  management queue based on the request status or to delete a request that has been queued.' };
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
            strTable.push('<form id="restore_cancel"  name="restore_cancel" onsubmit="return submitCancelRestore(this)">');
            strTable.push(addCredentials());
            strTable.push(hiddenObjectValue('row', rows));
            strTable.push('<table class="table table-striped table-hover"><thead><tr>');
            for (var i = 0; i < cols; i++)
                strTable.push('<th>' + result['header'][i] + '</th>');
            if (extra == 'Queued')
                strTable.push('<th>Delete Request</th>');
            for (var j = 0; j < rows; j++) {
                strTable.push('<tr>');
                for (var k = 0; k < 4; k++)
                    strTable.push(frameCol(result['data'][j][k]));
                strTable.push(frameCol(result[result['data'][j][4]]));
                if (extra == 'Queued')
                    if (result['data'][j][2] == 'Queued')
                        strTable.push(frameCol('<input name="id' + j + '" id="id' + j + '" value="' + result['data'][j][6] + '" type="checkbox" />'));
                    else
                        strTable.push(frameCol('&nbsp;'));
                else
                    strTable.push(frameCol(result['data'][j][5]));
                strTable.push('</tr>');
            }
            strTable.push('</tbody></table>');
            strTable.push('<div id="ManageRestoreInfo">');
            strTable.push(btnRestoreQueue('Queued'));
            strTable.push(btnRestoreQueue('Completed'));
            strTable.push(btnRestoreQueue('Cancelled'));
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

// cancel restore request
function submitCancelRestore(objForm) {
    $('#ManageRestoreInfo').html(pleaseWait());
    $.ajaxSetup({ cache: false });
    $.post('submitcancelrestore', $("#restore_cancel").serialize())
    .done(function (result) {
        $('#ManageRestoreInfo').html(frameError(result['errormsg']));
        setTimeout("restoreQueue('Queued')", 2500);
    })
    .fail(function () {
        $('#simpleInsert').html(frameError('Error occured while submitting request.'));
    });
    $.ajaxSetup({ cache: true });

    return false;
}


// build and display property update form
function buildFileSearchForm() {

    $('#move_list').html('&nbsp;');
    $('#db_directory').html('&nbsp;');
    var strHTML = [];
    strHTML.push('<h2>File Seach</h2>');
    strHTML.push('<p>Enter a directory and/or file partial name.  Select "Search" to return a list of matching files.</p>');
    strHTML.push('<div class="" id="simpleInsert"></div>');
    $('#sectionSimpleTask').html(strHTML.join(''));
    $('#simpleInsert').html(pleaseWait());
    showSection('SimpleTask');
    var data = [["Directory/Folder", "directory"], ["File ", "file"]];
    var rows = data.length;
    var strForm = [];
    strForm.push('<form class="form-horizontal" role="form" id="file_search" onsubmit="return validateFileSearch(this)">');
    strForm.push(addCredentials());
    for (var i = 0; i < rows; i++) {
        strForm.push('<div class="form-group"><label class="control-label col-sm-3 nobold" for="' + data[i][1] + '">' + data[i][0] + ':</label>');
        strForm.push('<div class="col-sm-9"><input type="text" class="form-control" id="' + data[i][1] + '"  name="' + data[i][1] + '">');
        strForm.push('</div></div>');
    }
    strForm.push('<div class="form-group"><div class="col-sm-offset-3 col-sm-9" id="seartch_btn">' + formBtn('Search') + '</div></div></form>');
    strForm.push('<div class="col-sm-offset-3 col-sm-9" id="update_error"></div>');

    $('#simpleInsert').html(strForm.join(''));
}

// vaidate and post property changes
function validateFileSearch() {
    if ($('#directory').val() == '' && $('#file ').val() == '') {
        $('#update_error').html(frameError('No search file or directory specified.'));
        window.setTimeout("buildFileSearchForm()", 2000);
        return false;
    }

    $('#update_error').html('&nbsp;');
    $('#seartch_btn').html(pleaseWait());

    $.ajaxSetup({ cache: false });
    $.post("filesearch", $("#file_search").serialize())
        .done(function (result) {
            if (result['error'] == 0) {
                if (result['data'].length == 0) {
                    $('#update_error').html(frameError('No files found based on search criteria.'));
                    window.setTimeout("buildFileSearchForm()", 2000);
                }
                else {
                    var strHTML = [];
                    strHTML.push('<h2>File Seach</h2>');
                    strHTML.push('<p>From the results table below select the location of files to be moved.</p>');
                    strHTML.push('<div class="small" id="simpleInsert"></div>');
                    $('#sectionSimpleTask').html(strHTML.join(''));

                    var strTable = [];
                    var header = ['File', 'Archived', 'Directory', 'Cartridge', 'In Library', 'Copy Location'];
                    var libraryStatus = ['no', 'yes'];
                    var moveCount = 0;
                    var passedInfo;
                    strTable.push('<form id="files_move"  name="files_move" onsubmit="return submitRestoreFile(this)">');
                    strTable.push('<table class="table table-striped table-hover"><thead><tr>');
                    rows = result['data'].length
                    for (var i = 0; i < header.length; i++)
                        strTable.push('<th>' + header[i] + '</th>');
                    strTable.push('</tr></thead><tbody>');
                    rows = result['data'].length
                    for (var i = 0; i < rows; i++) {
                        strTable.push('<tr> <td>' + result['data'][i][1] + '</td><td>'  + result['data'][i][5] + '</td><td>' + result['data'][i][4] + '</td><td>' +  result['data'][i][2] + '</td><td>' + libraryStatus[result['data'][i][3]] + '</td><td>');
                        if (result['data'][i][3] == 1) {
                            passedInfo = result['data'][i][0] + '|' + result['data'][i][1] + '|' + result['data'][i][2] + '|';
                            strTable.push('<select id="file' + moveCount + '" name="file' + moveCount + '"><option value= "">No Copy</option><option value="' + passedInfo + 'RestoreAlternate">Alternate</option><option value="' + passedInfo + 'VDiskMountPoint">Cache</option></select>');
                            moveCount++;
                        }
                        else
                            strTable.push('&nbsp;');
                    }
                    strTable.push('</tbody></table>');
                    if (moveCount > 0) {
                        strTable.push(hiddenObjectValue('rows', moveCount));
                        strTable.push(addCredentials());
                        strTable.push('<div id="dbTreeAction">');
                        strTable.push('<button type="button" class="btn btn-primary" onclick="buildFileSearchForm();">New Search</button>&nbsp;' + formBtn('Submit'));
                        strTable.push('</div');
                    }
                    strTable.push('</form>');
                    $('#simpleInsert').html(strTable.join(""));
                }
            }
            else
            {
                $('#update_error').html(frameError('Error: '+ result['errormsg']));
                $('#seartch_btn').html(formBtn('Search'));
            }
        }, "json")
        .fail(function () {
            $('#update_error').html(frameError('Problem occurred while searching for files information.'));
            $('#seartch_btn').html(formBtn('Search'));
        });
    $.ajaxSetup({ cache: true });
    return false;
}


// handle shift key combo for folder move
var shiftDown = false;
this.onkeydown = function (evt) {
    var evt2 = evt || window.event;
    var keyCode = evt2.keyCode || evt2.which;
    if (keyCode == 16) shiftDown = true;
}
this.onkeyup = function () {
    shiftDown = false;
}


// queue folder for movement
function folderCopyInfo(dirId) {
    shiftDown = false;
    $.ajaxSetup({ cache: false });
    $.post("foldercopyinfo", { "adminName": $('#adminName').val(), "adminPassword": $('#adminPassword').val(), "dirId": dirId })
        .done(function (result) {
            var fullName;
            if (result["error"] == 0) {
                if (moveList.newFolder(result) > 0) {
                    if (result['outLib'].length > 0)
                        moveList.missingTapeTable();
                    else {
                        $('#modalHeader').html('<h4 class="modal-title">Folder Restore Location</h4>');
                        $('#modalBody').html('<p>Please indicate the desired restore location for the selected folder.  The folder can be restored to Cache (virtual drive) or the Quarantine location.</p>');
                        $('#modalFooter').html('<button type="button" class="btn btn-default" data-dismiss="modal" onclick="moveList.clearFolder();">Cancel</button><button type="button" class="btn btn-primary" data-dismiss="modal" onclick="moveList.addFolder(0);">Quarantine</button><button type="button" class="btn btn-primary" data-dismiss="modal" onclick="moveList.addFolder(1);">Cache</button>'); // CHANGED TEXT HERE
                        $('#myModal').modal({ backdrop: "static" });
                    }
                }
                else {
                    $('#modalHeader').html('<h4 class="modal-title">No Folder Files to Move</h4>');
                    $('#modalBody').html('<p>No files exist in the requested folder/directory or the folder files have already been selected. Please cancel request.</p>');
                    $('#modalFooter').html('<button type="button" class="btn btn-default" data-dismiss="modal" onclick="moveList.clearFolder();">Cancel</button>');
                    $('#myModal').modal({ backdrop: "static" });
                }
            }
            else
                alert("Error: " + result["errormsg"]);
        }, "json")
        .fail(function () {
            alert('Error in folder information lookup;')
        });
    $.ajaxSetup({ cache: true });

}



// allows user to specify the location of the folder move from tape
function setFolderRestoreLocation() {
}


// --- Function to display the "File Search By Date" form ---  Now with console debug code.

// --- Function to display the "File Search By Date" form ---
function buildFileSearchFormDates() {
    $('#move_list').html('&nbsp;');        // Clear any previous move list
    $('#db_directory').html('&nbsp;');     // Clear any previous file tree
    hideAllSections();                   // Hide all other sections (using site.js function)
    $("#sectionFileSearchDates").show();  // Show the date search section
    $('#search_results_dates').html(''); // Clear any previous results
}

// --- Function to validate and submit the "File Search By Date" form ---


// In vd.js

// --- Function to validate and submit the "File Search By Date" form ---

function validateFileSearchDates() {
    var filename = $('#fileSearchFormDates_filename').val();
    var start_date = $('#start_date').val();
    var end_date = $('#end_date').val();

    // Regular expression to match mm/dd/yyyy format
    var date_regex = /^(0[1-9]|1[0-2])\/(0[1-9]|[12][0-9]|3[01])\/\d{4}$/;

    if (filename === '' && start_date === '' && end_date === '') {
        $('#search_results_dates').html(frameError('Please enter at least one search criteria.'));
        return false;
    }

    if (start_date !== '' && !date_regex.test(start_date)) {
        $('#search_results_dates').html(frameError('Invalid start date format. Please use mm/dd/yyyy.'));
        return false;
    }

    if (end_date !== '' && !date_regex.test(end_date)) {
        $('#search_results_dates').html(frameError('Invalid end date format. Please use mm/dd/yyyy.'));
        return false;
    }

    $('#search_results_dates').html('&nbsp;'); // Clear previous results/errors

    $.ajaxSetup({ cache: false });
    $.post("filesearchbydate", $("#fileSearchFormDates").serialize())
        .done(function (result) {
            if (result['error'] == 0) {
                if (result['data'].length == 0) {
                    $('#search_results_dates').html(frameError('No files found based on search criteria.'));
                } else {
                    // --- Build the results table ---
                    var strTable = [];
                    var header = ['Line #', 'File', 'Archived', 'Directory', 'Cartridge', 'In Library', 'Copy Location'];
                    var libraryStatus = ['no', 'yes'];
                    var moveCount = 0;
                    var passedInfo;

                    strTable.push('<form id="files_move_dates" name="files_move_dates">');
                    strTable.push('<table class="table table-striped table-hover"><thead><tr>');
                    for (var i = 0; i < header.length; i++) {
                        strTable.push('<th>' + header[i] + '</th>');
                    }
                    strTable.push('</tr></thead><tbody>');

                    for (var i = 0; i < result['data'].length; i++) {
                        strTable.push('<tr>');
                        strTable.push('<td>' + (moveCount + 1) + '</td>'); // Add line number
                        strTable.push('<td>' + result['data'][i][1] + '</td>'); // FileName
                        strTable.push('<td>' + result['data'][i][5] + '</td>'); // ArchiveDate
                        strTable.push('<td>' + result['data'][i][4] + '</td>'); // Directory (FullName)
                        strTable.push('<td>' + result['data'][i][2] + '</td>'); // TapeUID
                        strTable.push('<td>' + libraryStatus[result['data'][i][3]] + '</td>'); // InLibrary (0 or 1)
                        strTable.push('<td>');

                        if (result['data'][i][3] == 1) { // If InLibrary
                            passedInfo = result['data'][i][0] + '|' + result['data'][i][4] + '|' + result['data'][i][2] + '|'; // fileID|fullpath|tapeUID|
                            strTable.push('<select id="file' + moveCount + '" name="file' + moveCount + '">');
                            strTable.push('<option value="">No Copy</option>');
                            strTable.push('<option value="' + passedInfo + 'RestoreAlternate">Quarantine</option>'); // CHANGED TEXT HERE
                            strTable.push('<option value="' + passedInfo + 'VDiskMountPoint">Cache</option>');
                            strTable.push('</select>');
                            moveCount++;
                        } else {
                            strTable.push('&nbsp;');
                        }

                        strTable.push('</tr>');
                    }
                    strTable.push('</tbody></table>');

                    if(moveCount>0) {
                        strTable.push(hiddenObjectValue('rows', moveCount));
                        strTable.push(addCredentials());
                        strTable.push('<div id="dbTreeAction">');
                        strTable.push('<button type="button" class="btn btn-primary" onclick="buildFileSearchFormDates();">New Search</button>&nbsp;');
                        strTable.push('<button type="button" class="btn btn-primary" onclick="submitRestore(\'files_move_dates\');">Submit</button>');
                        strTable.push('</div>');
                    }
                    strTable.push('</form>');

                    $('#search_results_dates').html(strTable.join(''));
                }
            } else {
                $('#search_results_dates').html(frameError('Error: ' + result['errormsg']));
            }
        })
        .fail(function () {
            $('#search_results_dates').html(frameError('Problem occurred while searching for files information.'));
        });

    $.ajaxSetup({ cache: true });
    return false; // Prevent default form submission
}



// vaidate and post property changes
// vaidate and post property changes

function validateFileSearch() {
    if ($('#directory').val() == '' && $('#file ').val() == '') {
        $('#update_error').html(frameError('No search file or directory specified.'));
        window.setTimeout("buildFileSearchForm()", 2000);
        return false;
    }

    $('#update_error').html('&nbsp;');
    $('#seartch_btn').html(pleaseWait());

    $.ajaxSetup({ cache: false });
    $.post("filesearch", $("#file_search").serialize())
        .done(function (result) {
            if (result['error'] == 0) {
                if (result['data'].length == 0) {
                    $('#update_error').html(frameError('No files found based on search criteria.'));
                    window.setTimeout("buildFileSearchForm()", 2000);
                }
                else {
                    var strHTML = [];
                    strHTML.push('<h2>File Seach</h2>');
                    strHTML.push('<p>From the results table below select the location of files to be moved.</p>');
                    strHTML.push('<div class="small" id="simpleInsert"></div>');
                    $('#sectionSimpleTask').html(strHTML.join(''));

                    var strTable = [];
                    var header = ['Line #', 'File', 'Archived', 'Directory', 'Cartridge', 'In Library', 'Copy Location'];
                    var libraryStatus = ['no', 'yes'];
                    var moveCount = 0;
                    var passedInfo;
                    strTable.push('<form id="files_move"  name="files_move">');
                    strTable.push('<table class="table table-striped table-hover"><thead><tr>');
                    rows = result['data'].length
                    for (var i = 0; i < header.length; i++)
                        strTable.push('<th>' + header[i] + '</th>');
                    strTable.push('</tr></thead><tbody>');
                    rows = result['data'].length
                    for (var i = 0; i < rows; i++) {
                        strTable.push('<tr>');
                        strTable.push('<td>' + (moveCount + 1) + '</td>'); // Add line number
                        strTable.push('<td>' + result['data'][i][1] + '</td><td>'  + result['data'][i][5] + '</td><td>' + result['data'][i][4] + '</td><td>' +  result['data'][i][2] + '</td><td>' + libraryStatus[result['data'][i][3]] + '</td><td>');
                        if (result['data'][i][3] == 1) {
                            passedInfo = result['data'][i][0] + '|' + result['data'][i][4] + '|' + result['data'][i][2] + '|'; // fileID|fullpath|tapeUID|
                            strTable.push('<select id="file' + moveCount + '" name="file' + moveCount + '"><option value= "">No Copy</option><option value="' + passedInfo + 'RestoreAlternate">Quarantine</option><option value="' + passedInfo + 'VDiskMountPoint">Cache</option></select>'); //CHANGED TEXT HERE
                            moveCount++;
                        }
                        else
                            strTable.push('&nbsp;');
                        strTable.push('</tr>');

                    }
                    strTable.push('</tbody></table>');
                    if (moveCount > 0) {
                        strTable.push(hiddenObjectValue('rows', moveCount));
                        strTable.push(addCredentials());
                        strTable.push('<div id="dbTreeAction">');
                        strTable.push('<button type="button" class="btn btn-primary" onclick="buildFileSearchForm();">New Search</button>&nbsp;');
                        strTable.push('<button type="button" class="btn btn-primary" onclick="submitRestore(\'files_move\');">Submit</button>'); // Changed to call submitRestore()

                        strTable.push('</div');
                    }
                    strTable.push('</form>');
                    $('#simpleInsert').html(strTable.join(""));
                }
            }
            else
            {
                $('#update_error').html(frameError('Error: '+ result['errormsg']));
                $('#seartch_btn').html(formBtn('Search'));
            }
        }, "json")
        .fail(function () {
            $('#update_error').html(frameError('Problem occurred while searching for files information.'));
            $('#seartch_btn').html(formBtn('Search'));
        });
    $.ajaxSetup({ cache: true });
    return false;
}



// --- NEW Unified submitRestore function ---
// --- NEW Unified submitRestore function (REPLACES submitRestoreFile and submitRestoreFileDates) ---
function submitRestore(formId) {
    console.log("submitRestore() called!"); // Add this line
    console.log("formId:", formId); // Add this line
    
    $('#dbTreeAction').html(pleaseWait()); // Show "Please Wait"

    $.ajaxSetup({ cache: false });
    $.post("submitrestorefile", $("#" + formId).serialize())
        .done(function (data) {
            $('#dbTreeAction').html(frameError(data['errormsg']));
            setTimeout("restoreQueue('Queued')", 2500);
        }, "json")
        .fail(function () {
            alert("System error occured when submitting restore file request.");
            // moveList.clear(); // ONLY clear if successful?  Up to you.
        });
    $.ajaxSetup({ cache: true });
    return false;
}
