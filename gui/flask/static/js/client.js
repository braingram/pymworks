/*
 * This exposes a global mworks object
 */
var mworks = (function () {
    return {};
}());

mworks.utils = (function ($) {
    var utils = {};

    utils.array_equal = function (a, b) {
        return $(a).not(b).length == 0 && $(a).not(b).length == 0
    };

    id_index = 0;

    utils.get_id = function () {
        id = id_index;
        id_index += 1;
        return id;
    };

    utils.objects_equal = function (a, b) {
        if (Object.keys(a).length != Object.keys(b).length) {
            return false;
        };
        for (k in a) {
            if (!b.hasOwnProperty(k)) {
                return false;
            };
            if ((typeof(a[k]) == 'object') & (typeof(b[k]) == 'object')) {
                if (!utils.objects_equal(a[k], b[k])) {
                    return false;
                };
            } else {
                if (a[k] != b[k]) {
                    return false;
                };
            };
        };
        return true;
    };

    utils.find_most_recent = function (a, test) {
        if (a.length === 0) {
            return null;
        };
        if (test) {
            a = a.filter(test);
        };
        if (a.length === 0) {
            return null;
        };
        a.sort();
        return a[a.length - 1];
    };

    utils.make_filename = function (animal, suffix) {
        if (!suffix) {
            suffix = '';
        };
        d = new Date();
        y = d.getFullYear() - 2000;
        m = d.getMonth() + 1;
        d = d.getDate();
        return animal + '_' + (y < 10 ? '0' : '' ) + y + (m < 10 ? '0' : '') + m + (d < 10 ? '0' : '') + d + suffix;
    };

    utils.nan_test = function (v) {
        switch (typeof(v)) {
            case 'number':
                return isNaN(v);
            case 'string':
                return (v == 'NaN');
            default:
                return false;
        };
    };

    utils.match_type = function (a, b) {
        //return a;
        // try to convert a to type b
        if (b == null) {  // cannot cast a to null
            return a;
        };
        if (typeof(b) == 'string') {
            return String(a);
        };
        if (typeof(b) == 'number') {
            v = Number(a);
            if ((v == a) | (utils.nan_test(v) & utils.nan_test(a))) {
                return v;
            };
            throw "Matching error: could not convert " + a + " to " + typeof(b);
            return undefined;
        };
        if (typeof(b) == 'object') {
            return a;
            /*
            if (typeof(a) == 'string') {
                return io.JSON.parse(a);
            };
            */
        };
        return a;
    };

    return utils;
}(jQuery));


mworks.graph = function (client, vars, type) {
    var graph = this;
    graph.vars = vars;
    graph.type = type;
    graph.client = client;
    graph.data = [];
    //graph.updating = false;

    //graph.gid = null;
    graph.chart = null;

    graph.build = function () {
        // setup data
        for (i in vars) {
            graph.data.push({'key': vars[i], 'values': [], 'ref': 0});
            client.varbyname(vars[i]).n = 100;
        };

        // build chart
        switch (graph.type) {
            case 'stacked':
                graph.chart = nv.models.stackedAreaChart()
                    .x(function(d) { return d[0] })
                    .y(function(d) { return d[1] });
                graph.chart.xAxis.tickFormat(d3.format('i'));
                graph.chart.yAxis.tickFormat(d3.format('i'));
                break;
            default:
                throw "Unknown graph type: " + graph.type;
                break;
        };
        //redraw();
        nv.utils.windowResize(graph.chart.update);
    };

    graph.build();

    graph.getvalue = function (di, index, with_ref) {
        if (index >= graph.data[di]['values'].length) {
            v = graph.data[di]['values'][graph.data[di]['values'].length - 1];
            r = false;
        } else {
            v = graph.data[di]['values'][index];
            r = true;
        };
        if (with_ref) {
            return [r, [v[0], v[1] - graph.data[di]['ref']]];
        } else {
            return [r, v];
        };
    };

    graph.order_data = function (with_ref) {
        // copy data
        mi = 0;
        inds = {};
        cvs = {};
        for (i in graph.data) {
            vn = graph.data[i]['key']
            vs = [];
            v = graph.client.varbyname(vn);
            evs = v.events();
            for (vi in evs) {
                // TODO value checking
                vs.push([evs[vi].time, evs[vi].value]);
            };
            vs.sort(function(a, b) { return a[0] - b[0]; });
            graph.data[i]['values'] = vs;
            mi = Math.max(mi, vs.length);
            //inds[graph.data[i]['key']] = 0;
            inds[i] = 0;
            cvs[i] = [];
        };
        // prep data
        alldone = false;
        rs = {};
        values = {};
        while (!alldone) {
            // get values for all data
            mt = Infinity;
            mdi = 0;
            for (di in inds) {
                r = graph.getvalue(di, inds[di], with_ref);
                rs[di] = r[0];
                values[di] = r[1];
                // find one with lowest time
                if ((r[1][0] < mt) && (r[0])) {
                    mt = r[1][0];
                    mdi = di;
                };
            };
            alldone = true;
            for (i in rs) {
                alldone = alldone && (!rs[i]);
            };
            if (alldone) {
                break;
            };
            // match all others to that
            for (di in inds) {
                cvs[di].push([mt, values[di][1]]);
            };
            // increment that time for that one
            inds[mdi] += 1;
            alldone = true;
            for (i in rs) {
                alldone = alldone && (!rs[i]);
            };
        };

        for (di in cvs) {
            graph.data[di]['values'] = cvs[di];
            graph.data[di]['values'].sort(function(a, b) { return a[0] - b[0] });
        };
    };

    graph.redraw = function (with_ref) {
        graph.order_data(with_ref);
        d3.select('#chart')
            .datum(graph.data)
          .transition().duration(500);
            //.call(graph.chart);
        graph.chart.update();
    };
    
    graph.start = function () {
        graph.order_data();
        d3.select('#chart')
            .datum(graph.data)
          .transition().duration(500)
            .call(graph.chart);
    };

    /*
    graph.start = function () {
        graph.order_data();
        d3.select('#chart')
            .datum(graph.data)
          .transition().duration(500)
            .call(graph.chart);
        graph.gid = window.setInterval(graph.redraw, 1000);
        graph.updating = true;
    };

    graph.stop = function () {
        window.clearInterval(graph.gid);
        graph.updating = false;
    };
    */

    return graph;
};


mworks.variable = function (name, send_event) {
    var variable = this;
    variable.name = ko.observable(name);
    variable.events = ko.observableArray();
    variable.n = 1;

    variable.latest_value = ko.computed({
        read: function () {
            return variable.events().length ? variable.events()[variable.events().length - 1].value : null;
        },
        write: function (value) {
            try {
                value = mworks.utils.match_type(value, variable.latest_value());
                send_event(variable.name(), value);
            } catch (error) {
                console.log(error);
                // reset value, but don't send
                variable.latest_value.notifySubscribers()
            };
        },
        owner: this
    });

    variable.latest = ko.computed({
        read: function () {
            return variable.events().length ? variable.events()[variable.events().length - 1] : {value: null};
        },
        write: function (value) {
            try {
                value = mworks.utils.match_type(value, variable.latest_value());
                send_event(variable.name(), value);
            } catch (error) {
                console.log(error);
                // reset value, but don't send
                variable.latest_value.notifySubscribers()
            };
        },
        owner: this
    });

    variable.add_event = function (event) {
        variable.events.push(event);
        while (variable.events().length > variable.n) {
            variable.events.shift();
        };
    };

    //variable.incrementing = ko.computed(function () ...

    return variable;
};

mworks.message = function (event) {
    var message = {};
    message.time = event.time;

    if (typeof(event.value) !== 'object') {
        console.log({'Badly formed message': event.value});
        event.value = {};
    };
    
    stypes = {
        0: 'Invalid',
        1: 'Generic',
        2: 'Warning',
        3: 'Error',
        4: 'Fatal',
    };

    colors = {
        0: 'black',
        1: 'green',
        2: 'orange',
        3: 'red',
        4: 'red',
    };

    message.type = ('type' in event.value ? event.value['type'] : -1);
    ti = message.type + 1;
    message.stype = (ti in stypes ? stypes[ti] : 'Unknown');
    message.color = (ti in colors ? colors[ti] : 'red');
    message.origin = ('origin' in event.value ? event.value['origin'] : 0);
    message.domain = ('domain' in event.value ? event.value['domain'] : 0);
    message.message = ('message' in event.value ? event.value['message'] : '');

    return message;
};

mworks.client = (function () {
    /*
     * Add listeners for:
     * - protocol (for protocol selection)
     * - variables (for variables selection)
     */
    var client = {};
    client.id = mworks.utils.get_id();
    client.socket = null;
    client.config = {};

    client.user = ko.observable('');

    client.graphs = [];
    client.graph_ref = ko.observable(true);

    client.state = ko.observable(undefined);

    client.notes = ko.observableArray();
    client.messages = ko.observableArray();
    client.max_messages = ko.observable(50);
    client.message_verbosity = ko.observable(0);
    client.message_error_verbosity = ko.observable(1);

    client.host = ko.observable("");
    client.port = ko.observable(19989);
    client.user = ko.observable("");
    client.startserver = ko.observable(false);
    
    client.experiment_path = ko.observable("");
    client.experiment_name = ko.observable("");
    
    client.variableset = ko.observable("");
    client.variableset_overwrite = ko.observable(false);
    client.variablesets = ko.observableArray();

    client.datafile = ko.observable("");
    client.datafile_overwrite = ko.observable(false);
    client.datafile_saving = ko.observable(false);
    client.datafile_saving_verbose = ko.computed(function () {
        return client.datafile_saving() ? "Saving" : "Not Saving";
    });

    client.protocol = ko.observable("");
    client.protocols = ko.observableArray();
    
    client.connected = ko.observable(false);
    client.toggle_connect_label = ko.computed(function () {
        return client.connected() ? "Disconnect" : "Connect";
    });
    client.connected_verbose = ko.computed(function () {
        return client.connected() ? "Connected" : "Not Connected";
    });
    client.socket_connected = ko.observable(false);
    client.socket_connected_verbose = ko.computed(function () {
        return client.socket_connected() ? "Connected" : "Not Connected";
    });

    client.running = ko.observable(false);
    client.toggle_running_label = ko.computed(function () {
        return client.running() ? "Stop" : "Start";
    });
    client.paused = ko.observable(false);
    client.toggle_paused_label = ko.computed(function () {
        return client.paused() ? "Resume" : "Pause";
    });
    client.loaded = ko.observable(false);

    client.vars = ko.observableArray();
    client.variable_groups = {};
    client.codec = {};
    client.unstored_events = [];

    client.bindings = {};

    client.apply_binding = function (selector) {
        if (selector in client.bindings) {
            // remove binding
            $(selector).unbind('*'); // unbinds ALL events
            ko.cleanNode($(selector).get(0));
        };
        // apply binding
        ko.applyBindings(client, $(selector).get(0));
        client.bindings[selector] = true;
    };

    client.bind_variables = function (selector) {
        $(selector).each( function(index) {
            node = $(this).get(0);
            vb = node.attributes['var-bind'];
            if (vb.value.indexOf(':') === -1) {
                bt = 'value';
                vn = vb.value;
            } else {
                tokens = vb.value.split(':');
                bt = tokens[0];
                vn = tokens[1];
            };
            // check if bt has associated value
            if (bt.indexOf('=') === -1) {
                bv = 'client.varbyname("' + vn + '").latest_value()';
            } else {
                tokens = bt.split('=');
                bt = tokens[0];
                bv = tokens[1];
            };
            switch (bt) {
                case 'value':
                    $(this).attr('data-bind', "with: client.varbyname('" + vn + "')");
                    node.innerHTML = "<input class='control_input' value='' title='" + vn + "' data-bind='value: latest_value'/>" + node.innerHTML;
                    break;
                case 'check':
                    $(this).attr('data-bind', "with: client.varbyname('" + vn + "')");
                    node.innerHTML = "<input class='control_check' type='checkbox' title='" + vn + "' value='' data-bind='checked: latest_value'/>" + node.innerHTML;
                    break;
                case 'button':
                    node.innerHTML = '<button class="control_button" title="' + vn + '" onclick="client.send_event(' + "'" + vn + "', " + bv + ')">' + vn + '=' + bv + "</button>";
                    break;
                default:
                    client.throw("Invalid var-bind type: " + bt);
            };
        });
    };

    client.add_note = function (note) {
        d = new Date();
        client.notes.unshift('' + d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds() + ', ' + note);
    };

    client.log_message = function (message) {
        if (message.type <= client.message_verbosity()) return;
        if (client.messages.unshift(message) > client.max_messages()) {
            client.messages.pop();
        };
    };

    client.parse_message = function (event) {
        if ('type' in event.value) {
            lvl = event.value['type'];
        } else {
            lvl = -1;
        };

        if ('message' in event.value) {
            msg = '[' + lvl + ']' + event.value['message'];
        } else {
            msg = '[' + lvl + ']' + 'Invalid message:\n';
            for (k in event.value) {
                msg += '' + k + ' = ' + event.value[k] + '\n';
            };
        };

        if (lvl > client.message_error_verbosity()) {
            client.error('MWorks error:\n' + msg);
        };
        client.log_message(new mworks.message(event));
    };

    client.clear_messages = function () {
        client.messages([]);
    };

    client.error = function (msg) {
        console.log(msg);
    };

    client.info = function (msg) {
        console.log(msg);
    };

    client.throw = function (msg) {
        client.error(msg);
        throw msg;
    };

    client.load_config = function (config) {
        /*
         * host
         * port
         * user
         * experiment_path
         * experiment_name
         * variableset
         * variableeset_overwrite
         * variablesets : set by state
         * datafile
         * datafile_overwrite
         * protocol
         * protocols : set by state
         * 
         * autoconnect
         *
         * ui/graphs
         */
        client.config = config;
        if ('host' in config) {
            client.host(config['host']);
        };
        if ('port' in config) {
            client.port(config['port']);
        };
        if ('user' in config) {
            client.user(config['user']);
        };
        if ('experiment_path' in config) {
            client.experiment_path(config['experiment_path']);
        };
        if ('experiment_name' in config) {
            client.experiment_name(config['experiment_name']);
        };
        if ('variableset' in config) {
            client.variableset(config['variableset']);
        };
        if ('variableset_overwrite' in config) {
            client.variableset_overwrite(config['variableset_overwrite']);
        };
        if ('datafile' in config) {
            client.datafile(config['datafile']);
        };
        if ('datafile_overwrite' in config) {
            client.datafile_overwrite(config['datafile_overwrite']);
        };
        if ('protocol' in config) {
            client.protocol(config['protocol']);
        };

        if ('animal' in config) {
            // possibly define datafile
            if (client.datafile() === '') {
                fn = mworks.utils.make_filename(config['animal']);
                client.datafile(fn);
                client.config['datafile'] = fn;
            };
        };

        $(client).one('after:state', function () {
            console.log('auto_config, after:state');
            // check that experiment_path and config.experiment_path agree or experiment_path is blank?
            if ((client.experiment_path() === client.config['experiment_path']) | (client.experiment_path() === "")) {
                // ---- autoconfig!! ----
                // autoload_variableset
                // autosave_variableset
                $(client).one('after:variablesets', function () {
                    if (client.variableset() === "") {
                        if (client.config['autoload_variableset']) {
                            mr = mworks.utils.find_most_recent(client.variablesets(), function (i) {
                                return i.indexOf(client.config['animal']) !== -1;
                            });
                            if (mr !== null) {
                                client.variableset(mr);
                                client.load_variableset();
                            } else {
                                client.error('Failed to find recent variableset');
                                console.log('Failed to find recent variableset');
                            };
                        };
                        // autosave
                        if (client.config['autosave_variableset']) {
                            fn = mworks.utils.make_filename(client.config['animal'], '_vars');
                            if (client.variableset() === fn) {
                                client.save_variableset();
                            } else {
                                client.create_variableset(fn);
                            };
                        };
                    };
                });
                // autosave_datafile
                if (client.config['autosave_datafile']) { $(client).one('after:loaded', function () { client.open_datafile(); }); };
                // autostart
                if (client.config['autostart']) { $(client).one('after:protocols', function () { client.start_experiment(); }); };
                // autoload_experiment
                if (client.config['autoload_experiment']) { client.load_experiment(); };
                // autoconnect (done elsewhere)
            } else {
                client.error("Cowardly refusing to configure server\nwith loaded experiment:\n" + client.experiment_path());
            };
        });

        if (client.connected()) {
            $(client).trigger('after:connected');
        };

        if (client.loaded()) {
            $(client).trigger('after:loaded');
        };

        if ((config['autoconnect']) & (!(client.connected()))) {
            client.connect();
        };

        if (client.state() !== undefined) {
            client.trigger('after:state');
        };
    };

    client.parse_state = function (state) {
        console.log({'State': state});
        if ('paused' in state) {
            if (Boolean(state.paused) != client.paused()) {
                client.paused(Boolean(state.paused));
            };
        };
        if ('loaded' in state) {
            if (Boolean(state.loaded) != client.loaded()) {
                client.loaded(Boolean(state.loaded));
                $(client).trigger('after:loaded');
            };
        };
        if ('running' in state) {
            if (Boolean(state.running) != client.running()) {
                client.running(Boolean(state.running));
            };
        };
        if ('experiment name' in state) {
            if (state['experiment name'] != client.experiment_name()) {
                client.experiment_name(state['experiment name']);
                client.protocols.removeAll();
                client.variablesets.removeAll();
            };
        };
        if ('experiment path' in state) {
            if (state['experiment path'] != client.experiment_path()) {
                client.experiment_path(state['experiment path']);
            };
        };
        if ('current protocol' in state) {
            if (state['current protocol'] != client.protocol()) {
                client.protocol(state['current protocol']);
            };
        };
        if ('protocols' in state) {
            if (!(mworks.utils.array_equal(state.protocols, client.protocols()))) {
                client.protocols.removeAll();
                for (i in state.protocols) {
                    if (!(state.protocols[i] == null)) {
                        if ('protocol name' in state.protocols[i]) {
                            client.protocols.push(state.protocols[i]['protocol name']);
                        };
                    };
                };
                $(client).trigger('after:protocols');
            };
        };
        if ('saved variables' in state) {
            if (!(mworks.utils.array_equal(state['saved variables'], client.variablesets()))) {
                client.variablesets.removeAll();
                client.variablesets.push(""); // include a blank one
                for (i in state['saved variables']) {
                    if (!(state['saved variables'][i] == null)) {
                        client.variablesets.push(state['saved variables'][i]);
                    };
                };
                $(client).trigger('after:variablesets');
            };
        };
        if ('current protocol' in state) {
            if (state['current protocol'] != client.protocol()) {
                client.protocol(state['current protocol']);
            };
        };
        if ('datafile' in state) {
            if (state.datafile != client.datafile()) {
                client.datafile(state.datafile);
            };
        };
        if ('datafile error' in state) {
            if (state['datafile error']) {
                client.error('datafile error:' + state['datafile']);
                console.log({'datafile error': state});
            };
        };

        if ('datafile saving' in state) {
            if (state['datafile saving'] != client.datafile_saving()) {
                client.datafile_saving(state['datafile saving']);
            };
        };
        /*
         * datafile error
         * variableset : does not exist!
         */
        /*
        if ('variable groups' in state) {
            if (!mworks.utils.objects_equal(client.variable_groups, state['variable groups'])) {
                // update groups
            };
        };
        */

        if ('codec' in state) {
            // test equality of client.codec and state.codec
            if (!mworks.utils.objects_equal(client.codec, state.codec)) {
                client.codec = state.codec;
                // update vars
                client.vars.removeAll();
                for (k in client.codec) {
                    name = client.codec[k];
                    client.vars.push(
                            new mworks.variable(name, client.send_event));
                };
                events = client.unstored_events.splice(0, client.unstored_events.length);
                for (ei in events) {
                    event = events[ei];
                    for (vi in client.vars()) {
                        if (client.vars()[vi].name() == event.name) {
                            client.vars()[vi].add_event(event);
                            event = null;
                            break;
                        };
                    };
                    if (event) {
                        client.unstored_events.push(event);
                    };
                };
                $(client).trigger('after:codec');
            };
        };
    };

    client.require_socket = function () {
        if (client.socket == null) {
            client.throw("missing web socket, first call connect");
        };
    };

    client.require_connected = function () {
        if (!(client.connected())) {
            client.throw("no connection to server");
        };
    };

    client.varnames = function (key) {
        return $.map(client.vars(), function (v) { return v.name; });
    };

    client.varbyname = function (name) {
        for (vi in client.vars()) {
            if (client.vars()[vi].name() == name) {
                return client.vars()[vi];
            };
        };
        client.throw("Failed to find variable with name " + name);
    };

    /*
    client.varbyname = function (name) {
        matches = client.vars().filter( function (v) { return v.name == name; });
        if (matches.length == 1) {
            return matches;
        };
        client.throw("Failed to find variable with name " + name + " [" + matches + "]");
    };
    */

    // used to listen for events
    /*
    client.register = function (key) {
        console.log("Register: " + key);
        console.log(key);
        if (key == undefined) return;
        client.require_socket();
        client.require_connected();
        if (!(key in client.varnames())) {
            client.vars.push(new mworks.variable(key));
            client.socket.emit('register', key);
        } else {
            client.throw("register[" + key + "] called more than once");
        };
    };
    */
    
    client.connect_socket = function () {
        client.socket = io.connect('/client');

        client.socket.on('connect', function () {
            console.log('Socket connected');
            client.info('Socket connected');
            client.socket_connected(true);
        });

        client.socket.on('disconnect', function () {
            console.log('Socket disconnected');
            client.info('Socket disconnected');
            client.socket_connected(false);
        });

        client.socket.on('event', function (event) {
            /*
            if (!(event.name in client.varnames())) {
                client.throw('Received event[' + event + '] that was not in vars');
            };
            */
            if (event.name == null) {
                if (event.code > 3) {
                    client.throw('Received no name event with code > 3 [' + event.code + '=' + event.value + ']')
                } else {
                    return
                };
            };

            if (event.code === 6) {  // pass on messages
                if (typeof(event.value) === 'object') {
                    client.parse_message(event);
                };
            };

            for (i in client.vars()) {
                if (client.vars()[i].name() == event.name) {
                    client.vars()[i].add_event(event);
                    return
                };
            };
            client.unstored_events.push(event);
        });

        client.socket.on('error', function (error) {
            console.log("Error: " + error);
            client.throw(error)
        });

        client.socket.on('state', function (state) {
            client.state(state);
            try {
                client.parse_state(state);
            } catch (error) {
                client.error(error);
            };
            $(client).trigger('after:state');
        });
        
        client.socket.on('iostatus', function (iostatus) {
            client.connected(iostatus);
            if (client.connected()) {
                $(client).trigger('after:connected');
            };
        });
    };

    client.send_event = function(key, value) {
        client.require_socket();
        client.require_connected();
        client.socket.emit('event', {key: key, value: value});
    };

    // connect
    client.connect = function () {
        client.require_socket();
        client.socket.emit('command', 'host', client.host());
        client.socket.emit('command', 'port', client.port());
        client.socket.emit('command', 'user', client.user());
        client.socket.emit('command', 'startserver', client.startserver());
        client.socket.emit('command', 'connect');
        client.info('Connecting to ' + client.host() + ':' + client.port() + ' as ' + client.user());
    };

    client.disconnect = function () {
        client.require_socket();
        client.socket.emit('command', 'disconnect');
        client.info('Disconnect called on client')
    };

    client.toggle_connect = function () {
        if (client.connected()) {
            client.disconnect();
        } else {
            client.connect();
        };
    };

    client.reconnect = function () {
        client.require_socket();
        client.socket.emit('command', 'reconnect');
    };

    client.load_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'load_experiment', client.experiment_path());
        client.info('Loading experiment: ' + client.experiment_path());
    };

    client.close_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'close_experiment', client.experiment_path());
        client.info('Closing experiment: ' + client.experiment_path());
    };

    client.select_experiment = function () {
    };

    client.start_experiment = function () {
        client.require_socket();
        client.require_connected();
        if (client.protocol() != '') {
            for (i in client.protocols()) {
                if (client.protocol() == client.protocols()[i]) {
                    client.socket.emit('command', 'select_protocol', client.protocol());
                    client.socket.emit('command', 'start_experiment');
                    break;
                };
            };
        };
        client.info('Starting experiment: ' + client.protocol());
    };

    client.stop_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'stop_experiment');
        client.info('Stopping experiment: ' + client.protocol());
    };

    client.toggle_running = function () {
        if (client.running()) {
            client.stop_experiment();
        } else {
            client.start_experiment();
        };
    };

    client.toggle_paused = function () {
        if (client.paused()) {
            client.resume_experiment();
        } else {
            client.pause_experiment();
        };
    };

    client.pause_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'pause_experiment');
        client.info('Pausing');
    };

    client.resume_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'resume_experiment');
        client.info('Resuming');
    };

    client.open_datafile = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'open_datafile', 
                client.datafile(), client.datafile_overwrite());
        client.info('Opening datafile: ' + client.datafile());
    };

    client.close_datafile = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'close_datafile');
        client.info('Closing datafile: ' + client.datafile());
    };

    client.load_variableset = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'load_variables', client.variableset());
        client.info('Loading variableset: ' + client.variableset());
    };

    client.create_variableset = function (name) {
        client.require_socket();
        client.require_connected();
        // check if variableset is in variablesets
        if ((!(client.variableset_overwrite())) && ($.inArray(name, client.variablesets()) !== -1)) {
            client.throw("Cannot create variableset " + name + " without overwriting");
        };
        client.socket.emit('command', 'save_variables',
                name, client.variableset_overwrite());
        $(client).one('after:variablesets', function () {
            client.variableset(name);
        });
        client.info('Creating variableset: ' + name);
    };

    client.save_variableset = function () {
        client.require_socket();
        client.require_connected();
        if ((!(client.variableset_overwrite())) && ($.inArray(client.variableset(), client.variablesets()) !== -1)) {
            client.throw("Cannot save variableset " + client.variableset() + " without overwriting");
        };
        client.socket.emit('command', 'save_variables',
                client.variableset(), client.variableset_overwrite());
        client.info('Saving variableset: ' + client.variableset());
    };

    client.select_protocol = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'select_protocol', client.protocol());
        client.info('Protocol selected: ' + client.protocol());
    };

    client.add_graph = function (vars, type) {
        client.graphs.push(new mworks.graph(client, vars, type));
    };

    client.redraw_graphs = function () {
        for (i in client.graphs) {
            client.graphs[i].redraw(client.graph_ref());
        };
    };

    return client;
});
