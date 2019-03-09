from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants


class QuantityChoice(Page):
    form_model = 'player'
    form_fields = ['quantity_choice']


class Wait(WaitPage):
    def after_all_players_arrive(self):
        self.group.set_quantity()


class Bid(Page):

    def vars_for_template(self):
        return {
            'quantity': self.player.group.set_quantity()
        }

    form_model = 'player'
    form_fields = ['bid']


class ResultsWaitPage(WaitPage):

    def after_all_players_arrive(self):
        self.group.set_price()


class Results(Page):
    pass


page_sequence = [
    QuantityChoice,
    Wait,
    Bid,
    ResultsWaitPage,
    Results
]
