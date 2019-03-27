from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
import time
from .models import Constants
import json
import channels
import random


class Welcome(Page):
    def is_displayed(self):
        return self.round_number == 1
    timeout_seconds = 5
    pass


class StartWait(WaitPage):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']
    wait_for_all_groups = True


class QuantityChoice(Page):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']
    form_model = 'player'
    form_fields = ['quantity_choice']

    # gathers data to pass to history script
    def vars_for_template(self):
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        value = int(delta * (self.player.seller_type * (fH - fL) + fL))
        if self.round_number > 0:
            data = self.session.vars
            return {
                'roundNumber': self.round_number,
                'data': data,
                'value': value,
                'color': self.player.seller_color,
                'round_number': self.round_number
            }


class AssignWait(WaitPage):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']
    def after_all_players_arrive(self):
        # Gathers relevant info from the group's seller to pass to group
        self.group.get_type()
        self.group.get_color()
        self.group.set_quantity()


class NoAuction(Page):
    def is_displayed(self):
        return self.group.group_quantity == 0 and self.round_number <= self.session.config['final_round']

    def vars_for_template(self):
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        self.group.set_francs()
        self.player.update_payment()

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
            'round_number': self.round_number,
            'data': data,
            'vH': self.group.group_quantity * fH,
            'vL': self.group.group_quantity * fL,
            'role': self.player.role(),
            'quantity': self.player.group.group_quantity,
            'color': self.group.group_color,
            'to_be': to_be,
            'plural': plural,
            'pronoun': pronoun,
            'round_number': self.round_number
        }


class AssignRole(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def vars_for_template(self):
        data = self.session.vars
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        if self.group.group_quantity == 1:
            to_be = 'is'
            plural = ''
            pronoun = 'this'
        else:
            to_be = 'are'
            plural = 's'
            pronoun = 'these'
        return {
            'data': data,
            'vH': self.group.group_quantity * fH,
            'vL': self.group.group_quantity * fL,
            'role': self.player.role(),
            'quantity': self.player.group.group_quantity,
            'color': self.player.seller_color,
            'to_be': to_be,
            'plural': plural,
            'pronoun': pronoun,
            'round_number': self.round_number
        }

    timeout_seconds = 30

    # Enters buyers into auction
    def before_next_page(self):
        if self.player.role() == 'buyer':
            self.player.enter_auction()


class Wait(WaitPage):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def after_all_players_arrive(self):
        self.group.start = True


class Auction(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def vars_for_template(self):
        data = self.session.vars
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        if self.group.group_quantity == 1:
            to_be = 'is'
            plural = ''
            pronoun = 'this'
        else:
            to_be = 'are'
            plural = 's'
            pronoun = 'these'
        return {
            'role': self.player.role(),
            'vH': self.group.group_quantity * fH,
            'vL': self.group.group_quantity * fL,
            'quantity': self.player.group.group_quantity,
            'to_be': to_be,
            'plural': plural,
            'pronoun': pronoun,
            'data': data,
            'round_number': self.round_number
        }

    # def before_next_page(self):
    #     # If there are at least 2 players left in the auction, when one leaves, these commands update the player
    #     # field and group field
    #     if self.group.num_in_auction > 1 and not self.group.auction_over:
    #         self.player.leave_auction()
    #         self.group.remaining_bidders()
    #     # The auction ends when there is only one bidder left
    #     else:
    #         self.group.end_auction()

    # def before_next_page(self):
    #     self.group.activated = False


# Waitpage that bidders see once they leave the auction
class AuctionWait(Page):
    def is_displayed(self):
        return self.group.num_in_auction > 1 and not self.group.auction_over and self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

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
            'role': self.player.role(),
            'to_be': to_be,
            'plural': plural,
            'data': data,
            'round_number': self.round_number
        }


class SetAuction(WaitPage):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def after_all_players_arrive(self):
        self.group.set_winner()


class AuctionFinish(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    timeout_seconds = 30

    def vars_for_template(self):
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        buyer_endowment = self.session.config['buyer_endowment']
        self.group.set_francs()
        self.player.update_payment()
        revenue = self.group.price * self.group.group_quantity
        ticket_value = self.group.group_type * (fH - fL) + fL
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
            'revenue': round(revenue, 2),
            'tickets_kept': Constants.Q - self.group.group_quantity,
            'keep': Constants.Q - self.group.group_quantity,
            'retained_earnings': round(delta * total_value, 2),
            'ticket_value': round(ticket_value, 2),
            'buyer_value': buyer_value,
            'seller_value': round(delta * ticket_value, 2),
            'winner_earnings': round(buyer_endowment - revenue + self.group.group_quantity * ticket_value, 2),
            'seller_earnings': round(revenue + delta * total_value, 2),
            'round_number': self.round_number
        }


class ResultsWaitPage(WaitPage):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']
    wait_for_all_groups = True

    def after_all_players_arrive(self):
        groups = self.subsession.get_groups()
        for g in groups:
            seller_payoff = g.seller_payoff
            if g.group_quantity > 0:
                price = g.price
                winner_payoff = g.winner_payoff
            else:
                price = "N/A"
                winner_payoff = 'N/A'
            self.session.vars[str(self.round_number) + 'R' +
                              str(g.group_number)] = {
                'round': self.round_number,
                'group_number': g.group_number,
                'price': str(price) + ' francs per-ticket',
                'quantity': g.group_quantity,
                'color': g.group_color,
                'winner_payoff': str(winner_payoff) + ' francs',
                'seller_payoff': str(seller_payoff) + ' francs',
            }


class AllGroupsWaitPage(WaitPage):
    def is_displayed(self):
        self.round_number <= self.session.config['final_round']
    wait_for_all_groups = True


class Results(Page):
    timeout_seconds = 40

    def vars_for_template(self):
        data = {}
        for g in range(1, self.subsession.num_groups + 1):
            data['G' + str(g)] = self.session.vars[str(self.round_number) + 'R' + str(g)]
        return {
            'group_number': self.group.group_number,
            'data': data,
            'round_number': self.round_number
        }


class PerformanceReview(Page):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']
    timeout_seconds = 30

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
        if self.round_number == 1 and not self.player.dictionary_deleted:
            dict = self.participant.vars
            del dict['payoff_rounds']
            self.player.dictionary_deleted = True
        else:
            dict = self.participant.vars
        return {
            'data1': dict,
            'data': data
        }


class Payoffs(Page):
    def is_displayed(self):
        return self.round_number == self.session.config['final_round']

    def vars_for_template(self):
        payoff_rounds = [[p.round_number, p.francs, p.payoff] for p in self.player.in_all_rounds()
                         if p.payoff_round]
        total_payoff = self.participant.payoff_plus_participation_fee()

        return {
            'payoff_rounds': payoff_rounds,
            'total_payoff': total_payoff
        }


page_sequence = [
    Welcome,
    StartWait,
    # Page 1
    QuantityChoice,
    AssignWait,
    NoAuction,
    # Page 2
    AssignRole,
    Wait,
    # Page 3
    Auction,
    SetAuction,
    # Page 4
    AuctionFinish,

    ResultsWaitPage,
    # AllGroupsWaitPage,
    # Page 5
    Results,
    # Page 6
    PerformanceReview,
    Payoffs
]
