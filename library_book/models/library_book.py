from odoo import api, models, fields


class LibraryBook(models.Model):
    _name = "library.book"

    name = fields.Char("Title", required=True)
    date_release = fields.Date("Release Date")
    author_ids = fields.Many2many("res.partner", string="Authors")
    show_name = fields.Boolean("Show the name of this book?")
    limit_users = fields.Boolean("Limit the users display")

    @api.onchange("limit_users")
    def onchange_limit_users(self):
        return {"domain": {"author_ids": self.limit_users and [("name", "=", "Carlos")] or False}}

