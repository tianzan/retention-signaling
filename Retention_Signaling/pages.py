from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
import time
from .models import Constants
import json
import channels


class QuantityChoice(Page):
    form_model = 'player'
    form_fields = ['quantity_choice']

    def vars_for_template(self):
        r = []
        for i in range(self.round_number - 1):
            r.append(i + 1)

        if self.round_number > 1:
            data = self.session.vars
            return {
                'roundNumber': self.round_number,
                'range': r,
                'data': data
            }
        else:
            return {
                'roundNumber': self.round_number,
                'data': 0
            }


class Bid(Page):
    def is_displayed(self):
        return self.player.role() == 'buyer'

    def vars_for_template(self):
        return {
            'quantity': self.player.group.group_quantity
        }

    def before_next_page(self):
        self.group.activated = False


class Wait(WaitPage):
    def after_all_players_arrive(self):
        self.group.set_quantity()
        self.group.get_type()
        self.group.get_color()
        self.group.activated = True


class ResultsWaitPage(WaitPage):
    def after_all_players_arrive(self):
        # self.group.set_price()
        self.session.vars[str(self.round_number) + 'R' +
                          str(self.group.group_number)] = {'price': self.group.price,
                                                           'quantity': self.group.group_quantity,
                                                           'color': self.group.group_color}


class Results(Page):
    pass


page_sequence = [
    QuantityChoice,
    Wait,
    Bid,
    ResultsWaitPage
]
