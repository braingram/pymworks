var reports = (function () {
    return {};
}());

reports.url = '/report';
reports.spreadsheet = '';
reports.worksheet = 'od6';

//reports.vars = ['phases_completed', 'criterion_count', 'curr_performance', 'correct_lick', 'bad_lick', 'correct_ignore', 'bad_ignore', 'targetprob'];
reports.vars = [];

reports.parse_vars = function (d, client) {
    for (i in reports.vars) {
        vn = reports.vars[i];
        try {
            d[vn] = '' + client.varbyname(vn).latest_value();
        } catch (error) {
            d[vn] = '' + error;
        };
    };
};

reports.parse_graphs = function (d, client) {
    for (gi in client.graphs) {
        gd = client.graphs[gi].data;
        for (ki in gd) {
            d[gd[ki]['key'] + '_ref'] = '' + gd[ki]['ref']
        };
    };
};

reports.parse_messages = function (messages) {
    s = '';
    for (i in messages) {
        s += messages[i].stype + ':' + messages[i].message + '\n';
    };
    return s;
};

reports.parse_notes = function (notes) {
    s = '';
    for (i in notes) {
        s += notes[i] + '\n';
    };
    return s;
};

reports.generate = function (client) {
    d =  {};
    if ('animal' in client.config) {
        d['animal'] = client.config['animal'];
    };
    d['host'] = '' + client.host();
    d['user'] = '' + client.user();
    d['experiment_path'] = '' + client.experiment_path();
    if ((client.datafile() === "") & ('datafile' in client.config)) {
        d['datafile'] = '' + client.config['datafile'];
    } else {
        d['datafile'] = '' + client.datafile();
    };
    d['variableset'] = '' + client.variableset();
    // d['messages'] = '' + reports.parse_messages(client.messages());
    d['notes'] = '' + reports.parse_notes(client.notes());
    // host
    // experiment_path
    // datafile
    // variableset
    // messages
    //
    reports.parse_vars(d, client);
    // phases_completed
    // criterion_count
    // curr_performance
    // correct_lick
    // bad_lick
    // correct_ignore
    // bad_ignore
    // targetprob
    //
    reports.parse_graphs(d, client);
    // correct_lick_ref
    // bad_lick_ref
    // correct_ignore_ref
    // bad_ignore_ref
    return d;
};

reports.post_callback = function (a, b, c) {
    console.log({'a': a, 'b': b, 'c': c});
};

reports.post = function (report) {
    $.ajax({
        'url': reports.url,
        'data': {
            'worksheet': reports.worksheet,
            'spreadsheet': reports.spreadsheet,
            'data': JSON.stringify(report),
        },
    }).always(reports.post_callback);
};

reports.report = function (client) {
    reports.post(reports.generate(client));
};
