// EchoLeaf Version 1.4a / 1.5c
// get ltfs library inventory / fix writable metadata options
// ltfs status info
function getLTFSInfo() {
    return {
        'Valid LTFS': { 'info': 'The cartridge is valid. The index file is extracted to memory so that some file system requests, such as listing directory contents, can be processed without mounting a tape medium to a drive.', 'select': ['x', 'r', 'm'] },
        'In Progress': { 'info': 'The cartridge is being moved by LTFS from storage slot to drive or from drive to storage slot.', 'select': [] },
        'Unknown': { 'info': 'The cartridge contents are unknown. The index file must be read on the tape medium before most file system requests can be processed.', 'select': ['i', 'r', 'm'] },
        'Write protected': { 'info': 'Write protected	The cartridge is physically (or logically) in a write-protected or read-only state because of an absence of capacity. This status is reported only when the cartridge is "Valid." If the cartridge is in any state other than "Valid," the status is reported even though the cartridge is write protected.', 'select': ['r', 'm'] },
        'Warning': { 'info': 'A medium error is detected while the medium is being read. The operations that can be performed using this cartridge, however, are the same as for a "Valid" cartridge. This status is reported only when the cartridge is "Valid." If the cartridge is any state other than "Valid," the status is reported even though the cartridge has reported a medium error.', 'select': ['r', 'm'] },
        'Critical': { 'info': 'The index on memory is dirty. Data might not be able to be written to the tape medium due to the medium status. The volume is dropped to read-only and the drive is locked so that the cartridge cannot be removed. The drive scheduler excludes the drive from its scheduling in order to avoid an unexpected cartridge removal with an index write failure. The user can perform any backup operation in this state. Once the backup is completed, the user can remove the cartridge from the drive by unlocking the drive with the -r option. The cartridge status then changes to an "Error" state.', 'select': ['r', 'm'] },
        'Unavailable': { 'info': 'The cartridge has no problem, but is removed from LTFS. Adding cartridge might change the cartridge status to "Valid," "Unknown," "Write Protected," or "Warning."', 'select': ['a', 'm'] },
        'Invalid LTFS': { 'info': 'The cartridge is inconsistent with the LTFS format and must be checked.', 'select': ['c', 'm'] },
        'Unformatted': { 'info': 'The cartridge is not formatted and must be formatted.', 'select': ['f', 'm'] },
        'Inaccessible': { 'info': 'The cartridge is not allowed to move in the library or might be stuck in the drive. If the cartridge is stuck in the drive, the drive scheduler excludes this drive from its scheduling.', 'select': [] },
        'Error': { 'info': 'The cartridge status is "Critical" and the cartridge is removed from the library. LTFS does not allow the cartridge to be added to the file system again.', 'select': ['m'] },
        'Non-supported': { 'info': 'The cartridge is an older generation, an encrypted cartridge in a library with an enabled encryption feature, or a write-once, read-many (WORM) cartridge.', 'select': ['m'] },
        'Duplicated': { 'info': 'Two cartridges exist with the same bar code.', 'select': [] },
        'Cleaning': { 'info': '', 'select': ['m'] },   
        'WRITABLE': { 'info': 'The cartridge is valid and writable.', 'select': ['tape unassign'] },
		'WRITE_PROTECTED': { 'info': 'The tape is physically write-protected or advisory-locked from the LTFS Format Specification point of view. This status is reported only when the cartridge is write-protected or advisory-locked, and the LTFS format is detected as being correct.', 'select': ['tape unassign', 'tape move -L ieslot'] },
		'NOT_MOUNTED_YET': { 'info': 'The cartridge contents are unknown. The index file must be read on the tape medium before most file system requests can be processed.', 'select': ['tape recover','tape unassign'] },
		'NEED_FORMAT': { 'info': 'The tape is not formatted with LTFS.', 'select': ['tape format','tape move -L ieslot'] },		     
		'NEED_ASSIGN': { 'info': 'The tape is not listed as a resource in the Spectrum Archive system.', 'select': ['tape assign','tape move -L ieslot'] },
		'FULL': { 'info': 'The tape is full. All attempts to update it are rejected.', 'select': ['tape move -L ieslot'] },
		'METADATA_WRITABLE': { 'info': 'The tape is almost full. Only an update to the metadata is accepted.', 'select': ['tape unassign'] },
		'NON_SUPPORTED_TAPE': { 'info': 'A blacklisted bar code, such as "XXXXXXL2", or a cartridge type in CM are not supported by Spectrum Archive.', 'select': ['tape move -L ieslot'] },
		'INACCESSIBLE': { 'info': 'The tape cannot be included as a resource in the Spectrum Archive system because of the library, or because the drive that has this tape is not a resource of the Spectrum Archive system.', 'select': ['tape move -L ieslot'] },
		'DUPLICATED': { 'info': 'There are two or more tapes that have the same bar code.', 'select': ['tape assign','tape format', 'tape unassign', 'tape move -L ieslot'] },
		'LABEL_MISMATCH': { 'info': 'here is a mismatch between the bar code label and the VOL1 label on the tape. Only strict label checking is enabled.', 'select': ['tape assign','tape format', 'tape unassign', 'tape move -L ieslot'] },
		'WRITE_ERROR': { 'info': 'Permanent write errors were detected on both partitions (read only access).', 'select': ['tape recover', 'tape move -L ieslot'] },
		'WRITE_FENCED': { 'info': 'A permanent write error was detected on a partition (read only access).', 'select': ['tape assign','tape format', 'tape unassign', 'tape move -L ieslot'] },
		'READ_ERROR': { 'info': 'A medium error is detected while the medium is being read. However, the operations that can be performed by using this cartridge are the same as for a "WRITABLE" cartridge. This status is reported only when the cartridge is "WRITABLE". If the cartridge is any state other than "WRITABLE" the status is reported even though the cartridge reports a medium error.', 'select': ['tape recover', 'tape unassign'] },
		'UNDECRYPTABLE': { 'info': 'The tape cannot be mounted because it has a decryption error.', 'select': ['tape assign','tape format', 'tape unassign', 'tape move -L ieslot'] },
		'NEED_HBA_CHECK': { 'info': 'The tape label can be read, but the length of the VOL1 label is incorrect.', 'select': ['tape assign','tape format', 'tape unassign', 'tape move -L ieslot'] },																						
		'NEED_RECOVERY': { 'info': 'The LTFS format on the tape is inconsistent.', 'select': ['tape recover','tape move -L ieslot'] },																						
		'NEED_UNLOCK': { 'info': 'The tape is locked in the drive. The index on memory is dirty. Data might not be able to be written to the tape medium due to the medium status. The volume is dropped to read-only and the drive is locked so that the cartridge cannot be removed. The drive scheduler excludes the drive from its scheduling to avoid an unexpected cartridge removal with an index write failure. The user can perform any backup operation in this state. When the backup is completed, the user can unlock the cartridge. The cartridge status then changes to a "WRITE_ERROR" or "NEED_RECOVERY" state.', 'select': ['tape assign','tape format', 'tape unassign', 'tape move -L ieslot'] },																						
          
    };
}

function ltfsStatusTapes() {
    var tableInfo = { font: 'small', route: 'librarytapes', title: 'LTFS Tape Information', explain: 'Listing of tapes currently available int the LTFS Library (tape device).' };
    displayTable(tableInfo);
}

// display ltfs library drives
function ltfsStatusDrives() {
    var tableInfo = { font: 'small', route: 'librarydrives', title: 'LTFS Drive Information', explain: 'Tape drives and their status in the LTFS inventory.' };
    displayTable(tableInfo);
}


// create table from a table information object
function ltfsManageTapes() {
    var info = { font: 'small', route: 'ltfsmanagetapes', title: 'LTFS Tape Management', explain: 'Make sure File Manager is running. Select the management option for each cartridge. To select "Format" on all unformated cartridge click "Format All Unformated". Click "Submit" when finished.' };
    var strHTML = [];
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
            var ltfsCmds = getLTSFCmds();
            var ltfsInfo = getLTFSInfo();
            var cols = result['header'].length;
            var rows = result['data'].length;
            var tapesToFormat = [];
            var noCommand = [];
            strTable.push('<form id="tape_edit"  name="tape_edit" onsubmit="return submitManageTapes(this)">');
            strTable.push(addCredentials());
            strTable.push(tapeTableProperties('ltfs', rows));
            strTable.push('<table class="table table-striped table-hover"><thead><tr>');
            for (var i = 0; i < 3; i++)
                strTable.push('<th>' + result['header'][i] + '</th>');
            strTable.push('<th>Management Options</th>');
            strTable.push('</tr></thead><tbody>');
            for (var j = 0; j < rows; j++) {
                strTable.push('<tr>');
                strTable.push(frameCol(result['data'][j][0]));
                if (result['data'][j][1] in ltfsInfo) {
                    strTable.push(frameCol(addTip(result['data'][j][1], ltfsInfo[result['data'][j][1]]['info'])));
                    strTable.push(frameCol(result['data'][j][2]));
                    strTable.push(frameCol(buildSelect('tape' + j, ltfsInfo[result['data'][j][1]]['select'], ltfsCmds, result['data'][j][0] + '|' + result['data'][j][1])));
                    if (result['data'][j][1] == 'NEED_FORMAT')
                        tapesToFormat[tapesToFormat.length] = j;
                }
                else {
                    strTable.push(frameCol(result['data'][j][1]));
                    strTable.push(frameCol(result['data'][j][2]));
                    strTable.push(frameCol('&nbsp;'));
                    noCommand[noCommand.length] = j;
                }
                strTable.push('</tr>');
            }
            strTable.push('</tbody></table>');
            strTable.push('<div id="ManageTapesInfo">');
            strTable.push('<button type="button" class="btn btn-primary btn-md" onclick="ltfsManageTapes();">Reset</button>&nbsp;');
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
    })
    .fail(function () {
        $('#simpleInsert').html(frameError('Error occured while retrieving information.'));
    });
    $.ajaxSetup({ cache: true });

}
