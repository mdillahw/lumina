# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import datetime

class MrpWizard(models.TransientModel):
    _name = 'mrp.wizard'

    def _get_default_line_ids(self):        
        result = []
        if self._context.get('active_ids'):
            mrp_production = self.env['mrp.production'].search([('id','in',self._context.get('active_ids'))])
            for mrp in mrp_production:
                if mrp.manufacture_info_id.is_printing:
                    result.append([0,False,{'progress':'Printing','quantity':mrp.product_qty,'temp_progress':'Printing','temp_quantity':mrp.product_qty,'qty_done':0.0,'qty_waste':0.0}])
                if mrp.manufacture_info_id.is_dry_lamination:
                    result.append([0,False,{'progress':'Dry Lamination','quantity':mrp.product_qty,'temp_progress':'Dry Lamination','temp_quantity':mrp.product_qty,'qty_done':0.0,'qty_waste':0.0}])
                if mrp.manufacture_info_id.is_extrusi:
                    result.append([0,False,{'progress':'Extrusi','quantity':mrp.product_qty,'temp_progress':'Extrusi','temp_quantity':mrp.product_qty,'qty_done':0.0,'qty_waste':0.0}])
                if mrp.manufacture_info_id.is_slitting:
                    result.append([0,False,{'progress':'Slitting','quantity':mrp.product_qty,'temp_progress':'Slitting','temp_quantity':mrp.product_qty,'qty_done':0.0,'qty_waste':0.0}])
                if mrp.manufacture_info_id.is_bag_making:
                    result.append([0,False,{'progress':'Bag Making','quantity':mrp.product_qty,'temp_progress':'Bag Making','temp_quantity':mrp.product_qty,'qty_done':0.0,'qty_waste':0.0}])


        return result

    line_ids = fields.One2many('mrp.wizard.line','wizard_id',default=_get_default_line_ids)


    @api.multi
    def create_progress(self):        
        if self._context.get('active_ids'):
            mrp_production = self.env['mrp.production'].search([('id','in',self._context.get('active_ids'))])
            for mrp in mrp_production:
                for line in self.line_ids:
                    self.env['mrp.progress'].create({
                            'mrp_id' : mrp.id,
                            'progress' : line.progress,
                            'quantity' : line.quantity,
                            'qty_done' : line.qty_done,
                            'qty_waste' : line.qty_waste
                        })
        return True

class MrpWizardLine(models.TransientModel):
    _name = 'mrp.wizard.line'

    wizard_id = fields.Many2one('mrp.wizard')
    progress = fields.Char('Progress')
    quantity = fields.Float('Quantity')
    temp_progress = fields.Char('Progress')
    temp_quantity = fields.Float('Quantity')
    qty_done = fields.Float('Done')
    qty_waste = fields.Float('Waste')

class MrpProgress(models.Model):
    _name = 'mrp.progress'
    _order = 'id'

    mrp_id = fields.Many2one('mrp.production','Origin')
    date = fields.Datetime('Date',default=fields.Datetime.now)
    progress = fields.Char('Progress')
    quantity = fields.Float('Quantity')
    qty_done = fields.Float('Done')
    qty_waste = fields.Float('Waste')

class CustomManufacture(models.Model):
    _inherit = 'mrp.production'

    sale_order_line_id = fields.Many2one('sale.order.line')
    manufacture_info_id = fields.Many2one('sale.order.line.manufacture.info')
    check_to_done_partialy = fields.Boolean(compute="_compute_done_partialy", string="Check Produced Qty", 
        help="Technical Field to see if we can show 'Mark as Done Partially' button")
    mrp_progress_ids = fields.One2many('mrp.progress','mrp_id')


    @api.model
    def create(self, values):
        manufacture_info_id = 0
        sale_order_line_id = 0
        if 'origin' in values and values['origin'] != '':
            record = self.env['sale.order.line'].search([('order_id.name','=',values['origin']),('product_id','=',values['product_id']),('product_uom_qty','=',values['product_qty'])])
            for r in record:
                manufacture_info_id = r.custom_id.id
                sale_order_line_id = r.id
        if manufacture_info_id > 0:
            values['manufacture_info_id'] = manufacture_info_id
        if sale_order_line_id > 0:
            values['sale_order_line_id'] = sale_order_line_id
        return super(CustomManufacture,self).create(values)

    
    @api.multi
    def button_sale_line(self):
        id = 0
        '''for r in self:
            order_line_id = r.sale_order_line_id.id
            record = self.env['sale.order.line.manufacture.info'].search([('order_line_id','=',order_line_id)])
            for data in record:
                id = data.id
        '''
        #sale_order = self.env['sale.order'].search([('name','=',self.origin)])
        # order_line = self.env['sale.order.line'].search([('id','=',self.sale_order_line_id.id)])
        id = self.manufacture_info_id.id
        view = {
            'name': 'Manufacture Orders Information',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.line.manufacture.info',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'readonly': False,
            'res_id': id,
        }
        return view

    @api.multi
    def set_progress(self):
        view = {
            'name': 'Input Progress',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.wizard',
            'src_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'readonly': False,
        }
        return view

    @api.multi
    @api.depends('workorder_ids.state', 'move_finished_ids', 'is_locked')
    def _compute_done_partialy(self):
        for production in self:
            done_moves = production.move_finished_ids.filtered(lambda x: x.state != 'cancel' and x.product_id.id == production.product_id.id)
            qty_produced = sum(done_moves.mapped('quantity_done'))
            wo_done = True
            if any([x.state not in ('done', 'cancel') for x in production.workorder_ids]):
                wo_done = False
            production.check_to_done_partialy = production.is_locked and done_moves and (production.state not in ('done', 'cancel')) and wo_done
            
        return True

    @api.multi
    def button_mark_done(self):
        new_qty = 0
        finish_qty_done = 0
        for r in self: 
            if not r.check_to_done:               
                for finished_ids in r.finished_move_line_ids:
                    finish_qty_done += finished_ids.qty_done

                new_qty = r.product_qty - finish_qty_done
                current_production = super(CustomManufacture,self).button_mark_done()
                new_production = super(CustomManufacture,self).create({
                    'origin' : r.name,
                    'product_id' : r.product_id.id,
                    'product_tmpl_id' : r.product_tmpl_id.id,
                    'product_qty' : new_qty,
                    'product_uom_id' : r.product_uom_id.id,
                    'picking_type_id' : r.picking_type_id.id,
                    'location_src_id' : r.location_src_id.id,
                    'location_dest_id' : r.location_dest_id.id,
                    'date_planned_start' : r.date_planned_start,
                    'date_planned_finished' : r.date_planned_finished,
                    'date_start' : r.date_start,
                    'date_finished' : r.date_finished,
                    'bom_id' : r.bom_id.id,
                    'routing_id' : r.routing_id.id,
                    'procurement_group_id' : r.procurement_group_id.id,
                    'propagate' : r.propagate,
                    'production_location_id' : r.production_location_id.id,
                    'sale_order_line_id' : r.sale_order_line_id.id,
                    'manufacture_info_id': r.manufacture_info_id.id
                })

                for line in r.mrp_progress_ids:
                    self.env['mrp.progress'].create({
                            'mrp_id' : new_production.id,
                            'date' : line.date,
                            'progress' : line.progress,
                            'quantity' : line.quantity,
                            'qty_done' : line.qty_done,
                            'qty_waste' : line.qty_waste
                        })


                return current_production

            else:
                return super(CustomManufacture,self).button_mark_done()
        