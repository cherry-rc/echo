#     15 Nov 2024 -- updated to ELSentry v2.0a beta / test for file manager data 

"""
EchoLeaf Version 1.5c / p3
Application: routes.py
Version: 1.0
Release Date: 01 Dec 2016
Description: Routes and views for the EchoLeaf administration application.

Change History:

EchoLeaf Version 1.4a

Copyright EchoLeaf 2016
"""

from bottle import route, view, route, run, request , response
from bottle import static_file

from datetime import datetime
import common
import subprocess
import json
from common import resetFMTimer  # Import the function

x = "yes"


@route('/')
@route('/index')
@view('index')
def home():
    """Renders the home page."""
    return dict(
        year=datetime.now().year
    )


@route('/contact')
@view('contact')
def contact():
    """Renders the contact page."""
    return dict(
        title='Contact',
        message='Your contact page.' + x,
        year=datetime.now().year
    )


@route('/mountprogram')
def mountprogram():
    """returns mount program name."""
    return dict(name=common.getMountName())


@route('/alive')
def alive():
    """Provides alive information."""
    return common.alive([common.getMountName(), 'filemanager'])


@route('/alive/<item>')
def aliveDistinct(item):
    """Provides alive informatikon."""
    result = common.alive([item])
    if item == 'filemanager' and result["error"] == 0:
        if result["filemanager"][0] == 1:
            dict = common.fileManagerCheck()
            if dict["error"] == 0:
                result['error'] = 99
                result['errormsg'] = "File manager is in the process of shutting down. Recheck at a later time."
            else:
                if dict["error"] == 2:
                    result['error'] = 3
                    result['errormsg'] = dict['errormsg']
    return result


@route('/login', method='POST')
def login():
    """validate login"""
    return common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))


@route('/fasttracknow', method='POST')
def fasttracknow():
    """fast track existing files in the ToTapeQueue"""
    result = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if result['error'] == 0:
        result = common.fastTrackfiles()
    else:
        result = {'error': result["error"], 'errormsg': result["errormmsg"]}
    return result


@route('/vdstart', method='POST')
def vdstart():
    """start virtual drive process"""
    result = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if result['error'] == 0:
        result = common.validateConfigMount()
        if result['error'] == 0:
            result = common.submitApp(common.getMountName() + '.py')
    else:
        result = {'error': result["error"], 'errormsg': result["errormmsg"]}
    return result


@route('/vdstop', method='POST')
def vdStop():
    """start virtual drive process"""
    result = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if result['error'] == 0:
        result = common.dismountVirtualDrive()
    return result


@route('/fmstart', method='POST')
def fmstart():
    """start file manager process"""
    result = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if result['error'] == 0:
        result = common.validateConfigFilemanager()
        if result['error'] == 0:
            result = common.submitApp('filemanager.py')
    else:
        result = {'error': result["error"], 'errormsg': result["errormmsg"]}
    return result


@route('/fmstop', method='POST')
def fmstop():
    """start file manager process"""
    result = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if result['error'] == 0:
        result = common.validateConfigFilemanager()
        if result['error'] == 0:
            result = common.removeFileManagerMarker()
    else:
        result = {'error': result["error"], 'errormsg': result["errormmsg"]}
    return result


@route('/librarytapes')
def librarytapes():
    """return ltfsadmin -X -i"""
    return common.ltfsAdminCmd('cartridge', 'leadm tape list -o xml')


@route('/ltfsmanagetapes', method='POST')
def librarytapes():
    """return ltfsadmin -X -i"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if dict["error"] == 0:
        dict = common.ltfsAdminCmd('cartridge', 'leadm tape list -o xml')
    return dict


@route('/librarydrives')
def librarydrives():
    """return ltfsadmin -X -I"""
    return common.ltfsAdminCmd('drive', 'leadm drive list -o xml')


@route('/properytable')
def properytable():
    """return property table"""
    return common.readProperties('Header, PropertyValue, Info', ['Property', 'Current Value', 'About'], 0)


@route('/editproperties', method='POST')
def editproperties():
    """propery info for editing"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if dict["error"] == 0:
        dict = common.propertiesSystemLiveCheck('Property, Header, PropertyValue, Info',
                                                ['Property', 'Header', 'PropertyValue', 'info'], 0)
    return dict


@route('/updateproperties', method='POST')
def updateproperties():
    """update properties"""
    dict = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    if dict["error"] == 0:
        dict = common.propertiesSystemLiveCheck('Property, PropertyValue', ['Property', 'PropertyValue'], 0)
        data = []
        rowCount = 0
        if dict["error"] == 0:
            for item in dict['data']:
                if item[0] != 'adminName1' and item[0] != 'adminPassword1':
                    if item[1] != request.forms.get(item[0]):
                        data.append([item[0], request.forms.get(item[0])])
                        rowCount += 1
            if rowCount > 0:
                dict = common.updateProperties(data)
            else:
                dict = {'error': 0, 'errormsg': 'No changes where detected in requested update.'}
    return dict


@route('/vdtapes')
def vdtapes():
    """return info from LTO Table"""
    return common.readVDTapeProperties()


@route('/vdmanagetapes', method='POST')
def vdmanagetapes():
    """return info from LTO Tableand echoleaf database"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if dict["error"] == 0:
        dict = common.addEchoLeafStatus()
    return dict


@route('/submitManageTapes', method='POST')
def submitManageTapes():
    """return info from LTO Tableand echoleaf database"""
    source = request.forms.get("source")
    dict = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    rowCount = 0
    if dict["error"] == 0:
        if source == 'ltfs' or source == 'vd':
            manageTape = {'source': source}
            tapes = int(request.forms.get("tapes"))
            manageTape['data'] = []
            for i in range(0, tapes):
                hold = request.forms.get("tape" + str(i))
                if hold != '':
                    manageTape['data'].append([])
                    manageTape['data'][rowCount] = list(hold.split('|'))
                    rowCount += 1
            isFileMangerUp = common.filemanageralive()

            if isFileMangerUp == "Down":
                dict = {'error': 2,
                        'errormsg': 'File Manager Down. Start File Manager to process tape mangement requests.'}

            elif rowCount > 0:
                dict = common.addTapeCmdsToQueue(manageTape)

            else:
                dict = {'error': 2, 'errormsg': 'No tape management commands provided.'}
        else:
            dict = {'error': 1, 'errormsg': 'Invalid data set passed to manage tapes.'}
    dict['source'] = source
    return dict


@route('/tapequeue', method='POST')
def tapequeue():
    """return info on tape queue"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    extra = request.forms.get("extra")
    if dict["error"] == 0:
        dict = common.tapeQueueList(extra)
    dict['extra'] = extra
    return dict


@route('/submitCancelTapes', method='POST')
def submitCancelTapes():
    """return comands in tape queue"""
    extra = request.forms.get("exta")
    dict = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    manageTape = {}
    rows = int(request.forms.get("row"))
    if dict["error"] == 0:
        manageTape['data'] = []
        rowCount = 0
        for i in range(0, rows):
            hold = request.forms.get("id" + str(i))
            if hold != '' and hold != None:
                manageTape['data'].append(hold)
                rowCount += 1
        if rowCount > 0:
            dict = common.cancelTapeCmds(manageTape)
        else:
            dict = {'error': 2, 'errormsg': 'No tape management cancellations provided.'}
    dict['extra'] = extra
    return dict


@route('/storagestats')
def storagestats():
    """return ltfsadmin -X -i"""
    dict = common.ltfsAdminCmd('cartridge', 'leadm tape list -o xml')
    dict['diskfree'] = common.cacheFreespace()
    return dict


@route('/dbtree', method='POST')
def dbtree():
    """update properties"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if dict["error"] == 0:
        dict = common.directoryList(int(request.forms.get("dirId")))
    return dict


@route('/filecopyinfo', method='POST')
def filecopyinfo():
    """update properties"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if dict["error"] == 0:
        dict = common.getFileCopyInfo(int(request.forms.get("fileId")))
    return dict


@route('/submitrestorefile', method='POST')
def submitrestorefile():
    """return comands in tape queue"""
    extra = request.forms.get("exta")
    dict = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    rows = int(request.forms.get("rows"))
    if dict["error"] == 0:
        files = []
        rowCount = 0
        for i in range(0, rows):
            hold = request.forms.get("file" + str(i))
            if hold != '' and hold != None:
                files.append(hold)
                rowCount += 1
        if rowCount > 0:
            dict = common.restoreFiles(files)
        else:
            dict = {'error': 2, 'errormsg': 'No files to restore provided.'}
    return dict


@route('/restorequeue', method='POST')
def restorequeue():
    """return info on restore queue"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    extra = request.forms.get("extra")
    if dict["error"] == 0:
        dict = common.restoreQueueList(extra)
    dict['extra'] = extra
    return dict


@route('/submitcancelrestore', method='POST')
def submitcancelrestore():
    """cancel restore request"""
    extra = request.forms.get("exta")
    dict = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    manageRestore = {}
    rows = int(request.forms.get("row"))
    print(rows)
    if dict["error"] == 0:
        manageRestore['data'] = []
        for i in range(0, rows):
            hold = request.forms.get("id" + str(i))
            if hold != '' and hold != None:
                manageRestore['data'].append(hold)
        if len(manageRestore['data']) > 0:
            dict = common.cancelRestoreCmds(manageRestore)
        else:
            dict = {'error': 2, 'errormsg': 'No tape management cancellations provided.'}
    dict['extra'] = extra
    return dict


@route('/filesearch', method='POST')
def filesearch():
    """file search"""
    dict = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    if dict["error"] == 0:
        data = {}
        data["file"] = request.forms.get("file")
        data["directory"] = request.forms.get("directory")
        dict = common.fileSearch(data)
    return dict


@route('/totapequeue')
def totapequeue():
    """return info on to tape queue"""
    dict = common.toTapeQueue()
    return dict


@route('/fileMoveLog')
def totapequeue():
    """return info in file move lof"""
    dict = common.fileMoveLog()
    return dict


@route('/cleardiskqueue')
def cleardiskqueue():
    """return info on clear disk queue"""
    dict = common.clearDiskQueue()
    return dict


@route('/foldercopyinfo', method='POST')
def foldercopyinfo():
    """update properties"""
    dict = common.validateLogin(request.forms.get("adminName"), request.forms.get("adminPassword"))
    if dict["error"] == 0:
        dict = common.getFolderCopyInfo(int(request.forms.get("dirId")))
    return dict


@route('/runFileManager', method='POST')
def run_file_manager():
    try:
        # Call the function directly and get the return code
        return_code = resetFMTimer()

        response.content_type = 'application/json'

        if return_code == 1:
            msg = "File Manager Reset"
            error = 0
        elif return_code == 0:
            msg = "File Manager Not Running or Busy"
            error = 0  # Or a different error code if you want to distinguish this case
        elif return_code == -1:
            msg = "An error occurred in the File Manager"
            error = 1
        else:
            msg = "Unexpected return code from resetFMTimer."
            error = 1

        return json.dumps({"error": error, "msg": msg, "return_code": return_code})

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        response.content_type = 'application/json'
        return json.dumps({"error": 1, "msg": "Failed to run File Manager now.", "return_code": -1})


import json
from bottle import route, response
import common  # Assuming common.py contains the process_recent_logs function


@route('/process_logs', method='POST')
def process_logs_route():
    """
    Bottle route to run the process_recent_logs function from common.py
    and return the result to the client.
    """
    try:
        # Call the function from common.py
        return_message = common.process_recent_logs()

        response.content_type = 'application/json'

        # Process the return message
        if return_message == "success":
            return json.dumps({"error": 0, "msg": "Log data processed and loaded successfully.", "return_message": "success"})
        elif return_message == "log_file_not_found":
            return json.dumps({"error": 1, "msg": "Log file not found.", "return_message": "log_file_not_found"})
        elif return_message == "error_reading_log":
            return json.dumps({"error": 1, "msg": "Error reading the log file.", "return_message": "error_reading_log"})
        elif return_message == "error_parsing_log":
            return json.dumps({"error": 1, "msg": "Error parsing log entries.", "return_message": "error_parsing_log"})
        elif return_message == "error_writing_json":
            return json.dumps({"error": 1, "msg": "Error writing to JSON file.", "return_message": "error_writing_json"})
        elif return_message == "error_creating_json":
            return json.dumps({"error": 1, "msg": "Error creating empty JSON file.", "return_message": "error_creating_json"})
        else:
            return json.dumps({"error": 1, "msg": "An unexpected error occurred.", "return_message": "unknown_error"})

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        response.content_type = 'application/json'
        return json.dumps({"error": 1, "msg": f"Failed to process logs: {e}", "return_message": "Exception occurred"})





from bottle import route, request, HTTPError, response



@route('/filesearchbydate', method='POST')
def do_filesearchbydate():
    """Handles AJAX requests for file search by date."""

    # --- 1. Get parameters from the request ---
    filename = request.forms.get('filename')
    start_date_str = request.forms.get('start_date')  # Get as string
    end_date_str = request.forms.get('end_date')    # Get as string

    # --- 2. Validate Input (Basic) ---
    # It's good practice to validate *all* input, even if you have client-side
    # validation.  This is a minimal example; add more as needed.
    if filename and len(filename) > 255:  # Example validation
        return HTTPError(400, "Filename too long.")

    # --- 3. Convert Dates (mm/dd/yyyy to yyyy-mm-dd) ---
    start_date = None  # Initialize to None
    end_date = None    # Initialize to None

    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
    except ValueError:
        return HTTPError(400, "Invalid date format. Use mm/dd/yyyy.")

    # --- 4. Build search_criteria dictionary ---
    search_criteria = {}  # Initialize as empty dictionary
    if filename:
        search_criteria['filename'] = filename
    if start_date:
        search_criteria['start_date'] = start_date  # yyyy-mm-dd
    if end_date:
        search_criteria['end_date'] = end_date      # yyyy-mm-dd

    # --- 5. Call common.fileSearchDates ---
    results = common.fileSearchDates(search_criteria)

    # --- 6. Handle Results and Return JSON ---
    if results['error'] == 0:
        response.content_type = 'application/json'
        return json.dumps(results)  # Return the ENTIRE results dictionary
    else:
        # It's good practice to return JSON errors, even with HTTP error codes.
        response.content_type = 'application/json'
        return json.dumps(results) # Return ENTIRE result dictionary.
        #return HTTPError(500, results['errormsg']) # Return the error


from bottle import route, request, post, response, HTTPError
import json
import common  # Assuming your common functions are in a module named 'common'


@post('/submitrestorefiledates')
def submit_restore_file_dates():
    """Handles file restoration requests from the date-based search form."""

    # --- 1. Authentication (Using your existing pattern) ---
    dict_creds = common.validateLogin(request.forms.get("adminName1"), request.forms.get("adminPassword1"))
    if dict_creds["error"] != 0:
        response.content_type = 'application/json'
        return json.dumps(dict_creds)  # Return the error from validateLogin

    # --- 2. Get and Parse the Data (Corrected) ---
    files = []
    rows = int(request.forms.get('rows', 0))  # Get row count, default to 0
    for i in range(rows):
        file_data_str = request.forms.get(f'file{i}')
        if file_data_str and file_data_str != "":  # Check if value was provided AND is not empty
            file_data = file_data_str.split('|')
            # file_data[0] is fileID
            # file_data[1] is fileName
            # file_data[2] is tapeUID
            # file_data[3] is RestoreLocation

            # --- FIX: Construct the string in the CORRECT format ---
            files.append('|'.join(file_data)) #Recombine the split string

    # --- 3. Database Interaction (Using your existing common.restoreFiles) ---
    if files:  # Check if the files list is not empty
        dict_result = common.restoreFiles(files)  # Call your common function!
        response.content_type = 'application/json'
        return json.dumps(dict_result)  # Return ENTIRE result dictionary
    else:
        response.content_type = 'application/json'
        return json.dumps({'error': 2, 'errormsg': 'No files to restore provided.'})
