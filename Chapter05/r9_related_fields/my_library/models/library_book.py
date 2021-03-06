# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons import decimal_precision as dp


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'date_release desc, name'
    _rec_name = 'short_name'

    name = fields.Char('Title', required=True)
    short_name = fields.Char('Short Title', translate=True, index=True)
    notes = fields.Text('Internal Notes')
    state = fields.Selection(
        [('draft', 'Not Available'),
         ('available', 'Available'),
         ('lost', 'Lost')],
        'State', default="draft")
    description = fields.Html('Description', sanitize=True, strip_style=False)
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of Print?')
    date_release = fields.Date('Release Date')
    date_updated = fields.Datetime('Last Updated')
    pages = fields.Integer('Number of Pages',
            groups="base.group_user",
            state={'lost': [('readonly', True)]},
            help="Total book page count", company_dependent=False)
    reader_rating = fields.Float(
        'Reader Average Rating',
        digits=(14, 4), # 可选精度（总数，小数）
    )
    author_ids = fields.Many2many(
        'res.partner',
        string='Authors'
    )
    cost_price = fields.Float('Book Cost', digits=dp.get_precision('Book Price'))
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary('Retail Price') # 可选属性：currency_field='currency_id'，以防币种字段有currency_id 以外的名称

    publisher_id = fields.Many2one(
        'res.partner', string='Publisher',
        # 下为可选项
        ondelete='set null',
        context = {},
        domain = [],
    )
    publisher_city = fields.Char('Publisher City', related='publisher_id.city', readonly=True)
    category_id = fields.Many2one('library.book.category')
    age_days = fields.Float(
        string='Days Since Release',
        compute='_compute_age', inverse='_inverse_age', search='_search_age',
        store=False,
        compute_sudo=False,
    )

    @api.depends('date_release')
    def _compute_age(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            delta = today - book.date_release
            book.age_days = delta.days


    # 这一_compute_age的反向方法用于让 age_days 字段可编辑
    # 这是可选项，如果不想让该计算字段可编辑可以进行删除
    def _inverse_age(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            d = today - timedelta(days=book.age_days)
            book.date_release = d

    # 用于启动对计算字段的搜索
    # 这是可选项，如果不想启用该搜索可以进行删除
    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        # 转换运算符
        # age > value 对应 date < value_date
        operator_map = {
            '>': '<', '>=': '<=',
            '<': '>', '<=': '>=',
        }
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date)]

    def name_get(self):
        """ 这个方法用于自定义记录的显示名称 """
        result = []
        for record in self:
            rec_name = "%s (%s)" % (record.name, record.date_release)
            result.append((record.id, rec_name))
        return result

    _sql_constraints = [('name_uniq', 'UNIQUE(name)', 'Book title must be unique.')]

    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if record.date_release and record.date_release > fields.Date.today():
                raise models.ValidationError('Release date must be in the past')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    published_book_ids = fields.One2many(
        'library.book',
        'publisher_id',
        string='Published Books'
    )
    authored_book_ids = fields.Many2many(
        'library.book',
        string = 'Authored Books',
        # relation='library_book_res_partner_rel' # 可选项
    )