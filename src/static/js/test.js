/*jslint browser: true, forin: true, eqeq: true, white: true, sloppy: true, vars: true, nomen: true */
/*global $, jQuery, _, asm, common, config, controller, dlgfx, edit_header, format, header, html, tableform, validate */

$(function() {

    var test = {

        lastanimal: null,
        lastvet: null,

        model: function() {
            var dialog = {
                add_title: _("Add test"),
                edit_title: _("Edit test"),
                edit_perm: 'cat',
                helper_text: _("Tests need an animal and at least a required date."),
                close_on_ok: false,
                use_default_values: false,
                columns: 1,
                width: 500,
                fields: [
                    { json_field: "ANIMALID", post_field: "animal", label: _("Animal"), type: "animal" },
                    { json_field: "ANIMALS", post_field: "animals", label: _("Animals"), type: "animalmulti" },
                    { json_field: "TESTTYPEID", post_field: "type", label: _("Type"), type: "select", 
                        options: { displayfield: "TESTNAME", valuefield: "ID", rows: controller.testtypes }},
                    { json_field: "DATEREQUIRED", post_field: "required", label: _("Required"), type: "date", validation: "notblank" },
                    { json_field: "DATEOFTEST", post_field: "given", label: _("Performed"), type: "date" },
                    { json_field: "TESTRESULTID", post_field: "result", label: _("Result"), type: "select", 
                        options: { displayfield: "RESULTNAME", valuefield: "ID", rows: controller.testresults }},
                    { json_field: "ADMINISTERINGVETID", post_field: "administeringvet", label: _("Administering Vet"), type: "person", personfilter: "vet" },
                    { json_field: "COST", post_field: "cost", label: _("Cost"), type: "currency", hideif: function() { return !config.bool("ShowCostAmount"); } },
                    { json_field: "COSTPAIDDATE", post_field: "costpaid", label: _("Paid"), type: "date", hideif: function() { return !config.bool("ShowCostPaid"); } },
                    { json_field: "COMMENTS", post_field: "comments", label: _("Comments"), type: "textarea" }
                ]
            };

            var table = {
                rows: controller.rows,
                idcolumn: "ID",
                edit: function(row) {
                    if (controller.animal) {
                        $("#animal").closest("tr").hide();
                    }
                    else {
                        $("#animal").closest("tr").show();
                    }
                    $("#animals").closest("tr").hide();
                    $("#administeringvet").personchooser("clear");
                    test.enable_default_cost = false;
                    tableform.fields_populate_from_json(dialog.fields, row);
                    test.enable_default_cost = true;
                    tableform.dialog_show_edit(dialog, row)
                        .then(function() {
                            tableform.fields_update_row(dialog.fields, row);
                            test.set_extra_fields(row);
                            return tableform.fields_post(dialog.fields, "mode=update&testid=" + row.ID, "test");
                        })
                        .then(function(response) {
                            tableform.table_update(table);
                            tableform.dialog_close();
                        })
                        .fail(function(response) {
                            tableform.dialog_enable_buttons();
                        });
                },
                complete: function(row) {
                    if (row.DATEOFTEST) { return true; }
                    return false;
                },
                overdue: function(row) {
                    return !row.DATEOFTEST && format.date_js(row.DATEREQUIRED) < common.today_no_time();
                },
                columns: [
                    { field: "TESTNAME", display: _("Type") },
                    { field: "IMAGE", display: "", 
                        formatter: function(row) {
                            return '<a href="animal?id=' + row.ANIMALID + '"><img src=' + html.thumbnail_src(row, "animalthumb") + ' style="margin-right: 8px" class="asm-thumbnail thumbnailshadow" /></a>';
                        },
                        hideif: function(row) {
                            // Don't show this column if we're in an animal record, or the option is turned off
                            if (controller.animal || !config.bool("PicturesInBooks")) {
                                return true;
                            }
                        }
                    },
                    { field: "ANIMAL", display: _("Animal"), 
                        formatter: function(row) {
                            return html.animal_link(row, { noemblems: controller.name == "animal_test" });
                        },
                        hideif: function(row) {
                            // Don't show for animal records
                            if (controller.animal) { return true; }
                        }
                    },
                    { field: "ACCEPTANCENUMBER", display: _("Litter"),
                        hideif: function(row) {
                            return config.bool("DontShowLitterID");
                        }
                    },
                    { field: "LOCATIONNAME", display: _("Location"),
                        formatter: function(row) {
                            var s = row.LOCATIONNAME;
                            if (row.LOCATIONUNIT) {
                                s += ' <span class="asm-search-locationunit">' + row.LOCATIONUNIT + '</span>';
                            }
                            if (row.ACTIVEMOVEMENTID && row.CURRENTOWNERID && row.CURRENTOWNERNAME) {
                                s += '<br/>' + html.person_link(row.CURRENTOWNERID, row.CURRENTOWNERNAME);
                            }
                            return s;
                        },
                        hideif: function(row) {
                             // Don't show for animal records
                            if (controller.animal) { return true; }
                        }
                    },
                    { field: "DATEREQUIRED", display: _("Required"), formatter: tableform.format_date, initialsort: true, 
                        initialsortdirection: controller.name == "test" ? "asc" : "desc" },
                    { field: "DATEOFTEST", display: _("Performed"), formatter: tableform.format_date },
                    { field: "RESULTNAME", display: _("Result"), formatter: function(row) {
                            if (row.DATEOFTEST) {
                                return row.RESULTNAME;
                            }
                            return "";
                        }},
                    { field: "ADMINISTERINGVET", display: _("Vet"), 
                        formatter: function(row) {
                            if (!row.ADMINISTERINGVETID) { return ""; }
                            return html.person_link(row.ADMINISTERINGVETID, row.ADMINISTERINGVETNAME);
                        }
                    },
                    { field: "COST", display: _("Cost"), formatter: tableform.format_currency,
                        hideif: function() { return !config.bool("ShowCostAmount"); }
                    },
                    { field: "COSTPAIDDATE", display: _("Paid"), formatter: tableform.format_date,
                        hideif: function() { return !config.bool("ShowCostPaid"); }
                    },
                    { field: "COMMENTS", display: _("Comments") }
                ]
            };

            var buttons = [
                { id: "new", text: _("New Test"), icon: "new", enabled: "always", perm: "aat", 
                     click: function() { test.new_test(); }},
                { id: "bulk", text: _("Bulk Test"), icon: "new", enabled: "always", perm: "cat", 
                    hideif: function() { return controller.animal; }, click: function() { test.new_bulk_test(); }},
                 { id: "delete", text: _("Delete"), icon: "delete", enabled: "multi", perm: "dat", 
                     click: function() { 
                         tableform.delete_dialog()
                             .then(function() {
                                 tableform.buttons_default_state(buttons);
                                 var ids = tableform.table_ids(table);
                                 return common.ajax_post("test", "mode=delete&ids=" + ids);
                             })
                             .then(function() {
                                 tableform.table_remove_selected_from_json(table, controller.rows);
                                 tableform.table_update(table);
                             });
                     } 
                 },
                 { id: "perform", text: _("Perform"), icon: "complete", enabled: "multi", perm: "cat",
                     click: function() {
                        var comments = "";
                        $.each(controller.rows, function(i, v) {
                            if (tableform.table_id_selected(v.ID)) {
                                comments += "[" + v.SHELTERCODE + " - " + v.ANIMALNAME + "] ";
                            }
                        });
                        $("#usagecomments").val(comments);
                        $("#newdate").datepicker("setDate", new Date());
                        $("#testresult").select("firstvalue");
                        $("#usagetype").select("firstvalue");
                        $("#usagedate").datepicker("setDate", new Date());
                        $("#usagedate").closest("tr").hide();
                        $("#quantity").val("0");
                        // Default animal's current vet if set and this is an animal test tab
                        if (controller.animal && controller.animal.CURRENTVETID) { 
                            $("#givenvet").personchooser("loadbyid", controller.animal.CURRENTVETID); 
                        }
                        $("#dialog-given").dialog("open");
                     }
                 },
                 { id: "offset", type: "dropdownfilter", 
                     options: [ "m365|" + _("Due today"), "p7|" + _("Due in next week"), "p31|" + _("Due in next month"), "p365|" + _("Due in next year") ],
                     click: function(selval) {
                        common.route(controller.name + "?offset=" + selval);
                     },
                     hideif: function(row) {
                         // Don't show for animal records
                         if (controller.animal) {
                             return true;
                         }
                     }
                 }
            ];
            this.dialog = dialog;
            this.table = table;
            this.buttons = buttons;
        },

        render: function() {
            var s = "";
            this.model();
            s += tableform.dialog_render(this.dialog);
            s += test.render_givendialog();
            if (controller.animal) {
                s += edit_header.animal_edit_header(controller.animal, "test", controller.tabcounts);
            }
            else {
                s += html.content_header(_("Test Book"));
            }
            s += tableform.buttons_render(this.buttons);
            s += tableform.table_render(this.table);
            s += html.content_footer();
            return s;
        },

        new_test: function() { 
            var dialog = test.dialog, table = test.table;
            tableform.dialog_show_add(dialog, {
                onadd: function() {
                    tableform.fields_post(dialog.fields, "mode=create", "test")
                        .then(function(response) {
                            var row = {};
                            row.ID = response;
                            tableform.fields_update_row(dialog.fields, row);
                            test.set_extra_fields(row);
                            controller.rows.push(row);
                            tableform.table_update(table);
                            tableform.dialog_close();
                        })
                        .fail(function() {
                            tableform.dialog_enable_buttons();   
                        });
                },
                onload: function() {
                    if (controller.animal) {
                        $("#animal").animalchooser("loadbyid", controller.animal.ID);
                        $("#animal").closest("tr").hide();
                    }
                    else {
                        $("#animal").closest("tr").show();
                        $("#animal").animalchooser("clear");
                    }
                    $("#animals").closest("tr").hide();
                    $("#administeringvet").personchooser("clear");
                    $("#dialog-tableform .asm-textbox, #dialog-tableform .asm-textarea").val("");
                    $("#type").select("value", config.str("AFDefaultTestType"));
                    test.enable_default_cost = true;
                    test.set_default_cost();
                }
            });
        },

        new_bulk_test: function() { 
            var dialog = test.dialog, table = test.table;
            tableform.dialog_show_add(dialog, {
                onadd: function() {
                    tableform.fields_post(dialog.fields, "mode=createbulk", "test")
                        .then(function(response) {
                            tableform.dialog_close();
                            common.route_reload();
                        })
                        .fail(function() {
                            tableform.dialog_enable_buttons();   
                        });
                },
                onload: function() {
                    $("#animal").closest("tr").hide();
                    $("#animals").closest("tr").show();
                    $("#animals").animalchoosermulti("clear");
                    $("#dialog-tableform .asm-textbox, #dialog-tableform .asm-textarea").val("");
                    $("#type").select("value", config.str("AFDefaultTestType"));
                    test.enable_default_cost = true;
                    test.set_default_cost();
                }
            });
        },

        render_givendialog: function() {
            return [
                '<div id="dialog-given" style="display: none" title="' + html.title(_("Perform Test")) + '">',
                '<table width="100%">',
                '<tr>',
                '<td><label for="newdate">' + _("Performed") + '</label></td>',
                '<td><input id="newdate" data="newdate" type="textbox" class="asm-textbox asm-datebox asm-field" /></td>',
                '</tr>',
                '<tr>',
                '<td><label for="testresult">' + _("Result") + '</label></td>',
                '<td><select id="testresult" data="testresult" class="asm-selectbox asm-field">',
                html.list_to_options(controller.testresults, "ID", "RESULTNAME"),
                '</select>',
                '</td>',
                '</tr>',
                '<tr>',
                '<td><label for="givenvet">' + _("Administering Vet") + '</label></td>',
                '<td><input id="givenvet" data="givenvet" type="hidden" class="asm-personchooser asm-field" data-filter="vet" /></td>',
                '</tr>',
                '<tr class="tagstock"><td></td><td>' + html.info(_("These fields allow you to deduct stock for the test(s) given. This single deduction should cover the selected tests being performed.")) + '</td></tr>',
                '<tr class="tagstock">',
                '<td><label for="item">' + _("Item") + '</label></td>',
                '<td><select id="item" data="item" class="asm-selectbox asm-field">',
                '<option value="-1">' + _("(no deduction)") + '</option>',
                html.list_to_options(controller.stockitems, "ID", "ITEMNAME"),
                '</select></td>',
                '</tr>',
                '<tr class="tagstock">',
                '<td><label for="quantity">' + _("Quantity") + '</label></td>',
                '<td><input id="quantity" data="quantity" type="textbox" class="asm-textbox asm-numberbox asm-field" /></td>',
                '</tr>',
                '<tr class="tagstock">',
                '<td><label for="usagetype">' + _("Usage Type") + '</label></td>',
                '<td><select id="usagetype" data="usagetype" class="asm-selectbox asm-field">',
                html.list_to_options(controller.stockusagetypes, "ID", "USAGETYPENAME"),
                '</select></td>',
                '</tr>',
                '<tr class="tagstock">',
                '<td><label for="usagedate">' + _("Usage Date") + '</label></td>',
                '<td><input id="usagedate" data="usagedate" class="asm-textbox asm-datebox asm-field" />',
                '</select></td>',
                '</tr>',
                '<tr class="tagstock">',
                '<td><label for="usagecomments">' + _("Comments") + '</label></td>',
                '<td><textarea id="usagecomments" data="usagecomments" class="asm-textarea asm-field"></textarea>',
                '</td>',
                '</tr>',
                '</table>',
                '</div>'
            ].join("\n");
        },

        bind_givendialog: function() {
            var givenbuttons = { };
            var dialog = test.dialog, table = test.table;
            givenbuttons[_("Save")] = function() {
                validate.reset("dialog-given");
                if (!validate.notblank([ "newdate" ])) { return; }
                $("#usagedate").val($("#newdate").val()); // copy given to usage
                $("#dialog-given").disable_dialog_buttons();
                var ids = tableform.table_ids(table);
                common.ajax_post("test", $("#dialog-given .asm-field").toPOST() + "&mode=perform&ids=" + ids)
                    .then(function() {
                        $.each(controller.rows, function(i, t) {
                            if (tableform.table_id_selected(t.ID)) {
                                t.DATEOFTEST = format.date_iso($("#newdate").val());
                                t.TESTRESULTID = $("#testresult").val();
                                t.RESULTNAME = common.get_field(controller.testresults, t.TESTRESULTID, "RESULTNAME");
                            }
                        });
                        tableform.table_update(table);
                    })
                    .always(function() {
                        $("#dialog-given").dialog("close");
                        $("#dialog-given").enable_dialog_buttons();
                    });
            };
            givenbuttons[_("Cancel")] = function() {
                $("#dialog-given").dialog("close");
            };

            $("#dialog-given").dialog({
                autoOpen: false,
                width: 550,
                modal: true,
                dialogClass: "dialogshadow",
                show: dlgfx.edit_show,
                hide: dlgfx.edit_hide,
                buttons: givenbuttons
            });

        },

        bind: function() {
            $(".asm-tabbar").asmtabs();
            tableform.dialog_bind(this.dialog);
            tableform.buttons_bind(this.buttons);
            tableform.table_bind(this.table, this.buttons);
            this.bind_givendialog();

            // When the test type is changed, use the default cost from the test type
            $("#type").change(test.set_default_cost);

            // Remember the currently selected animal when it changes so we can add
            // its name and code to the local set
            $("#animal").bind("animalchooserchange", function(event, rec) { test.lastanimal = rec; });
            $("#animal").bind("animalchooserloaded", function(event, rec) { test.lastanimal = rec; });

            // Same for the vet
            $("#administeringvet").bind("personchooserchange", function(event, rec) { test.lastvet = rec; });
            $("#administeringvet").bind("personchooserloaded", function(event, rec) { test.lastvet = rec; });
            $("#givenvet").bind("personchooserchange", function(event, rec) { test.lastvet = rec; });
            $("#givenvet").bind("personchooserloaded", function(event, rec) { test.lastvet = rec; });

            if (controller.newtest == 1) {
                this.new_test();
            }
        },

        sync: function() {
            // If an offset is given in the querystring, update the select
            if (common.querystring_param("offset")) {
                $("#offset").select("value", common.querystring_param("offset"));
            }
            // Hide stock deductions if stock control is disabled
            if (config.bool("DisableStockControl")) {
                $(".tagstock").hide();
            }
        },

        /** Whether or not we should allow overwriting of the cost */
        enable_default_cost: true,

        /** Sets the default cost based on the selected test type */
        set_default_cost: function() {
            if (!test.enable_default_cost) { return; }
            var seltype = $("#type").val();
            $.each(controller.testtypes, function(i, v) {
                if (seltype == v.ID) {
                    if (v.DEFAULTCOST) {
                        $("#cost").currency("value", v.DEFAULTCOST);
                    }
                    else {
                        $("#cost").currency("value", 0);
                    }
                    return true;
                }
            });
        },

        set_extra_fields: function(row) {
            if (controller.animal) {
                row.LOCATIONUNIT = controller.animal.SHELTERLOCATIONUNIT;
                row.LOCATIONNAME = controller.animal.SHELTERLOCATIONNAME;
                row.ANIMALNAME = controller.animal.ANIMALNAME;
                row.SHELTERCODE = controller.animal.SHELTERCODE;
                row.WEBSITEMEDIANAME = controller.animal.WEBSITEMEDIANAME;
            }
            else if (test.lastanimal) {
                // Only switch the location for new records to prevent
                // movementtypes being changed to internal locations on existing records
                if (!row.LOCATIONNAME) {
                    row.LOCATIONUNIT = test.lastanimal.SHELTERLOCATIONUNIT;
                    row.LOCATIONNAME = test.lastanimal.SHELTERLOCATIONNAME;
                }
                row.ANIMALNAME = test.lastanimal.ANIMALNAME;
                row.SHELTERCODE = test.lastanimal.SHELTERCODE;
                row.WEBSITEMEDIANAME = test.lastanimal.WEBSITEMEDIANAME;
            }
            row.TESTNAME = common.get_field(controller.testtypes, row.TESTTYPEID, "TESTNAME");
            row.RESULTNAME = common.get_field(controller.testresults, row.TESTRESULTID, "RESULTNAME");
            row.ADMINISTERINGVETNAME = "";
            if (row.ADMINISTERINGVETID && test.lastvet) { row.ADMINISTERINGVETNAME = test.lastvet.OWNERNAME; }
        },

        destroy: function() {
            common.widget_destroy("#dialog-given");
            common.widget_destroy("#animal");
            common.widget_destroy("#animals");
            common.widget_destroy("#administeringvet");
            tableform.dialog_destroy();
            this.lastanimal = null;
            this.lastvet = null;
        },

        name: "test",
        animation: function() { return controller.name == "test" ? "book" : "formtab"; },
        title:  function() { 
            var t = "";
            if (controller.name == "animal_test") {
                t = common.substitute(_("{0} - {1} ({2} {3} aged {4})"), { 
                    0: controller.animal.ANIMALNAME, 1: controller.animal.CODE, 2: controller.animal.SEXNAME,
                    3: controller.animal.SPECIESNAME, 4: controller.animal.ANIMALAGE }); 
            }
            else if (controller.name == "test") { t = _("Test Book"); }
            return t;
        },

        routes: {
            "animal_test": function() { common.module_loadandstart("test", "animal_test?id=" + this.qs.id); },
            "test": function() { common.module_loadandstart("test", "test?" + this.rawqs); }
        }


    };
    
    common.module_register(test);

});
