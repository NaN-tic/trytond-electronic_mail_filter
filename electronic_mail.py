# This file is part of electronic_mail_filter module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval
from trytond.transaction import Transaction


__all__ = ['ElectronicMailFilter', 'SearchingStart']
__metaclass__ = PoolMeta


class ElectronicMailFilter(ModelSQL, ModelView):
    'eMail Filter'
    __name__ = 'electronic.mail.filter'

    name = fields.Char('Name', required=True,
        help='Name of the cron for sending Email.')
    template = fields.Many2One('electronic.mail.template', 'eMail Template',
        required=True)
    model = fields.Function(fields.Many2One('ir.model', 'Model'),
        'on_change_with_model')
    cron = fields.Many2One('ir.cron', 'Cron', readonly=True)
    active = fields.Boolean('Active')
    profile = fields.Many2One('searching.profile', 'Profile',
        domain=[
            ('model', '=', Eval('model')),
            ],
        context={
            'model': Eval('model'),
            },
        depends=['model'])
    last_send = fields.DateTime('Last Send', required=True)
    manual = fields.Boolean('Manual')
    source = fields.Text('Source',
        states={
            'readonly': Bool(Eval('manual')) == False,
            'required': Bool(Eval('manual')) == True,
            }, depends=['manual'],
        help='Available global variables:\n'
            '\tself: Instance of this model.\n'
            '\tpool: Instance of Pool that allows get access to any model '
                'of database.\n'
            'Returns `records`: List of records you want to select.')
    mix_operator = fields.Selection([
            ('all', 'All'),
            ('any', 'Any'),
            ], 'Mix operator',
        states={
            'readonly': Bool(Eval('manual')) == False,
            },
        help='Operator to mix the records obtained through the filters in the '
            'first tab and records calculated by the manual code.')

    @classmethod
    def __setup__(cls):
        super(ElectronicMailFilter, cls).__setup__()
        cls._error_messages.update({
                'filter_error': 'Manual filter error:\n%s',
                'filter_success': 'Filter obtained these records:\n%s',
                'filter_without_errors': 'Filter ended without errors, but do '
                    'not obtained any records.',
                'details': 'Details:\n%s',
                })
        cls._buttons.update({
                'test_profile': {
                    },
                'send_emails': {
                    },
                'create_cron': {
                    'invisible': Bool(Eval('cron')) == True,
                    },
                'delete_cron': {
                    'invisible': Bool(Eval('cron')) == False,
                    },
                })

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_mix_operator():
        return 'all'

    @staticmethod
    def default_last_send():
        return datetime.now()

    @fields.depends('template')
    def on_change_with_model(self, name=None):
        if self.template:
            return self.template.model.id

    @classmethod
    @ModelView.button
    def create_cron(cls, filters):
        pool = Pool()
        Cron = pool.get('ir.cron')
        User = pool.get('res.user')
        cron_user, = User.search([
                ('active', '=', False),
                ('login', '=', 'user_cron_trigger'),
                ])
        admin_user, = User.search([('login', '=', 'admin')])
        args = []
        vlist = []
        for filter_ in filters:
            vlist = [{
                'name': filter_.name,
                'user': cron_user.id,
                'request_user': admin_user.id,
                'active': True,
                'interval_number': 1,
                'interval_type': 'days',
                'number_calls':-1,
                'next_call': datetime.now(),
                'model': 'electronic.mail.filter',
                'function': 'send_emails',
                'args': '(%s,)' % filter_.id,
                }]
            cron, = Cron.create(vlist)
            args.extend(([filter_], {'cron': cron}))
        cls.write(*args)

    @classmethod
    @ModelView.button
    def delete_cron(cls, filters):
        Cron = Pool().get('ir.cron')
        crons = [f.cron for f in filters]
        Cron.delete(crons)

    @classmethod
    @ModelView.button_action(
        'searching.act_searching')
    def test_profile(cls, filters):
        pass

    def search_records(self):
        Model = Pool().get(self.model.model)
        domain = self.profile.get_domain()
        try:
            records = Model.search(domain)
        except (SyntaxError, NameError, IndexError, AttributeError), exc:
            self.raise_user_error('filter_error', exc)
        return records

    @classmethod
    @ModelView.button
    def send_emails(cls, filters):
        Template = Pool().get('electronic.mail.template')
        if isinstance(filters, int):
            filters = cls.search([
                    ('id', '=', filters),
                    ])
        for filter_ in filters:
            records = filter_.search_records()
            Template.render_and_send(filter_.template.id, records)


class SearchingStart:
    __name__ = 'searching.start'

    @staticmethod
    def default_profile():
        context = Transaction().context
        active_id = context.get('active_id')
        filter_ = Pool().get('electronic.mail.filter')(active_id)
        if filter_.profile:
            return filter_.profile.id
