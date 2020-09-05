from odoo import models, fields, api, exceptions
from odoo11.odoo.addons import decimal_precision as dp
from odoo.fields import Date as fDate
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.tools.translate import _


class LibraryBook(models.Model):

    _name = "library.book"
    _description = "Library Book"
    _order = 'date_release desc, name'
    _rec_name = 'short_name'

    name = fields.Char("Title", required=True)
    isbn = fields.Char('ISBN')
    date_release = fields.Date("Release Date")
    author_ids = fields.Many2many('res.partner', string='Authors')
    short_name = fields.Char(string='Short Title', required=True, )
    notes = fields.Text('Internal Notes')
    state = fields.Selection([('draft', 'Not Available'), ('available', 'Available'), ('lost', 'Lost')], 'State')
    description = fields.Html(string='Description',
                              sanitize=True,
                              strip_style=False,
                              translate=False, )
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of Print?')
    date_release = fields.Date('Release Date')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer(string='Number of Pages', default=0,
                           help='Total book page count',
                           groups='base.group_user',
                           states={'lost': [('readonly', True)]}, copy=True,
                           index=False,
                           readonly=False,
                           required=False,
                           company_dependent=False, )
    reader_rating = fields.Float('Reader Average Rating', digits=(14, 4))
    cost_price = fields.Float('Book Cost', dp.get_precision('Book Price'))
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary('Retail Price', currency_field='currency_id', )
    publisher_id = fields.Many2one('res.partner', string='Publisher', ondelete='set null', )
    publisher_city = fields.Char('Publisher City',
                                 related='publisher_id.city',
                                 readonly=True)

    age_days = fields.Float(
        string='Days Since Release',
        compute='_compute_age',
        inverse='_inverse_age',
        search='_search_age',
        store=False,
        compute_sudo=False,
    )

    ref_doc_id = fields.Reference(
        selection='_referencable_models',
        string='Reference Document')

    manager_remarks = fields.Text('Manager Remarks')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE (name)',
         'Book title must be unique.')
    ]

    _sql_constraints = [
        ('shortname_unique',
         'UNIQUE (short_name)',
         'Book Short Name must be unique.')
    ]

    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if (record.date_release and
                    record.date_release > fields.Date.today()):
                raise models.ValidationError('Release date must be in the past')

    @api.depends('date_release')
    def _compute_age(self):
        today = fDate.from_string(fDate.today())
        for book in self.filtered('date_release'):
            try:
                delta = (today - fDate.from_string(book.date_release))
                book.age_days = delta.days
            except (IOError, OSError) as exc:
                message = _('Unable to compute age days') % exc
                raise UserError(message)

    def _inverse_age(self):
        today = fDate.from_string(fDate.context_today(self))
        for book in self.filtered('date_release'):
            try:
                d = today - timedelta(days=book.age_days)
                book.date_release = fDate.to_string(d)
            except (IOError, OSError) as exc:
                message = _('Unable to inverse age') % exc
                raise UserError(message)

    def _search_age(self, operator, value):
        try:
            today = fDate.from_string(fDate.context_today(self))
            value_days = timedelta(days=value)
            value_date = fDate.to_string(today - value_days)
            operator_map = {'>': '<', '>=': '<=', '<': '>', '<=': '>=', }
            new_op = operator_map.get(operator, operator)
            return [('date_release', new_op, value_date)]
        except (IOError, OSError) as exc:
            message = _('Unable to search by age') % exc
            raise UserError(message)

    @api.multi
    def name_get(self):
        result = []
        for book in self:
            authors = book.author_ids.mapped('name')
            name = '%s (%s)' % (book.name, ', '.join(authors))
            result.append((book.id, name))
            return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike',
                     limit=100, name_get_uid=None):
        args = [] if args is None else args.copy()
        if not (name == '' and operator == 'ilike'):
            args += ['|', '|',
                 ('name', operator, name),
                 ('isbn', operator, name),
                 ('author_ids.name', operator, name)
                 ]
        return super(LibraryBook, self)._name_search(
            name='', args=args, operator='ilike',
            limit=limit, name_get_uid=name_get_uid)

    @api.model
    def _referencable_models(self):
        models = self.env['res.request.link'].search([])
        return [(x.object, x.name) for x in models]

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'available'),
                   ('available', 'borrowed'),
                   ('borrowed', 'available'),
                   ('available', 'lost'),
                   ('borrowed', 'lost'),
                   ('lost', 'available')]
        return (old_state, new_state) in allowed

    @api.multi
    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state, new_state):
                book.state = new_state
            else:
                continue

    @api.model
    def get_all_library_members(self):
        library_member_model = self.env['library.member']
        return library_member_model.search([])

    @api.model
    def create(self, values):
        if not self.user_has_groups(
                'library.group_library_manager'):
            if 'manager_remarks' in values:
                raise exceptions.UserError('You are not allowed to modify ''manager_remarks')
            return super(LibraryBook, self).create(values)

    @api.multi
    def write(self, values):
        if not self.user_has_groups('library.group_library_manager'):
            if 'manager_remarks' in values:
                raise exceptions.UserError('You are not allowed to modify ''manager_remarks')
        return super(LibraryBook, self).write(values)

    @api.model
    def fields_get(self,
                   allfields=None,
                   attributes=None):
        fields = super(LibraryBook, self).fields_get(
            allfields=allfields,
            attributes=attributes
        )
        if not self.user_has_groups('library.group_library_manager'):
            if 'manager_remarks' in fields:
                fields['manager_remarks']['readonly'] = True


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _order = 'name'
    _name = 'res.partner'

    name = fields.Char('Name', required=True)
    email = fields.Char('Email')
    date = fields.Date('Date')
    is_company = fields.Boolean(
        'Is a company',
        help="Check if the contact is a company, "
             "otherwise it is a person"
    )
    parent_id = fields.Many2one('res.partner', 'Related Company')
    child_ids = fields.One2many('res.partner', 'parent_id',
                                'Contacts')

    published_book_ids = fields.One2many('library.book', 'publisher_id', string='Published Books')
    authored_book_ids = fields.Many2many('library.book',
                                         string='Authored Books',
                                         relation='library_book_res_partner_rel')
    count_books = fields.Integer('Number of Authored Books',
                                 compute='_compute_count_books')

    def first_val(self):
        today_str = fields.Date.context_today(self)
        val1 = {'name': 'Eric Idle',
                'email': 'eric.idle@example.com',
                'date': today_str}
        val2 = {'name': 'John Cleese',
                'email': 'john.cleese@example.com',
                'date': today_str}
        partner_val = {
            'name': 'Flying Circus',
            'email': 'm.python@example.com',
            'date': today_str,
            'is_company': True,
            'child_ids': [(0, 0, val1),
                          (0, 0, val2),
                          ]}
        record = self.env['res.partner'].create(partner_val)

    @api.model
    def add_contacts(self, partner, contacts):
        partner.ensure_one()
        if contacts:
            partner.date = fields.Date.context_today(self)
            partner.child_ids |= contacts

    @api.depends('authored_book_ids')
    def _compute_count_books(self):
        for r in self:
            r.count_books = len(r.authored_book_ids)

    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if (record.date_release and
                    record.date_release > fields.Date.today()):
                raise models.ValidationError('Release date must be in the past')

    @api.model
    def find_partners_and_contacts(self, name):
        partner = self.env['res.partner']
        domain = ['|',
                  '&',
                  ('is_company', '=', True),
                  ('name', 'like', name),
                  '&',
                  ('is_company', '=', False),
                  ('parent_id.name', 'like', name)]
        return partner.search(domain)

    @api.model
    def partners_with_email(self, partners):
        def predicate(partner):
            if partner.email:
                return True
            return False
        return partners.filter(predicate)

    @api.model
    def get_email_addresses(self, partner):
        return partner.mapped('child_ids.email')

    @api.model
    def get_companies(self, partners):
        return partners.mapped('parent_id')


class LibraryMember(models.Model):
    _inherit = {'res.partner': 'partner_id'}
    _inherit = 'library.member'
    _name = 'library.member'
    loan_duration = fields.Integer('Loan duration',
                                   default=15,
                                   required=True)
    name = fields.Char('Name', required=True)
    email = fields.Char('Email')
    date = fields.Date('Date')
    is_company = fields.Boolean(
        'Is a company',
        help="Check if the contact is a company, "
             "otherwise it is a person"
    )

    partner_id = fields.Many2one('res.partner',
                                 ondelete='cascade')
    date_start = fields.Date('Member Since')
    date_end = fields.Date('Termination Date')
    member_number = fields.Char()
    date_of_birth = fields.Date('Date of birth')


class LibraryBookLoan(models.Model):
    _inherit = 'library.book.loan'
    expected_return_date = fields.Date('Due for', required=True)


class BaseArchive(models.AbstractModel):
    _name = 'base.archive'
    active = fields.Boolean(default=True)

    def do_archive(self):
        for record in self:
            record.active = not record.active


class LibraryLoanWizard(models.TransientModel):
    _inherit = 'library.load.wizard'

    def _prepare_loan(self, book):
        values = super(LibraryLoanWizard,self)._prepare_loan(book)
        loan_duration = self.member_id.loan_duration
        today_str = fields.Date.context_today(self)
        today = fields.Date.from_string(today_str)
        expected = today + timedelta(days=loan_duration)
        values.update({'expected_return_date':
        fields.Date.to_string(expected)})
        return values

    @api.multi
    def record_loans(self):
        for wizard in self:
            books = wizard.book_ids
            loan = self.env['library.book.loan']
            for book in wizard.book_ids:
                values = wizard._prepare_loan(book)
                loan.create(values)

    @api.multi
    def _prepare_loan(self, book):
        return {'member_id': self.member_id.id,
                'book_id': book.id}
