from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
import time
from .models import Constants
import json
import channels
import random


class QuantityChoice(Page):
    form_model = 'player'
    form_fields = ['quantity_choice']

    # gathers data to pass to history script
    def vars_for_template(self):
        value = int(Constants.delta * (self.player.seller_type * (Constants.fH - Constants.fL) + Constants.fL))
        if self.round_number > 0:
            data = self.session.vars
            return {
                'roundNumber': self.round_number,
                'data': data,
                'value': value,
                'color': self.player.seller_color
            }

    # timeout_seconds = 30

    def before_next_page(self):
        if self.timeout_happened:
            self.player.quantity_choice = random.choice([0, 1, 2, 3, 4, 5])


class AssignWait(WaitPage):
    def after_all_players_arrive(self):
        # Gathers relevant info from the group's seller to pass to group
        self.group.get_type()
        self.group.get_color()
        self.group.set_quantity()


class AssignRole(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0

    def vars_for_template(self):
        data = self.session.vars
        if self.group.group_quantity == 1:
            to_be = 'is'
            plural = ''
            pronoun = 'this'
        else:
            to_be = 'are'
            plural = 's'
            pronoun = 'these'
        return {
            'roundNumber': self.round_number,
            'data': data,
            'vH': self.group.group_quantity*Constants.fH,
            'vL': self.group.group_quantity*Constants.fL,
            'role': self.player.role(),
            'quantity': self.player.group.group_quantity,
            'color': self.player.seller_color,
            'to_be': to_be,
            'plural': plural,
            'pronoun': pronoun
        }

    # Enters buyers into auction
    def before_next_page(self):
        if self.player.role() == 'buyer':
            self.player.enter_auction()


class Wait(WaitPage):
    def is_displayed(self):
        return self.group.group_quantity > 0

    def after_all_players_arrive(self):
        # Activates group to start the auction
        self.group.activated = True


class Bid(Page):
    def is_displayed(self):
        return self.player.role() == 'buyer' and self.group.group_quantity > 0

    def vars_for_template(self):
        data = self.session.vars
        if self.group.group_quantity == 1:
            to_be = 'is'
            plural = ''
        else:
            to_be = 'are'
            plural = 's'
        return {
            'quantity': self.player.group.group_quantity,
            'to_be': to_be,
            'plural': plural,
            'data': data
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
        return self.group.num_in_auction > 1 and not self.group.auction_over and self.group.group_quantity > 0

    def vars_for_template(self):
        return {
            'quantity': self.player.group.group_quantity,
            'role': self.player.role()
        }


class SetAuction(WaitPage):
    def is_displayed(self):
        return self.group.group_quantity > 0

    def after_all_players_arrive(self):
        self.group.set_winner()


class AuctionFinish(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0

    def vars_for_template(self):
        is_winner = self.player.auction_winner
        return {
            'is_winner': is_winner
        }


class ResultsWaitPage(WaitPage):
    def after_all_players_arrive(self):
        # self.group.set_price()
        if self.group.group_quantity > 0:
            price = self.group.price
        else:
            price = "N/A"
        self.session.vars[str(self.round_number) + 'R' +
                          str(self.group.group_number)] = {
            'round': self.round_number,
            'price': price,
            'quantity': self.group.group_quantity,
            'color': self.group.group_color}


class AllGroupsWaitPage(WaitPage):
    wait_for_all_groups = True


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
    ResultsWaitPage,
    AllGroupsWaitPage,
    Results
]
