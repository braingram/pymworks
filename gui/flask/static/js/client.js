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

    return utils;
}(jQuery));


mworks.graph = function (client, vars, type) {
    var graph = this;
    graph.vars = vars;
    graph.type = type;
    graph.client = client;
    graph.data = [];

    graph.gid = null;
    graph.chart = null;

    graph.build = function () {
        // setup data
        for (i in vars) {
            graph.data.push({'key': vars[i], 'values': []});
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

    graph.getvalue = function (di, index) {
        if (index >= graph.data[di]['values'].length) {
            return [false, graph.data[di]['values'][graph.data[di]['values'].length - 1]];
        } else {
            return [true, graph.data[di]['values'][index]];
        };
    };

    graph.order_data = function () {
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
                r = graph.getvalue(di, inds[di]);
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

    graph.redraw = function () {
        graph.order_data();
        console.log(graph.data);
        d3.select('#chart')
            .datum(graph.data)
          .transition().duration(500)
            .call(graph.chart);
    };

    graph.start = function () {
        graph.gid = window.setInterval(graph.redraw, 1000);
    };

    graph.stop = function () {
        window.clearInterval(graph.gid);
    };

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
            send_event(variable.name(), value);
        },
        owner: this
    });

    variable.latest = ko.computed({
        read: function () {
            return variable.events().length ? variable.events()[variable.events().length - 1] : {value: null};
        },
        write: function (value) {
            send_event(variable.name(), value);
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

mworks.client = (function () {
    /*
     * Add listeners for:
     * - protocol (for protocol selection)
     * - variables (for variables selection)
     */
    var client = {};
    client.id = mworks.utils.get_id();
    client.socket = null;

    client.graphs = [];

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
    client.codec = {};
    client.unstored_events = [];

    // these will be called after their respective state changes
    //client.after_connected = null;
    //client.after_loaded = null;
    //client.after_protocols = null;

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
                    node.innerHTML = "<input class='control_input' value='' data-bind='value: latest_value'/>" + node.innerHTML;
                    break;
                case 'check':
                    $(this).attr('data-bind', "with: client.varbyname('" + vn + "')");
                    node.innerHTML = "<input class='control_check' type='checkbox' value='' data-bind='checked: latest_value'/>" + node.innerHTML;
                    break;
                case 'button':
                    node.innerHTML = '<button class="control_button" title="' + vn + '" onclick="client.send_event(' + "'" + vn + "', " + bv + ')">' + vn + '=' + bv + "</button>";
                    break;
                default:
                    client.throw("Invalid var-bind type: " + bt);
            };
        });
    };

    client.error = function (msg) {
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
        if ('host' in config) {
            client.host(config['host']);
        };
        if ('port' in config) {
            client.port(config['port']);
        };
        if ('user' in config) {
            client.port(config['user']);
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

        if ('autoconnect' in config) {
            client.connect();
        };
        if ('autoload_experiment' in config) {
            // only do this once
            $(client).one('after:connected', function () {
            //client.after_connected = function () {
                console.log("after_connected... ");
                client.load_experiment();
            });
            if (client.connected()) {
                $(client).trigger('after:connected');
                //client.after_connected();
            };
        };
        /*
        $(client).on('after:loaded', function () {
        //client.after_loaded = function () {
            console.log("after_loaded...");
            if ('autoload_variableset' in config) {
                client.load_variableset();
            };
            if ('autosave_datafile' in config) {
                client.open_datafile();
            };
        });
        */
        if (client.loaded()) {
            $(client).trigger('after:loaded');
            //client.after_loaded();
        };

        // autoload_variableset
        if ('autoload_variableset' in config) {
            // only do this once
            $(client).one('after:variablesets', function () {
                console.log("after:variablesets");
                // if defined, load that
                if (client.variableset() === "") {
                    // else find most recent
                    if ('animal' in config) {
                        test = function (i) { return i.indexOf(config['animal']) !== -1; };
                    } else {
                        test = undefined;
                    };
                    mr = mworks.utils.find_most_recent(client.variablesets(), test);
                    if (mr !== null) {
                        client.variableset(mr);
                        client.load_variableset();
                    } else {
                        // TODO error
                        client.error('Failed to find recent variableset');
                        console.log('Failed to find recent variableset');
                    };
                };
                // autosave_variableset
                if ('autosave_variableset' in config) {
                    if ('animal' in config) {
                        fn = mworks.utils.make_filename(config['animal'], '_vars');
                        if (client.variableset() === fn) {
                            client.save_variableset();
                        } else {
                            client.create_variableset(fn);
                        };
                    } else {
                        // TODO error
                        client.error('Failed to autosave variableset, no animal defined in config');
                        console.log('Failed to autosave variableset, no animal defined in config');
                    };
                };
            });
        };

        // autosave_datafile
        if ('autosave_datafile' in config) {
            $(client).one('after:loaded', function () {
                // start streaming
                if (client.datafile() === '') {
                    if ('animal' in config) {
                        client.datafile(mworks.utils.make_filename(config['animal']));
                    } else {
                        // TODO error
                        client.error('Failed to autosave datafile, no animal defined in config');
                        console.log('Failed to autosave datafile, no animal defined in config');
                    };
                };
                client.open_datafile();
            });
        };

        if ('autostart' in config) {
            $(client).one('after:protocols', function () {
            //client.after_protocols = function () {
                console.log("after_protocols...");
                client.start_experiment();
            });
            for (i in client.protocols()) {
                if (client.protocol() == client.protocols()[i]) {
                    $(client).trigger('after:protocols');
                    //client.after_protocols();
                    break;
                };
            };
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
                //if (client.loaded() & (client.after_loaded != null)) {
                //    client.after_loaded();
                //};
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
                //if (client.after_protocols != null) {
                //    client.after_protocols();
                //};
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
            client.error('datafile error:' + state['datafile']);
            console.log({'datafile error': state});
        };
        /*
         * datafile error
         * variableset : does not exist!
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
                //if (client.after_codec != null) {
                //    client.after_codec();
                //};
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
            client.socket_connected(true);
        });

        client.socket.on('disconnect', function () {
            console.log('Socket disconnected');
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
            client.parse_state(state);
        });
        
        client.socket.on('iostatus', function (iostatus) {
            client.connected(iostatus);
            if (client.connected()) {
                $(client).trigger('after:connected');
            };
            //if (client.connected() & (client.after_connected != null)) {
            //    client.after_connected();
            //};
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
    };

    client.disconnect = function () {
        client.require_socket();
        client.socket.emit('command', 'disconnect');
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
    };

    client.stop_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'stop_experiment');
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
    };

    client.resume_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'resume_experiment');
    };

    client.open_datafile = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'open_datafile', 
                client.datafile(), client.datafile_overwrite());
    };

    client.close_datafile = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'close_datafile');
    };

    client.load_variableset = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'load_variables', client.variableset());
    };

    client.create_variableset = function (name) {
        console.log('create_variableset: ' + name);
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'save_variables',
                name, client.variableset_overwrite());
        client.variableset(name);
    };

    client.save_variableset = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'save_variables',
                client.variableset(), client.variableset_overwrite());
    };

    client.select_protocol = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'select_protocol', client.protocol());
    };

    client.add_graph = function (vars, type) {
        client.graphs.push(new mworks.graph(client, vars, type));
    };

    client.start_graphing = function () {
        for (i in client.graphs) {
            client.graphs[i].start();
        };
    };

    client.stop_graphing = function () {
        for (i in client.graphs) {
            client.graphs[i].stop();
        };
    };

    return client;
});
