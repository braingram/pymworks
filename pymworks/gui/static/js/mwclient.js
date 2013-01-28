var MWClient = function(selector, cfg, debug) {
    this.host = ko.observable("");
    this.port = ko.observable(19989);
    this.user = ko.observable("");

    this.experiment = ko.observable("");

    this.variables = ko.observable("");
    this.variables_overwrite = ko.observable(false);

    this.datafile = ko.observable("");
    this.datafile_overwrite = ko.observable(false);

    this.protocol = ko.observable("");
    this.protocols = ko.observableArray();

    this.connected = ko.observable(false);  // client connected to server

    this.running = ko.observable(false);  // experiment running
    this.paused = ko.observable(false);
    this.loaded = ko.observable(false);

    this.vars = {};

    this.max_time = null;

    if (debug === 'console') {
        this.debug = console.log;
    } else if (debug === 'notify') {
        this.debug = function(message) {
            $.pnotify({
                title: message,
            });
        };
    } else {
        this.debug = function(message) {
        };
    };

    // levels
    // 0 : critical
    // 1 : error
    // 2 : warning
    // 3 : info
    // 4 : debug
    this.notify_threshold = ko.observable(5);
    this.notify_default_level = ko.observable(4);

    this.notify = function(message, status, result, error, level) {
        if (level === undefined) {
            level = this.notify_default_level();
        };

        if (level > this.notify_threshold) {
            return;
        };

        o = {title: message};

        if (status == 0) {
            o.type = 'success';
            o.text = 'result: ' + result;
        } else {
            o.type = 'error';
            o.text = 'error: ' + error + ' result: ' + result;
        };

        $.pnotify(o);
    };

    this.ajnofiy = function(message, level) {
        return function (status, result, error) {
            this.notify(message, status, result, error, level);
        };
    };

    this.connect = function() {
        this.debug("Connecting...");
        // use this.host() this.port() this.user()
        // to connect to the server
    };

    this.disconnect = function() {
        this.debug("Disconnecting...");
    };

    this.load_experiment = function() {
        Ajaxify.send({
            func: 'load_experiment',
            args: [this.experiment()],
            callback: this.ajnotify('load_experiment'),
        });
    };

    this.start_experiment = function() {
        Ajaxify.send({
            func: 'start_experiment',
            callback: this.ajnotify('start_experiment'),
        });
    };

    this.stop_experiment = function() {
        Ajaxify.send({
            func: 'stop_experiment',
            callback: this.ajnotify('stop_experiment'),
        });
    };

    this.start_experiment = function() {
        Ajaxify.send({
            func: 'pause_experiment',
            callback: this.ajnotify('pause_experiment'),
        });
    };

    this.open_datafile = function() {
        Ajaxify.send({
            func: 'open_datafile',
            args: [this.datafile(), this.datafile_overwrite()],
            callback: this.ajnotify('open_datafile'),
        });
    };

    this.close_datafile = function() {
        Ajaxify.send({
            func: 'close-datafile',
            callback: this.ajnotify('close_datafile'),
        });
    };

    this.load_variables = function() {
        Ajaxify.send({
            func: 'load_variables',
            args: [this.variables()],
            callback: this.ajnotify('load_variables'),
        });
    };

    this.save_variables = function() {
        Ajaxify.send({
            func: 'save_variables',
            args: [this.variables(), this.variables_overwrite()],
            callback: this.ajnotify('save_variables'),
        });
    };

    this.select_protocol = function() {
        Ajaxify.send({
            func: 'select_protocol',
            args: [this.protocol()],
            callback: this.ajnotify('select_protocol'),
        });
    };

    this.parse_state = function(state) {
        if ('protocols' in state) {
            // TODO update this.protocols
        };
        if ('current protocol' in state) {
            this.protocol(state['current protocol']);
        };
        if ('experiment name' in state) {
            this.experiment(state['experiment name']);
        };
        if ('datafile' in state) {
            this.datafile(state['datafile']);
        };
        /*
         * loaded
         * paused - not used?
         * running
         * saved variables
         * client_connected
         * client_disconnected
         * server_disconnected
         */
    };

    this.process_events = function(events) {
        for (event in events) {
            if (!('name' in event)) {
                this.debug("event " + event + " missing name");
                continue;
            };
            if (event.name in this.vars) {
                this.vars.push(event);
            };
        };
    };

    this.update = function() {
        // make sure client is updated
        Ajaxify.send({
            func: 'update',
            callback: this.ajnotify('update'),
        });

        // update running
        Ajaxify.send({
            attr: '_running',
            callback: function (status, result, error) {
                this.notify('update(running)', status, result, error);
                if (status == 0) {
                    this.connected(result);
                };
            },
        });

        if (this.connected()) {
            // update state
            Ajaxify.send({
                attr: 'state',
                callback: function (status, result, error) {
                    this.notify('update(state)', status, result, error);
                    if (status == 0) {
                        this.parse_state(result);
                    };
                },
            });
            // update events/vars
            Ajaxify.send({
                func: 'get_events',
                kwargs: {
                    time_range: [this.last_time, this.max_time],
                },
                callback: function (status, result, error) {
                    this.notify('update(get_events)', status, result, error);
                    if (status == 0) {
                        this.process_events(result);
                    };
                },
            });
        };
    };

    /* ----------------------------------------------
    this.toolbar_text = function(label, text) {
        $(".toolbar button." + label, this.node)
            .attr("title", text)
            .button("option", "label", text);
    };

    this.load_experiment = function(event) {
        console.log("load_experiment");
        experiment = $("#experiment_dialog input[name='filename']").val();
        // check if experiment is valid
        if (experiment != "") {
            this.experiment = experiment;
            this.toolbar_text("experiment", this.experiment);
        };
        $("#experiment_dialog").dialog("close");
    };

    this.close_experiment = function(event) {
        this.experiment = "";
        console.log("close_experiment");
        this.toolbar_text("experiment", "Experiment");
        $("#experiment_dialog").dialog("close");
    };
    
    this.start_experiment = function() {
        console.log("start_experiment");
        Ajaxify.send({
            func: "start_experiment",
            callback: function (s, r, e) {
                this.notify("start_experiment", s, r, e);
            }});
        // issue ajax request: ajax?client=host&function=start_experiment
        this.running = true;
    };

    this.stop_experiment = function() {
        console.log("stop_experiment");
        $(".toolbar button.control", this.node).attr("title", "Start")
            .button("option", {
                label: "Start",
                icons: {
                    primary: "ui-icon-play"
                }
            });
        this.running = false;
    };

    this.connect = function(event) {
        console.log("connect");
        host = $("#connect_dialog input[name='host']").val();
        port = Number($("#connect_dialog input[name='port']").val());
        if ((host != "") & (port > 0)) {
            this.host = host;
            this.port = port;
            $.pnotify({
                title: "Client Event",
                text: "Connecting to..."
            });
            this.toolbar_text("connect", this.host);
        };
        $("#connect_dialog").dialog("close");
    };

    this.disconnect = function(event) {
        console.log("disconnect");
        this.toolbar_text("connect", "Connect");
        $("#connect_dialog").dialog("close");
    };

    this.load_variableset = function(event) {
        console.log("load_variableset");
        variableset = $("#variableset_dialog input[name='filename']").val();
        if (variableset != "") {
            this.variablset = varibleset;
            this.toolbar_text("connect", this.variableset);
        };
        $("#variableset_dialog").dialog("close");
    };

    this.save_variableset = function(event) {
        // TODO should saving also load?
        // TODO should saving be automatic?
        console.log("save_variableset");
        variableset = $("#variableset_dialog input[name='filename']").val();
        if (variableset != "") {
            this.varibleset = variableset;
        };
        $("#variableset_dialog").dialog("close");
    };

    this.start_stream = function(event) {
        console.log("start_stream");
        stream = $("#stream_dialog input[name='filename']").val();
        if (stream != "") {
            this.stream = stream;
            this.toolbar_text("stream", this.stream);
        };
        $("#stream_dialog").dialog("close");
    };

    this.stop_stream = function(event) {
        console.log("stop_stream");
        this.toolbar_text("stream", "Stream");
        $("#stream_dialog").dialog("close");
    };
    */

    /****************************************************************
     *                            Button
     *                           Handlers
     ****************************************************************/
    this.connect_click = function(event) {
        // host
        // port
        console.log("connect_click");
        $("#connect_dialog").dialog({
            autoOpen: false,
            height: 300,
            width: 350,
            modal: true,
            buttons: {
                "Connect": function(event) { this.connect(event); },
                "Disconnect": function(event) { this.disconnect(event); },
                "Cancel": function() { $(this).dialog("close"); },
            },
            close: function() { $(this).dialog("close"); }
        });
        // set to current values
        $("#connect_dialog input[name='host']").val(this.host);
        $("#connect_dialog input[name='port']").val(this.port);
        // show
        $("#connect_dialog").dialog("open");
    };

    this.experiment_click = function(event) {
        // filename
        console.log("experiment_click");
        $("#experiment_dialog").dialog({
            autoOpen: false,
            height: 300,
            width: 350,
            modal: true,
            buttons: {
                "Load Experiment": function(event) {
                    this.load_experiment(event); },
                "Close Experiment": function(event) {
                    this.close_experiment(event); },
                "Cancel": function() { $(this).dialog("close"); },
            },
            close: function() { $(this).dialog("close"); }
        });
        $("#experiment_dialog input[name='filename']").val(this.experiment);
        $("#experiment_dialog").dialog("open");
    };

    this.control_click = function(event) {
        // start/stop
        console.log("control_click");
        if (this.running) {
            this.stop_experiment();
        } else {
            this.start_experiment();
        };
    };

    this.variableset_click = function(event) {
        // load/save
        // filename
        console.log("variableset_click");
        $("#variableset_dialog").dialog({
            autoOpen: false,
            height: 300,
            width: 350,
            modal: true,
            buttons: {
                "Load": function(event) { this.load_variableset(event); },
                "Save": function(event) { this.save_variableset(event); },
                "Cancel": function() { $(this).dialog("close"); },
            },
            close: function() { $(this).dialog("close"); }
        });
        $("#variableset_dialog input[name='filename']").val(this.variableset);
        $("#variableset_dialog").dialog("open");
    };

    this.stream_click = function(event) {
        // start/stop
        // filename
        console.log("stream_click");
        $("#stream_dialog").dialog({
            autoOpen: false,
            height: 300,
            width: 350,
            modal: true,
            buttons: {
                "Start": function(event) { this.start_stream(event); },
                "Stop": function(event) { this.stop_stream(event); },
                "Cancel": function() { $(this).dialog("close"); },
            },
            close: function() { $(this).dialog("close"); }
        });
        $("#stream_dialog input[name='filename']").val(this.stream);
        $("#stream_dialog").dialog("open");
    };

    /****************************************************************
     *                             Setup 
     *                           Functions
     ****************************************************************/
    this.setup_toolbar = function() {
        // buttons
        $(".connect", this.node).button({
            text: "Connect",
            icons: {
                primary: "ui-icon-transferthick-e-w"
            }})
            .click(function(event) { this.connect_click(event); });

        $(".experiment", this.node).button({
            text: "Experiment",
            icons: {
                primary: "ui-icon-folder-open"
            }})
            .click(this.experiment_click);

        $(".control", this.node).button({
            text: false,
            icons: {
                primary: "ui-icon-play"
            }})
            .click(function(event) { this.control_click(event); });

        $(".variableset", this.node).button({
            text: "Variable Set",
            icons: {
                primary: "ui-icon-gear"
            }})
            .click(this.variableset_click);

        $(".stream", this.node).button({
            text: "Stream",
            icons: {
                primary: "ui-icon-disk"
            }})
            .click(this.stream_click);

    };

    this.load_config = function(cfg) {
        this.host = cfg.host === undefined ? "localhost" : cfg.host;
        this.port = cfg.port === undefined ? 19989 : cfg.port;
        this.experiment = cfg.experiment === undefined ? "" : cfg.experiment;
        this.variableset = cfg.variableset === undefined ? "" : cfg.variableset;
        this.stream = cfg.stream === undefined ? "" : cfg.stream;
        // TODO protocol
        // TODO load canvas
        this.setup_canvas();

        if (cfg.autoconnect === undefined ? false : cfg.autoconnect) {
            // connect
        };
        if (cfg.autoexperiment === undefined ? false : cfg.autoexperiment) {
            // experiment
        };
        if (cfg.autovariableset === undefined ? false : cfg.autovariableset) {
            // variableset
        };
        if (cfg.autostream === undefined ? false : cfg.autostream) {
            // stream
        };
        if (cfg.autostart === undefined ? false : cfg.autostart) {
            // start
        };

        // TODO protocol
    };

    this.save_config = function() {
        // TODO soemthing like this
        d = {
            host: this.host,
            port: this.port,
            experiment: this.experiment,
            variableset: this.variableset,
            stream: this.stream,
        };
    };

    this.setup_canvas = function(cfg) {
        canvas = $('.canvas', this.node);
        $('.flags', canvas).buttonset();
    };

    // ************** Return **************
    //this.setup_toolbar();
    this.load_config(cfg === undefined ? Object() : cfg)
    return this;
}();
