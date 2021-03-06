/*jslint browser: true, forin: true, eqeq: true, white: true, sloppy: true, vars: true, nomen: true */
/*global $, jQuery, _, asm, common, config, controller, dlgfx, format, header, html, tableform, validate */

$(function() {

    var onlineform_incoming = {

        model: function() {
            var table = {
                rows: controller.rows,
                idcolumn: "COLLATIONID",
                edit: function(row) {
                    header.show_loading(_("Loading..."));
                    common.ajax_post("onlineform_incoming", "mode=view&collationid=" + row.COLLATIONID)
                        .then(function(result) {
                            $("#dialog-viewer-content").html(result); 
                            $("#dialog-viewer").dialog("open");
                        })
                        .always(function() {
                            header.hide_loading();
                        });
                },
                complete: function(row) {
                    if (row.LINK) { return true; }
                },
                columns: [
                    { field: "FORMNAME", display: _("Name") },
                    { field: "POSTEDDATE", display: _("Received"), initialsort: true, initialsortdirection: "desc", formatter: tableform.format_datetime },
                    { field: "HOST", display: _("From") },
                    { field: "PREVIEW", display: _("Preview") },
                    { field: "LINK", display: _("Link") }
                ]
            };

            var buttons = [
                { id: "delete", text: _("Delete"), icon: "delete", enabled: "multi", 
                     click: function() { 
                         tableform.delete_dialog()
                             .then(function() {
                                 tableform.buttons_default_state(buttons);
                                 var ids = tableform.table_ids(table);
                                 return common.ajax_post("onlineform_incoming", "mode=delete&ids=" + ids);
                             })
                             .then(function() {
                                 tableform.table_remove_selected_from_json(table, controller.rows);
                                 tableform.table_update(table);
                             });
                     } 
                },
                { id: "print", text: _("Print"), icon: "print", enabled: "multi", tooltip: _("Print selected forms"), 
                    click: function() {
                        common.route("onlineform_incoming_print?ajax=false&mode=print&ids=" + encodeURIComponent(tableform.table_ids(table)));
                    }
                },
                { id: "attach", icon: "link", text: _("Attach"), enabled: "one", type: "buttonmenu" },
                { id: "create", icon: "complete", text: _("Create"), enabled: "multi", type: "buttonmenu" }

            ];
            this.table = table;
            this.buttons = buttons;
        },

        render_buttonmenus: function() {
            var h = [
                '<div id="button-attach-body" class="asm-menu-body">',
                '<ul class="asm-menu-list">',
                    '<li id="button-attachperson" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("person-find") + ' ' + _("Person") + '</a></li>',
                    '<li id="button-attachanimal" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("animal-find") + ' ' + _("Animal") + '</a></li>',
                '</ul>',
                '</div>',
                '<div id="button-create-body" class="asm-menu-body">',
                '<ul class="asm-menu-list">',
                    '<li id="button-animal" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("animal-find") + ' ' + _("Animal") + '</a></li>',
                    '<li id="button-person" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("person-add") + ' ' + _("Person") + '</a></li>',
                    '<li id="button-lostanimal" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("animal-lost-add") + ' ' + _("Lost Animal") + '</a></li>',
                    '<li id="button-foundanimal" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("animal-found-add") + ' ' + _("Found Animal") + '</a></li>',
                    '<li id="button-incident" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("call") + ' ' + _("Incident") + '</a></li>',
                    '<li id="button-transport" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("transport") + ' ' + _("Transport") + '</a></li>',
                    '<li id="button-waitinglist" class="asm-menu-item"><a '
                        + '" href="#">' + html.icon("waitinglist") + ' ' + _("Waiting List") + '</a></li>',
                '</ul>',
                '</div>'

            ];
            return h.join("\n");
        },

        bind_buttonmenus: function() {
            $("#button-attachperson").click(function() {
                $("#dialog-attach-person").dialog("open");
            });
            $("#button-attachanimal").click(function() {
                $("#dialog-attach-animal").dialog("open");
            });
            $("#button-animal").click(function() {
                onlineform_incoming.create_record("animal", "animal");
            });
            $("#button-person").click(function() {
                onlineform_incoming.create_record("person", "person");
            });
            $("#button-lostanimal").click(function() {
                onlineform_incoming.create_record("lostanimal", "lostanimal");
            });
            $("#button-foundanimal").click(function() {
                onlineform_incoming.create_record("foundanimal", "foundanimal");
            });
            $("#button-incident").click(function() {
                onlineform_incoming.create_record("incident", "incident");
            });
            $("#button-transport").click(function() {
                onlineform_incoming.create_record("transport", "animal_transport");
            });
            $("#button-waitinglist").click(function() {
                onlineform_incoming.create_record("waitinglist", "waitinglist");
            });
        },

        render_viewer: function() {
            return [
                '<div id="dialog-viewer" style="display: none" title="' + html.title(_("View")) + '">',
                '<div id="dialog-viewer-content">',
                '</div>',
                '</div>'
            ].join("\n");
        },

        bind_viewer: function() {
            var viewbuttons = {};
            viewbuttons[_("Close")] = function() { $(this).dialog("close"); };
            $("#dialog-viewer").dialog({
                autoOpen: false,
                resizable: true,
                height: "auto",
                width: 760,
                modal: true,
                dialogClass: "dialogshadow",
                show: dlgfx.add_show,
                hide: dlgfx.add_hide,
                buttons: viewbuttons
            });

        },


        render_attach_person: function() {
            return [
                '<div id="dialog-attach-person" style="display: none" title="' + html.title(_("Select a person")) + '">',
                '<div class="ui-state-highlight ui-corner-all" style="margin-top: 20px; padding: 0 .7em">',
                '<p><span class="ui-icon ui-icon-info" style="float: left; margin-right: .3em;"></span>',
                _("Select a person to attach this form to."),
                '</p>',
                '</div>',
                html.capture_autofocus(),
                '<table width="100%">',
                '<tr>',
                '<td><label for="attachperson">' + _("Person") + '</label></td>',
                '<td>',
                '<input id="attachperson" data="attachperson" type="hidden" class="asm-personchooser" value="" />',
                '</td>',
                '</tr>',
                '</table>',
                '</div>'
            ].join("\n");
        },

        render_attach_animal: function() {
            return [
                '<div id="dialog-attach-animal" style="display: none" title="' + html.title(_("Select an animal")) + '">',
                '<div class="ui-state-highlight ui-corner-all" style="margin-top: 20px; padding: 0 .7em">',
                '<p><span class="ui-icon ui-icon-info" style="float: left; margin-right: .3em;"></span>',
                _("Select an animal to attach this form to."),
                '</p>',
                '</div>',
                html.capture_autofocus(),
                '<table width="100%">',
                '<tr>',
                '<td><label for="attachanimal">' + _("Animal") + '</label></td>',
                '<td>',
                '<input id="attachanimal" data="attachanimal" type="hidden" class="asm-animalchooser" value="" />',
                '</td>',
                '</tr>',
                '</table>',
                '</div>'
            ].join("\n");
        },

        bind_attach_person: function() {
            var ab = {}, table = onlineform_incoming.table; 
            ab[_("Attach")] = function() { 
                if (!validate.notblank(["attachperson"])) { return; }
                var formdata = "mode=attachperson&personid=" + $("#attachperson").val() + "&collationid=" + tableform.table_selected_row(table).COLLATIONID;
                common.ajax_post("onlineform_incoming", formdata)
                    .then(function() { 
                        var personname = $("#attachperson").closest("td").find(".asm-embed-name").html();
                        header.show_info(_("Successfully attached to {0}").replace("{0}", personname));
                        tableform.table_selected_row(table).LINK = 
                            '<a target="_blank" href="person_media?id=' + $("#attachperson").val() + '">' + personname + '</a>';
                        tableform.table_update(table);
                    })
                    .always(function() {
                        $("#dialog-attach-person").dialog("close");
                    });
            };
            ab[_("Cancel")] = function() { $(this).dialog("close"); };
            $("#dialog-attach-person").dialog({
                 autoOpen: false,
                 width: 600,
                 resizable: false,
                 modal: true,
                 dialogClass: "dialogshadow",
                 show: dlgfx.delete_show,
                 hide: dlgfx.delete_hide,
                 buttons: ab
            });
        },

        bind_attach_animal: function() {
            var ab = {}, table = onlineform_incoming.table; 
            ab[_("Attach")] = function() { 
                if (!validate.notblank(["attachanimal"])) { return; }
                var formdata = "mode=attachanimal&animalid=" + $("#attachanimal").val() + "&collationid=" + tableform.table_selected_row(table).COLLATIONID;
                common.ajax_post("onlineform_incoming", formdata)
                    .then(function() { 
                        var animalname = $("#attachanimal").closest("td").find(".asm-embed-name").html();
                        header.show_info(_("Successfully attached to {0}").replace("{0}", animalname));
                        tableform.table_selected_row(table).LINK = 
                            '<a target="_blank" href="animal_media?id=' + $("#attachanimal").val() + '">' + animalname + '</a>';
                        tableform.table_update(table);
                    })
                    .always(function() {
                        $("#dialog-attach-animal").dialog("close");
                    });
            };
            ab[_("Cancel")] = function() { $(this).dialog("close"); };
            $("#dialog-attach-animal").dialog({
                 autoOpen: false,
                 width: 600,
                 resizable: false,
                 modal: true,
                 dialogClass: "dialogshadow",
                 show: dlgfx.delete_show,
                 hide: dlgfx.delete_hide,
                 buttons: ab
            });
        },

        /**
         * Make an AJAX post to create a record.
         * mode: The type of record to create - person, lostanimal, foundanimal, waitinglist
         * url:  The url to link to the target created record
         */
        create_record: function(mode, target) {
             header.hide_error();
             var table = onlineform_incoming.table, ids = tableform.table_ids(table);
             common.ajax_post("onlineform_incoming", "mode=" + mode + "&ids=" + ids)
                 .then(function(result) {
                     var selrows = tableform.table_selected_rows(table);
                     $.each(selrows, function(i, v) {
                         $.each(result.split("^$"), function(ir, vr) {
                             var vb = vr.split("|");
                             if (vb[0] == v.COLLATIONID) {
                                 v.LINK = '<a target="_blank" href="' + target + '?id=' + vb[1] + '">' + vb[2] + '</a>';
                             }
                         });
                     });
                     tableform.table_update(table);
                 });
        },

        render: function() {
            var s = "";
            this.model();
            s += this.render_viewer();
            s += this.render_attach_person();
            s += this.render_attach_animal();
            s += this.render_buttonmenus();
            s += html.content_header(_("Incoming Forms"));
            s += html.info(_("Incoming forms are online forms that have been completed and submitted by people on the web.") + 
                "<br />" + _("You can use incoming forms to create new records or attach them to existing records."));
            s += tableform.buttons_render(this.buttons);
            s += tableform.table_render(this.table);
            s += html.content_footer();
            return s;
        },

        bind: function() {
            tableform.buttons_bind(this.buttons);
            tableform.table_bind(this.table, this.buttons);
            this.bind_viewer();
            this.bind_attach_animal();
            this.bind_attach_person();
            this.bind_buttonmenus();
        },

        sync: function() {
        },

        destroy: function() {
            common.widget_destroy("#dialog-viewer");
            common.widget_destroy("#dialog-attach-animal");
            common.widget_destroy("#dialog-attach-person");
            common.widget_destroy("#attachanimal", "animalchooser");
            common.widget_destroy("#attachperson", "personchooser");
        },


        name: "onlineform_incoming",
        animation: "formtab",
        title: function() { return _("Incoming Forms"); },
        routes: {
            "onlineform_incoming": function() { common.module_loadandstart("onlineform_incoming", "onlineform_incoming"); }
        }

    };

    common.module_register(onlineform_incoming);

});
