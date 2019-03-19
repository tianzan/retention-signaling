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

    timeout_seconds = 5

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
            'vH': self.group.group_quantity * Constants.fH,
            'vL': self.group.group_quantity * Constants.fL,
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
        self.group.set_francs()
        revenue = self.group.price * self.group.group_quantity
        ticket_value = self.group.group_type * (Constants.fH - Constants.fL) + Constants.fL
        total_value = (Constants.Q - self.group.group_quantity) * ticket_value
        buyer_value = self.group.group_quantity * ticket_value
        if self.group.group_quantity == 1:
            to_be = 'was'
            plural = ''
        else:
            to_be = 'were'
            plural = 's'
        if self.group.group_quantity == 4:
            kplural = ''
        else:
            kplural = 's'

        is_winner = self.player.auction_winner
        return {
            'to_be': to_be,
            'plural': plural,
            'kplural': kplural,
            'price': self.group.price,
            'quantity': self.group.group_quantity,
            'color': self.group.group_color,
            'role': self.player.role(),
            'is_winner': is_winner,
            'francs': self.player.francs,
            'revenue': revenue,
            'tickets_kept': Constants.Q - self.group.group_quantity,
            'keep': Constants.Q - self.group.group_quantity,
            'retained_earnings': int(Constants.delta * total_value),
            'ticket_value': ticket_value,
            'buyer_value': buyer_value,
            'seller_value': int(Constants.delta * ticket_value),
            'winner_earnings': Constants.buyer_endowment - revenue + self.group.group_quantity * ticket_value,
            'seller_earnings': revenue + int(Constants.delta * total_value)
        }


class ResultsWaitPage(WaitPage):
    def after_all_players_arrive(self):
        # self.group.set_price()
        seller_payoff = self.group.seller_payoff
        if self.group.group_quantity > 0:
            price = self.group.price
            winner_payoff = self.group.winner_payoff
        else:
            price = "N/A"
            winner_payoff = 'N/A'
        self.session.vars[str(self.round_number) + 'R' +
                          str(self.group.group_number)] = {
            'round': self.round_number,
            'group_number': self.group.group_number,
            'price': str(price) + ' francs per-ticket',
            'quantity': self.group.group_quantity,
            'color': self.group.group_color,
            'winner_payoff': str(winner_payoff) + ' francs',
            'seller_payoff': str(seller_payoff) + ' francs',
        }

class AllGroupsWaitPage(WaitPage):
    wait_for_all_groups = True


class Results(Page):
    def vars_for_template(self):
        data = {}
        for g in range(1, Constants.num_groups + 1):
            data['G' + str(g)] = (self.session.vars[str(self.round_number) + 'R' + str(g)])
        return {
            'data': data
        }


class PerformanceReview(Page):
    def vars_for_template(self):
        self.participant.vars[str(self.round_number) + 'R' + str(self.group.group_number)] = {
            'round': self.round_number,
            'role': self.player.role(),
            'color': self.player.seller_color,
            'quantity_choice': self.player.quantity_choice,
            'auction_winner': self.player.auction_winner,
            'price': self.group.price,
            'group_quantity': self.group.group_quantity,
            'group_color': self.group.group_color,
            'francs': self.player.francs
        }
        data = self.session.vars
        data1 = self.participant.vars
        return{
            'data1': data1,
            'data': data
        }




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
    Results,
    PerformanceReview
]
