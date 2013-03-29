var reports = (function () {
    return {};
}());

reports.boundary = '------------86753098675309'
reports.authorized = false;

reports._handle_auth = function (auth_result) {
    if (auth_result && !auth_result.error) {
        reports.authorized = true;
    } else {
        reports.authorized = false;
    };
};

reports.auth = function () {
    info = {
        'client_id': CLIENT_ID,
        'scope': 'https://www.googleapis.com/auth/drive',
        'immediate': true,
    };
    gapi.auth.authorize(info, reports.handle_auth);
};

reports.generate = function (client) {
    // convert client to base64data
    s = "";
    base64data = btoa(s);
    report = "";
    // header
    report += '--' + reports.boundary + '\r\n';
    report += 'Content-Type: application/json\r\n\r\n';
    report += JSON.stringify({
        'title': 'TITLE',
        'mimeType': 'text/html',
    });
    // body
    report += '--' + reports.boundary + '\r\n';
    report += 'Content-Type: text/html\r\n';
    report += 'Content-Transfer-Encoding: base64\r\n\r\n';
    report += base64data;
    // footer
    report += '\r\n--' + reports.boundary + '--';
    return report;
};

reports.post_callback = function (file) {
    console.log({'report posted': file});
};

reports._post_report = function (report) {
    request = gapi.client.request({
        'path': '/upload/drive/v2/files',
        'method': 'POST',
        'params': {'uploadType': 'multipart'},
        'headers': {
            'Content-Type': 'multipart/mixed; boundary="' + reports.boundary + '"',
        },
        'body': report,
    });
    request.execute(reports.post_callback);
};

reports.post = function (report) {
    gapi.client.load('drive', 'v2', function () {
        reports._post_report(report);
    };
};
