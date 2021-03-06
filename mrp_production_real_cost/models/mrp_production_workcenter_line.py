# -*- coding: utf-8 -*-
# © 2014-2015 Avanzosc
# © 2014-2015 Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import api, fields, models
from openerp.tools.translate import _


class MrpProductionWorkcenterLine(models.Model):

    _inherit = 'mrp.production.workcenter.line'

    pre_cost = fields.Float('Pre-Operation Cost')
    post_cost = fields.Float('Post-Operation Cost')

    @api.multi
    def _create_analytic_line(self):
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        task_obj = self.env['project.task']
        if self.workcenter_id.costs_hour > 0.0:
            hour_uom = self.env.ref('product.product_uom_hour', False)
            operation_line = self.operation_time_lines[-1]
            production = self.production_id
            workcenter = self.workcenter_id
            product = workcenter.product_id
            journal_id = workcenter.costs_journal_id or self.env.ref(
                'mrp.analytic_journal_machines', False)
            name = "-".join([production.name or '',
                             workcenter.code or '',
                             self.routing_wc_line.routing_id.code or '',
                             product.default_code or '',
                             _('HOUR')])
            general_acc = workcenter.costs_general_account_id or False
            price = -(workcenter.costs_hour * operation_line.uptime)
            if price:
                analytic_vals = production._prepare_real_cost_analytic_line(
                    journal_id, name, production, product,
                    general_account=general_acc, workorder=self,
                    qty=operation_line.uptime, amount=price)
                task = task_obj.search(
                    [('mrp_production_id', '=', production.id),
                     ('workorder', '=', False)])
                analytic_vals['task_id'] = task and task[0].id or False
                analytic_vals['product_uom_id'] = hour_uom.id
                analytic_vals['ref'] = workcenter.costs_hour_account_id.name
                analytic_line_obj.create(analytic_vals)

    @api.multi
    def _create_pre_post_cost_lines(self, cost_type='pre'):
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        task_obj = self.env['project.task']
        hour_uom = self.env.ref('product.product_uom_hour', False)
        production = self.production_id
        workcenter = self.workcenter_id
        journal_id = workcenter.costs_journal_id or self.env.ref(
            'mrp.analytic_journal_machines', False)
        general_acc = workcenter.costs_general_account_id or False
        qty = 0
        price = 0
        product = False
        name = ''
        if cost_type == 'pre':
            product = workcenter.pre_op_product
            name = "-".join([production.name or '',
                             workcenter.code or '',
                             self.routing_wc_line.routing_id.code or '',
                             product.default_code or '',
                             _('PRE')])
            price = -self.pre_cost
            qty = self.time_start
        elif cost_type == 'post':
            product = workcenter.post_op_product
            name = "-".join([production.name or '',
                             workcenter.code or '',
                             self.routing_wc_line.routing_id.code or '',
                             product.default_code or '',
                             _('POST')])
            price = -self.post_cost
            qty = self.time_stop
        if price:
            analytic_vals = production._prepare_real_cost_analytic_line(
                journal_id, name, production, product,
                general_account=general_acc, workorder=self,
                qty=qty, amount=price)
            task = task_obj.search([('mrp_production_id', '=', production.id),
                                    ('workorder', '=', False)])
            analytic_vals['task_id'] = task[:1].id
            analytic_vals['product_uom_id'] = hour_uom.id
            analytic_line_obj.create(analytic_vals)

    @api.multi
    def action_start_working(self):
        result = super(MrpProductionWorkcenterLine,
                       self).action_start_working()
        self._create_pre_post_cost_lines(cost_type='pre')
        return result

    @api.multi
    def action_pause(self):
        result = super(MrpProductionWorkcenterLine, self).action_pause()
        self._create_analytic_line()
        return result

    @api.multi
    def action_done(self):
        not_paused_records = self.filtered(lambda x: x.state != 'pause')
        not_paused_records._write_end_date_operation_line()
        self._create_analytic_line()
        self._create_pre_post_cost_lines(cost_type='post')
        result = super(MrpProductionWorkcenterLine, self).action_done()
        return result
