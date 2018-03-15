odoo.define('custom_sale.manufacture_info', function (require) {
	"use strict";

	var field_registry = require('web.field_registry');
	var ListView = require('web.ListRenderer');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;
        
    var InheritListView = ListView.include({
    	
        unselectRow: function () {
            var self = this;
            var record = this.state.data[this.currentRow];
            
            return this._super.apply(this, arguments).done(function() {
                 
                 if(record != undefined){
                    
                    if(record.model == 'sale.order.line' && record.data.custom_id == false){   
                        var error = {
                            'data':{
                                'message':'Classification is empty. It is recommended to fill Classification field',
                            }
                        }                     
                        new Dialog(this, {
                            size: 'medium',
                            title: _.str.capitalize(error.type || error.message) || _t("Odoo Warning"),
                            subtitle: error.data.title,
                            $content: $(QWeb.render('CrashManager.warning', {error: error}))
                        }).open();
                    }
                 }
            });
        },

    });

	field_registry.add('manufacture_info', InheritListView);

	return InheritListView;
});