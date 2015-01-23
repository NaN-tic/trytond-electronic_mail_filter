# This file is part of electronic_mail_filter module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .electronic_mail import *


def register():
    Pool.register(
        ElectronicMailFilter,
        SearchingStart,
        module='electronic_mail_filter', type_='model')
