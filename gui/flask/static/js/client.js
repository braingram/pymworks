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

    return utils;
}(jQuery));

mworks.variable = function (name) {
    var variable = this;
    variable.name = ko.observable(name);
    variable.events = ko.observableArray();

    variable.latest = ko.computed(function () {
        return variable.events().length ? variable.events()[variable.events().length - 1] : {value: null};
    });

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

    client.host = ko.observable("");
    client.port = ko.observable(19989);
    client.user = ko.observable("");
    
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
    client.loaded = ko.observable(false);

    client.vars = ko.observableArray();

    client.throw = function (msg) {
        throw msg;
    };

    client.parse_state = function (state) {
        console.log('State...');
        console.log(state);
        if ('paused' in state) {
            if (Boolean(state.paused) != client.paused()) {
                client.paused(Boolean(state.paused));
            };
        };
        if ('loaded' in state) {
            if (Boolean(state.loaded) != client.loaded()) {
                client.loaded(Boolean(state.loaded));
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
            };
        };
        if ('saved variables' in state) {
            if (!(mworks.utils.array_equal(state['saved variables'], client.variablesets()))) {
                client.variablesets.removeAll();
                for (i in state['saved variables']) {
                    if (!(state['saved variables'][i] == null)) {
                        client.variablesets.push(state['saved variables'][i]);
                    };
                };
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
        /*
         * datafile error
         * variableset : does not exist!
         */
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
            for (i in client.vars()) {
                if (client.vars()[i].name() == event.name) {
                    client.vars()[0].events.push(event);
                    return
                };
            };
            client.throw("event not stored: " + event);
            //client.varbyname(event.name).push(event);
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
        });
    };

    client.send_event = function(name, key, value) {
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
            client.socket.emit('command', 'select_protocol', client.protocol());
            client.socket.emit('command', 'start_experiment');
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
    }

    client.pause_experiment = function () {
        client.require_socket();
        client.require_connected();
        client.socket.emit('command', 'pause_experiment');
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

    return client;
});
