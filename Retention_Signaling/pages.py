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

    # gathers data to pass to history script
    def vars_for_template(self):
        r = []
        a = [1, 2, 3, 4, 5]
        for i in range(self.round_number - 1):
            r.append(i + 1)

        if self.round_number > 0:
            data = self.session.vars
            return {
                'roundNumber': self.round_number,
                'range': r,
                'data': data,
                'color': self.player.seller_color
            }
        # else:
        #     return {
        #         'roundNumber': self.round_number,
        #         'data': 0,
        #         'color': self.player.seller_color
        #     }


class AssignWait(WaitPage):
    def after_all_players_arrive(self):
        # Gathers relevant info from the group's seller to pass to group
        self.group.get_type()
        self.group.get_color()
        self.group.set_quantity()


class AssignRole(Page):
    def vars_for_template(self):
        return {
            'role': self.player.role(),
            'quantity': self.player.group.group_quantity,
            'color': self.player.seller_color
        }

    # Enters buyers into auction
    def before_next_page(self):
        if self.player.role() == 'buyer':
            self.player.enter_auction()


class Wait(WaitPage):
    def after_all_players_arrive(self):
        # Activates group to start the auction
        self.group.activated = True


class Bid(Page):
    def is_displayed(self):
        return self.player.role() == 'buyer'

    def vars_for_template(self):
        return {
            'quantity': self.player.group.group_quantity
        }

    def before_next_page(self):
        # If there are at least 2 players left in the auction, when one leaves, these commands update the player
        # field and group field
        if self.group.num_in_auction > 1 and not self.group.auction_over:
            self.player.leave_auction()
            self.group.remaining_bidders()
        # The auction ends when there is only one bidder left
        else:
            self.group.end_auction()

    # def before_next_page(self):
    #     self.group.activated = False


# Waitpage that bidders see once they leave the auction
class AuctionWait(Page):
    def is_displayed(self):
        return self.group.num_in_auction > 1 and not self.group.auction_over

    def vars_for_template(self):
        return {
            'quantity': self.player.group.group_quantity,
            'role': self.player.role()
        }


class SetAuction(WaitPage):
    def after_all_players_arrive(self):
        self.group.set_winner()


class AuctionFinish(Page):
    def vars_for_template(self):
        is_winner = self.player.auction_winner
        return {
            'is_winner': is_winner
        }


class ResultsWaitPage(WaitPage):
    def after_all_players_arrive(self):
        # self.group.set_price()
        self.session.vars[str(self.round_number) + 'R' +
                          str(self.group.group_number)] = {
            'round': self.round_number,
            'price': self.group.price,
            'quantity': self.group.group_quantity,
            'color': self.group.group_color}


class Results(Page):
    pass


page_sequence = [
    QuantityChoice,
    AssignWait,
    AssignRole,
    Wait,
    Bid,
    AuctionWait,
    SetAuction,
    AuctionFinish,
    ResultsWaitPage
]
