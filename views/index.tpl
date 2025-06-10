<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EchoLeaf Management System</title>
    <link rel="stylesheet" type="text/css" href="/static/content/bootstrap.min.css" />
    <link rel="stylesheet" type="text/css" href="/static/content/site.css" />
    <link rel="stylesheet" type="text/css" href="/static/content/jqueryFileTree.css" />
    </head>

<body>

    <nav class="navbar navbar-inverse" style="background-color:Black; border-radius:0px;">
        <div class="container-fluid" style="background-color: Black">
            <div class="navbar-header">
                <a class="navbar-brand" href="#">EchoLeaf</a>
            </div>
            <div>
                <ul class="nav navbar-nav">
                    <li id="menuSystem" class="dropdown" style="display:none">
                        <a class="dropdown-toggle" data-toggle="dropdown" href="#">System<span class="caret"></span></a>
                        <ul class="dropdown-menu">
                            <li><a href="#" onclick="displayDashBoard();">Dashboard</a></li>
                            <li><a href="#" onclick="properytable();">View EchoLeaf Properties</a></li>
                            <li><a href="#" onclick="buildPropertyForm();">Update EchoLeaf Properties</a></li>
                            <li><a href="#" onclick="vdStartStop();">Virtual Drive Start/Stop</a></li>
                            <li><a href="#" onclick="fmStartStop();">File Manager Start/Stop</a></li>
                            <li><a href="#" onclick="totapequeuetable();">Files Queued for Tape Archive</a></li>
                            <li><a href="#" onclick="cleardiskqueuetable();">Files Queued for Cache Cleanup</a></li>
                        </ul>
                    </li>
                    <li id="menuLTFSLE" class="dropdown" style="display:none">
                        <a class="dropdown-toggle" data-toggle="dropdown" href="#">LTFS<span class="caret"></span></a>
                        <ul class="dropdown-menu">
                            <li><a href="#" onclick="vdStatusTapes();">Status Tapes</a></li>
                            <li><a href="#" onclick="vdManageTapes();">Manage Tapes</a></li>
                            <li><a href="#" onclick="tapeQueue('Queued');">Manage Tape Queue</a></li>
                            <li><a href="#" onclick="ltfsStatusDrives();">Status Drives</a></li>
                        </ul>
                    </li>
                    <li id="menuVirtualDrive" class="dropdown" style="display:none">
                        <a class="dropdown-toggle" data-toggle="dropdown" href="#">Restore<span
                                class="caret"></span></a>
                        <ul class="dropdown-menu">
                            <li><a href="#" onclick="vdFastTrack();">Fast Track Cache</a></li>
                            <li><a href="#" onclick="dbdirectory();">Explore/Restore Folders/Files</a></li>
                            <li><a href="#" onclick="buildFileSearchForm();">File Search</a></li>
                            <li><a href="#" onclick="buildFileSearchFormDates();">File Search By Date</a></li>
                        </ul>
                    </li>
                    <li id="menuLogin"><a href="#" onclick="displayLogin()">Login</a></li>
                    <li id="menuLogout" style="display:none"><a href="#" onclick="logout();">Logout</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container body-content">

        <div id="sectionIntro">  <div class="jumbotron" style="background-color: #ECEDD1">
                <div style="float: left"><img src="static/images/newlogo.png" /></div>
                <div><p>&nbsp;</p><p>&nbsp;</p></div>
            </div>

            <div class="row">
                <div class="col-sm-12">
                    <h2>Getting started</h2>
                    <p>This browser based utility provides easy to use tools for:</p>
                    <ul>
                        <li>Managing your EchoLeaf System</li>
                        <li>Managing your LTFS Library</li>
                        <li>Reporting</li>
                    </ul>
                    <p><button type="button" class="btn btn-primary btn-md" onclick="displayLogin()">login</button></p>
                </div>
            </div>
        </div>

        <div id="sectionLogin" class="wrapper" style="display:none">
            <form id="login_form" class="form-signin" onsubmit="return validateLogin(this)">
                <input id="extra" name="extra" type="hidden" value="" />
                <h2 class="form-signin-heading"><img src="static/images/smalllogo.jpg" />Please Login</h2>
                <br>
                <input type="text" class="form-control" name="adminName" id="adminName" placeholder="User Name" required=""
                    autofocus="" />
                <br>
                <input type="password" class="form-control" name="adminPassword" id="adminPassword" placeholder="Password"
                    required="" />
                <br>
                <button class="btn btn-lg btn-primary btn-block" type="submit">Login</button>
                <br>
                <p class="text-danger" id="login_error"></p>
            </form>
        </div>

        <div id="sectionDashboard" style="display:none">
            <div class="row">
                <div class="col-sm-12">
                    <h2>System Dashboard</h2>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-6">
                    <div id="dashboard_active">
                        <table class="table">
                            <tr>
                                <td class="text-left">Mount Uptime:</td>
                                <td id="vdUptime" class="text-right"></td>
                            </tr>
                            <tr>
                                <td class="text-left">File Manager Uptime:</td>
                                <td id="fmUptime" class="text-right"></td>
                            </tr>
                        </table>
                        <table class="table" id="fm-timer-table">
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
                                <td class="text-right"><button id="runFileManagerButton"
                                        class="btn btn-success">Cycle File Manager Now</button></td>
                            </tr>
                            <tr>
                                <td class="text-left">Process Status:</td>
                            </tr>
                            <tr>
                                <td colspan="2" id="fmProcessStatus" class="text-center"></td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="col-sm-6">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Storage Statistics</th>
                                <th>Value</th>
                            </tr>
                            <tr>
                                <td>Formatted Tapes</td>
                                <td id="formattedTapes">&nbsp;</td>
                            </tr>
                            <tr>
                                <td>Tape Total Space (GB)</td>
                                <td id="tapeTotalSpace">&nbsp;</td>
                            </tr>
                            <tr>
                                <td>Tape Used Space (GB)</td>
                                <td id="tapeUsed">&nbsp;</td>
                            </tr>
                            <tr>
                                <td>Tape Percent Used</td>
                                <td id="tapePercentUsed">&nbsp;</td>
                            </tr>
                            <tr>
                                <td>Disk Cache Free Space (GB)</td>
                                <td id="cachefreespace">&nbsp;</td>
                            </tr>
                        </thead>
                    </table>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-12" id="simpleTaskLog"></div>
            </div>
            <div class="row">
                <div class="col-sm-12">
                    <p><button type="button" class="btn  btn-primary btn-md"
                            onclick="displayDashBoard();">Refresh</button></p>
                </div>
            </div>
        </div>

        <div id="sectionDBTree" style="display:none">
            <div class="row">
                <div class="col-sm-12">
                    <h2>Explore/Restore Folders/Files</h2>
                    <p>To collapse and expand a folder listing, click the folder. To restore a folder, press the shift
                        key and click the folder. To restore a file, click file.</p>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-4">
                    <h4>Database Folder/File Listing</h4>
                    <div id="db_directory" class="small"></div>
                </div>
                <div class="col-sm-1">&nbsp;</div>
                <div class="col-sm-7">
                    <h4>Restore to Disk Folder/File List</h4>
                    <div id="move_list" class="small"></div>
                </div>
                <div class="col-sm-1">&nbsp;</div>
            </div>
        </div>
        <div id="sectionFileSearch" style="display:none">
            <div class="row">
                <div class="col-sm-12">
                    <h2>File Search</h2>
                    <form id="fileSearchForm" name="fileSearchForm" method="post">
                        <div class="form-group">
                            <label for="fileSearchForm_filename">Filename:</label>
                            <input type="text" class="form-control" id="fileSearchForm_filename" name="filename">
                        </div>
                        <div class="form-group">
                            <label for="path">Path:</label>
                            <input type="text" class="form-control" id="path" name="path">
                        </div>
                        <button type="button" class="btn btn-primary" onclick="validateFileSearch();">Search</button>
                    </form>
                    <div id="search_results"></div>
                </div>
            </div>
        </div>
        <div id="sectionFileSearchDates" style="display:none">
            <div class="row">
                <div class="col-sm-12">
                    <h2>File Search By Date</h2>
                    <p>Enter a full or partial file name.  Enter beginning and end dates for the search.  Select "Search" to return a list of matching files.</p>
                    <form id="fileSearchFormDates" name="fileSearchFormDates" method="post" class="form-horizontal">
                        <div class="form-group row">
                            <label for="fileSearchFormDates_filename" class="col-sm-2 col-form-label">Filename:</label>
                            <div class="col-sm-10">
                                <input type="text" class="form-control" id="fileSearchFormDates_filename" name="filename">
                            </div>
                        </div>
                        <div class="form-group row">
                            <label for="start_date" class="col-sm-2 col-form-label">Date Range:</label>
                            <div class="col-sm-4">
                                <input type="text" class="form-control" id="start_date" name="start_date" autocomplete="off" placeholder="Start Date (mm/dd/yyyy)">
                            </div>
                            <div class="col-sm-4">
                                <input type="text" class="form-control" id="end_date" name="end_date" autocomplete="off" placeholder="End Date (mm/dd/yyyy)">
                            </div>
                            <div class="col-sm-2">
                                <button type="button" class="btn btn-primary" onclick="validateFileSearchDates();">Search</button>
                            </div>
                        </div>
                    </form>
                    <div id="search_results_dates"></div>
                </div>
            </div>
        </div>
        <div id="sectionSimpleTask" style="display:none">
        </div>

        <hr />
        <footer>
            <p><small>© {{ year }} - EchoLeaf Systems&nbsp;&nbsp;/v1.5c</small></p>
        </footer>

        <div class="modal fade" id="myModal" role="dialog">
            <div class="modal-dialog modal-sm">
                <div class="modal-content">
                    <div id="modalHeader" class="modal-header"></div>
                    <div id="modalBody" class="modal-body"></div>
                    <div id="modalFooter" class="modal-footer"></div>
                </div>
            </div>
        </div>

    </div>
    <script src="//cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <script src="/static/scripts/jquery-1.10.2.min.js"></script>
    <script src="/static/scripts/bootstrap.min.js"></script>
    <script src="/static/scripts/respond.min.js"></script>
    <script src="/static/scripts/modernizr-2.6.2.js"></script>
    <script src="/static/scripts/site.js"></script>
    <script src="/static/scripts/vd.js"></script>
    <script src="/static/scripts/ltfs.js"></script>
    <script src="/static/scripts/vdtree.js?v=1"></script>
</body>
</html>
