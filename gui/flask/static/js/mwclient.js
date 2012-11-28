var MWClient = function(selector, cfg) {
    this.node = $(selector);

    this.host = "";
    this.port = 19989;
    this.experiment = "";
    this.variableset = "";
    this.stream = "";
    this.protocol = "";
    this.running = false;

    //console.log(this);
    var instance = this;

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
        $(".toolbar button.control", this.node).attr("title", "Stop")
            .button("option", {
                label: "Stop",
                icons: {
                    primary: "ui-icon-stop"
                }
            });
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
                "Connect": function(event) { instance.connect(event); },
                "Disconnect": function(event) { instance.disconnect(event); },
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
                    instance.load_experiment(event); },
                "Close Experiment": function(event) {
                    instance.close_experiment(event); },
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
                "Load": function(event) { instance.load_variableset(event); },
                "Save": function(event) { instance.save_variableset(event); },
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
                "Start": function(event) { instance.start_stream(event); },
                "Stop": function(event) { instance.stop_stream(event); },
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
            .click(function(event) { instance.connect_click(event); });

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
            .click(function(event) { instance.control_click(event); });

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
    this.setup_toolbar();
    this.load_config(cfg === undefined ? Object() : cfg)
    return this;
};
