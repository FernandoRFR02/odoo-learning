from odoo import models, api, fields


class BookCategory(models.Model):

    _name = 'library.book.category'

    name = fields.Char('Category')
    parent_id = fields.Many2one('library.book.category',
                                string='Parent Category',
                                ondelete='restrict',
                                index=True)
    child_ids = fields.One2many('library.book.category', 'parent_id',
                                string='Child Categories')
    _parent_store = True
    parent_left = fields.Integer(index=True)
    parent_right = fields.Integer(index=True)


@api.constrains('parent_id')
def _check_hierarchy(self):
    if not self._check_recursion():
        raise models.ValidationError('Error! You cannot create recursive categories.')

    class LibraryBook(models.Model):
        _name = 'library.book'

    name = fields.Char('Title', required=True)
    date_release = fields.Date('Release Date')

    _sql_constraints = [
        ('name_uniq',
         'UNIQUE (name)',
         'Book title must be unique.')
    ]

    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if (record.date_release and
                    record.date_release > fields.Date.today()):
                raise models.ValidationError('Release date must be in the past')