var reports = (function () {
    return {};
}());

reports.boundary = '------------86753098675309'
reports.authorized = false;

reports._handle_auth = function (auth_result) {
    reports.auth_result = auth_result;
    console.log({'reports._handle_auth': auth_result});
    if (auth_result && !auth_result.error) {
        reports.authorized = true;
    } else {
        reports.authorized = false;
        info = {
            'client_id': reports.client_id,
            'scope': 'https://www.googleapis.com/auth/drive',
            'immediate': false,
        };
        console.log({'reports.auth': info});
        gapi.auth.authorize(info, reports._handle_auth);
    };
};

reports.client_id = '';

reports.auth = function (callback) {
    info = {
        'client_id': reports.client_id,
        'scope': 'https://www.googleapis.com/auth/drive',
        'immediate': true,
    };
    console.log({'reports.auth': info});
    if (!callback) {
        cb = reports._handle_auth;
    } else {
        cb = function (auth_result) {
            reports._handle_auth(auth_result);
            if (reports.authorized) {
                callback();
            } else {
                console.log('failed to authorize, skipping callback');
            };
        };
    };
    gapi.auth.authorize(info, cb);
};

reports._generate = function (client) {
    // convert client to base64data
    //base64data = client;
    s = "<html><head></head><body>Hello World!</body></html>";
    //s = document.documentElement.innerHTML;
    //s = '<html><head></head><body>' + $('svg').get(0).parentNode.innerHTML + '</body></html>';
    //s = $('svg').get(0).parentNode.innerHTML;
    base64data = btoa(s);
    report = "";
    // header
    report += '\r\n--' + reports.boundary + '\r\n';
    report += 'Content-Type: application/json\r\n\r\n';
    report += JSON.stringify({
        'title': 'test',
        'mimeType': 'text/html',
        //'convert': true,
    });
    // body
    report += '\r\n--' + reports.boundary + '\r\n';
    report += 'Content-Type: text/html\r\n';
    report += 'Content-Transfer-Encoding: base64\r\n\r\n';
    report += base64data;
    // footer
    report += '\r\n--' + reports.boundary + '--';
    return report;
};

reports.post_callback = function (file, raw) {
    console.log({'reports.post_callback': file, 'raw': raw});
};

reports._post_report = function (report) {
    request = gapi.client.request({
        'path': '/upload/drive/v2/files',
        'method': 'POST',
        'params': {
            'uploadType': 'multipart',
            'convert': true,
        },
        'headers': {
            'Content-Type': 'multipart/mixed; boundary="' + reports.boundary + '"',
        },
        'body': report,
    });
    console.log({'_post_report': request});
    request.execute(reports.post_callback);
};

reports._post = function (report) {
    console.log({'reports.post': report});
    gapi.client.load('drive', 'v2', function () {
        reports._post_report(report);
    });
};

reports.report = function (client) {
    if (!reports.authorized) {
        reports.auth(function () {
            reports.report(client);
        });
        return;
    }; 
    // generate port
    /*
    html2canvas(document.body, {onrendered: function (canvas) {
        s = canvas.toDataURL();
        reports._post(reports._generate(s.slice(s.indexOf(',') + 1, s.length)));
        //reports._post(reports._generate(canvas.toDataURL()));
        }
    });
    */
    // post report
    reports._post(reports._generate(client));
};
