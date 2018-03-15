# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import datetime

class CustomOrderLineInfo(models.Model):
    _name = 'sale.order.line.manufacture.info'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Manufacture Info"

    @api.model
    def default_get(self,fields):
        res = super(CustomOrderLineInfo,self).default_get(fields)
        if self._context.get('product_id'):
            res['product_id'] = self._context['product_id']
            product_line = self.env['product.product'].search([('id','=',res['product_id'])])
            res['template_id'] = product_line.product_tmpl_id.id
        return res

    template_id = fields.Many2one('product.template')
    product_id = fields.Many2one('product.product')
    name = fields.Char()
    order_line_id = fields.Many2one('sale.order.line')
    length = fields.Float(track_visibility='onchange')
    width = fields.Float(track_visibility='onchange')
    description = fields.Text(track_visibility='onchange')
    is_printing = fields.Boolean(string='Printing')
    is_dry_lamination = fields.Boolean(string='Dry Lamination')
    is_extrusi = fields.Boolean(string='Extrusi')
    is_slitting = fields.Boolean(string='Slitting')
    is_bag_making = fields.Boolean(string='Bag Making')
    date_order = fields.Datetime(compute='compute_info',store=False)
    mo_number = fields.Char(compute='compute_info',store=False)
    product_name = fields.Char(compute='compute_info',store=False)
    origin = fields.Char(compute='compute_info',store=False)
    sales_person = fields.Char(compute='compute_info',store=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = '(L:' + str(record.length) + ',W:' + str(record.width) + ') '
            if record.is_printing:
                name += 'Printing, '
            if record.is_dry_lamination:
                name += 'Dry Lamination, '
            if record.is_extrusi:
                name += 'Extrusi, '
            if record.is_slitting:
                name += 'Slitting, '
            if record.is_bag_making:
                name += 'Bag Making '
            result.append((record.id,name))
        return result

    @api.one
    def compute_info(self):
        mo_number = ''
        mo_origin = ''        
        order_line_id = {}
        sale_order_lines = self.env['sale.order.line'].search([('custom_id','=',self.id)])
        for line in sale_order_lines:
            order_line_id = line
        if order_line_id:
            mos = self.env['mrp.production'].search([('sale_order_line_id','=',order_line_id.id)],limit=1)
            for mo in mos:
                mo_number = mo.name

            self.mo_number = mo_number
            self.date_order = order_line_id.order_id.date_order            
            self.origin = order_line_id.order_id.name
            self.sales_person = order_line_id.order_id.user_id.name
        else:
            mos = self.env['mrp.production'].search([('manufacture_info_id','=',self.id)],limit=1)
            for mo in mos:
                mo_number = mo.name
                mo_origin = mo.origin
            self.mo_number = mo_number         
            self.origin = mo_origin
        self.product_name = self.product_id.name

    @api.multi
    def action_confirm(self):
        self.write({'state':'confirmed'})
        return True
        
    @api.multi
    def write(self,vals):
        if not vals.get('state'):
            sale_order_lines = self.env['sale.order.line'].search([('custom_id','=',self.id)])
            for line in sale_order_lines:
                line.order_id.write({'is_classification_has_edited':True})

        return super(CustomOrderLineInfo,self).write(vals)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_normal_confirm_sale = fields.Boolean(compute="compute_confirm_sale")
    is_warning_confirm_sale = fields.Boolean(compute="compute_confirm_sale")
    is_classification_has_edited = fields.Boolean(default=False)

    @api.multi
    @api.depends('order_line')
    def compute_confirm_sale(self):
        if self.state in ['draft','sent']:
            result = True
            for line in self.order_line:
                if not line.custom_id:
                    result = False
            if result:
                self.is_normal_confirm_sale = True
                self.is_warning_confirm_sale = False
            else:
                self.is_normal_confirm_sale = False
                self.is_warning_confirm_sale = True
        else:
            self.is_normal_confirm_sale = False
            self.is_warning_confirm_sale = False
        

        
class CustomOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    #line_info_id = fields.One2many('sale.order.line.manufacture.info','order_line_id')

    @api.model
    def create(self,values):        
        order_line = super(CustomOrderLine,self).create(values)
        #order_line.generate_manufacture_info()
        return order_line

    @api.multi
    def generate_manufacture_info(self):
        data = {
            'order_line_id' : self.id,
            'name' : self.name,
            'length' : 0,
            'width' : 0,
            'description' : '',
            'mo_route' : 'printing',
            'product_id' : self.product_id.id,
            'template_id' : self.product_id.product_tmpl_id.id
        }
        return self.env['sale.order.line.manufacture.info'].create(data)

    @api.multi
    def button_detail(self):
        id = 0
        for r in self.line_info_id:
            id = r.id
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

    custom_id = fields.Many2one('sale.order.line.manufacture.info', 'Classification', domain="[('product_id', '=', product_id)]")
    
    '''@api.multi
    def button_detail_history(self):
        treeview_id = self.env.ref('custom_sale.product_custom_history_tree')
        ids = []
        lines = self.env['sale.order.line.manufacture.info'].search([('product_id','=',self.product_id.id)])
        for line in lines:
            ids.append(line.id)
        domain = [('id','in',ids)]
        view = {
            'type': 'ir.actions.act_window',
            'name': 'Manufacture Orders History',
            'res_model': 'sale.order.line.manufacture.info',
            'view_type': 'form',
            'view_mode': 'tree',
            'view_id': treeview_id.id,
            'target': 'new',
            'readonly': True,
            'domain' : domain
        }
        return view'''

class CustomProduct(models.Model):
    _inherit = 'product.product'
    manufacture = fields.One2many('sale.order.line.manufacture.info','product_id',string='Manufacture')

class CustomTemplate(models.Model):
    _inherit = 'product.template'
    manufacture = fields.One2many('sale.order.line.manufacture.info','template_id',string='Template')