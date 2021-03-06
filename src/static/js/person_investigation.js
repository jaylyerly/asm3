/*jslint browser: true, forin: true, eqeq: true, white: true, sloppy: true, vars: true, nomen: true */
/*global $, _, asm, common, config, controller, dlgfx, format, edit_header, html, tableform, validate */

$(function() {

    var person_investigation = {

        model: function() {
            var dialog = {
                add_title: _("Add investigation"),
                edit_title: _("Edit investigation"),
                edit_perm: 'coi',
                helper_text: _("Date and notes are mandatory."),
                close_on_ok: false,
                columns: 1,
                width: 550,
                fields: [
                    { json_field: "DATE", post_field: "date", label: _("Date"), type: "date", validation: "notblank" },
                    { json_field: "NOTES", post_field: "notes", label: _("Notes"), type: "textarea", validation: "notblank" }
                ]
            };

            var table = {
                rows: controller.rows,
                idcolumn: "ID",
                edit: function(row) {
                    tableform.dialog_show_edit(dialog, row)
                        .then(function() {
                            tableform.fields_update_row(dialog.fields, row);
                            return tableform.fields_post(dialog.fields, "mode=update&investigationid=" + row.ID, "person_investigation");
                        })
                        .then(function(response) {
                            tableform.table_update(table);
                            tableform.dialog_close();
                        })
                        .fail(function() {
                            tableform.dialog_enable_buttons();
                        });
                    $("#date").datepicker("hide");
                },
                columns: [
                    { field: "CREATEDBY", display: _("By") },
                    { field: "DATE", display: _("Date"), initialsort: true, initialsortdirection: "desc", formatter: tableform.format_date }, 
                    { field: "NOTES", display: _("Notes") }
                ]
            };

            var buttons = [
                 { id: "new", text: _("New"), icon: "new", enabled: "always", perm: "aoi",
                     click: function() { 
                         $("#date").datepicker("setDate", new Date());
                         $("#date").datepicker("hide");
                         tableform.dialog_show_add(dialog)
                             .then(function() {
                                 return tableform.fields_post(dialog.fields, "mode=create&personid="  + controller.person.ID, "person_investigation");
                             })
                             .then(function(response) {
                                 var row = {};
                                 row.ID = response;
                                 row.CREATEDBY = asm.user;
                                 tableform.fields_update_row(dialog.fields, row);
                                 controller.rows.push(row);
                                 tableform.table_update(table);
                                 tableform.dialog_close();
                             })
                            .fail(function() {
                                tableform.dialog_enable_buttons();
                            });
                     } 
                 },
                 { id: "delete", text: _("Delete"), icon: "delete", enabled: "multi", perm: "doi",
                     click: function() { 
                         tableform.delete_dialog()
                             .then(function() {
                                 tableform.buttons_default_state(buttons);
                                 var ids = tableform.table_ids(table);
                                 return common.ajax_post("person_investigation", "mode=delete&ids=" + ids);
                             })
                             .then(function() {
                                 tableform.table_remove_selected_from_json(table, controller.rows);
                                 tableform.table_update(table);
                             });
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
            s += edit_header.person_edit_header(controller.person, "investigation", controller.tabcounts);
            s += tableform.buttons_render(this.buttons);
            s += tableform.table_render(this.table);
            s += '</div> <!-- asmcontent -->';
            s += '</div> <!-- tabs -->';
            return s;
        },

        bind: function() {
            $(".asm-tabbar").asmtabs();
            tableform.dialog_bind(this.dialog);
            tableform.buttons_bind(this.buttons);
            tableform.table_bind(this.table, this.buttons);
        },

        destroy: function() {
            tableform.dialog_destroy();
        },

        name: "person_investigation",
        animation: "formtab",
        title: function() { return controller.person.OWNERNAME; },
        routes: {
            "person_investigation": function() { common.module_loadandstart("person_investigation", "person_investigation?id=" + this.qs.id); }
        }

    };

    common.module_register(person_investigation);

});
