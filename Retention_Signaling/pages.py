from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
import time
from .models import Constants
import json
import channels
import random
from .models import loop, runEverySecond


class Welcome(Page):
    def is_displayed(self):
        return self.round_number == 1

class QuantityChoice(Page):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']

    form_model = 'player'
    form_fields = ['quantity_choice_blue', 'quantity_choice_green']

    # gathers data to pass to history script
    def vars_for_template(self):
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        green_value = int(delta * fH)
        blue_value = int(delta * fL)
        if self.round_number > 0:
            data = self.session.vars['past_rounds']
            return {
                'push': self.session.config['push'],
                'roundNumber': self.round_number,
                'data': data,
                'green_value': green_value,
                'blue_value': blue_value,
                'color': self.player.seller_color,
                'round_number': self.round_number,
                'group_number': self.group.group_number,
                'num_groups': self.subsession.num_groups,
                'group_numbers': self.participant.vars['group_numbers']
            }


class AssignWait(WaitPage):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']

    def after_all_players_arrive(self):
        # Gathers relevant info from the group's seller to pass to group
        self.group.get_type()
        self.group.get_color()
        self.group.set_quantity()
        if self.group.group_quantity == 0:
            self.group.set_francs()
            seller_payoff = self.group.seller_payoff
            temp = dict()
            temp[str(self.round_number) + 'R' + str(self.group.group_number)] = {
                'round': self.round_number,
                'group_number': self.group.group_number,
                'price': 'N/A',
                'quantity': self.group.group_quantity,
                'color': self.group.group_color,
                'winner_payoff': 'N/A',
                'seller_payoff': seller_payoff,
            }
            self.session.vars['current_round'].update(temp)


class NoAuction(Page):
    def is_displayed(self):
        return self.group.group_quantity == 0 and self.round_number <= self.session.config['final_round']

    def vars_for_template(self):
        return {
            'round_number': self.round_number,
            'role': self.player.role(),
            'color': self.group.group_color,
        }


class AssignRole(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def vars_for_template(self):
        data = self.session.vars['past_rounds']
        fH = self.group.fH
        fL = self.group.fL
        if self.group.group_quantity == 1:
            to_be = 'is'
            plural = ''
            pronoun = 'this'
        else:
            to_be = 'are'
            plural = 's'
            pronoun = 'these'
        return {
            'push': self.session.config['push'],
            'data': data,
            'vH': self.group.group_quantity * fH,
            'vL': self.group.group_quantity * fL,
            'role': self.player.role(),
            'quantity': self.group.group_quantity,
            'color': self.player.seller_color,
            'to_be': to_be,
            'plural': plural,
            'pronoun': pronoun,
            'round_number': self.round_number,
            'group_number': self.group.group_number,
            'num_groups': self.subsession.num_groups,
            'group_numbers': self.participant.vars['group_numbers']
        }

    # Enters buyers into auction
    def before_next_page(self):
        if self.player.role() == 'buyer':
            self.player.enter_auction()


class Wait(WaitPage):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def after_all_players_arrive(self):
        self.group.hidden_start = True


class Auction(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def vars_for_template(self):
        data = self.session.vars['past_rounds']
        fH = self.group.fH
        fL = self.group.fL
        if self.group.group_quantity == 1:
            to_be = 'is'
            plural = ''
            pronoun = 'this'
        else:
            to_be = 'are'
            plural = 's'
            pronoun = 'these'
        return {
            'push': self.session.config['push'],
            'role': self.player.role(),
            'vH': self.group.group_quantity * fH,
            'vL': self.group.group_quantity * fL,
            'quantity': self.player.group.group_quantity,
            'to_be': to_be,
            'plural': plural,
            'pronoun': pronoun,
            'initial_expense': self.group.start_price * self.group.group_quantity,
            'data': data,
            'round_number': self.round_number,
            'group_number': self.group.group_number,
            'group_numbers': self.participant.vars['group_numbers'],
            'num_groups': self.subsession.num_groups
        }


class SetAuction(WaitPage):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']

    def after_all_players_arrive(self):
        self.group.set_winner()
        self.group.set_francs()
        seller_payoff = self.group.seller_payoff
        price = self.group.price
        winner_payoff = self.group.winner_payoff
        temp = dict()
        temp[str(self.round_number) + 'R' +
             str(self.group.group_number)] = {
            'round': self.round_number,
            'group_number': self.group.group_number,
            'price': price,
            'quantity': self.group.group_quantity,
            'color': self.group.group_color,
            'winner_payoff': winner_payoff,
            'seller_payoff': seller_payoff,
        }
        self.session.vars['current_round'].update(temp)


class AuctionFinish(Page):
    def is_displayed(self):
        return self.group.group_quantity > 0 and self.round_number <= self.session.config['final_round']


    def vars_for_template(self):
        fH = self.group.fH
        fL = self.group.fL
        delta = self.session.config['delta']
        buyer_endowment = self.session.config['buyer_endowment']
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
            'push': self.session.config['push'],
            'to_be': to_be,
            'plural': plural,
            'kplural': kplural,
            'price': self.group.price,
            'fH': fH,
            'buyer_endowment': buyer_endowment,
            'quantity': self.group.group_quantity,
            'color': self.group.group_color,
            'role': self.player.role(),
            'is_winner': is_winner,
            'francs': self.player.francs,
            'revenue': revenue,
            'tickets_kept': Constants.Q - self.group.group_quantity,
            'keep': Constants.Q - self.group.group_quantity,
            'retained_earnings': int(delta * total_value),
            'ticket_value': ticket_value,
            'buyer_value': buyer_value,
            'seller_value': int(delta * ticket_value),
            'winner_earnings': buyer_endowment - revenue + self.group.group_quantity * ticket_value,
            'seller_earnings': revenue + int(delta * total_value),
            'round_number': self.round_number,
        }


class ResultsWaitPage(WaitPage):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']

    wait_for_all_groups = True

    def after_all_players_arrive(self):
        self.session.vars['past_rounds'].update(self.session.vars['current_round'])
        self.session.vars['current_round'] = {}


class PerformanceReview(Page):
    def is_displayed(self):
        return self.round_number <= self.session.config['final_round']


    def vars_for_template(self):
        data = self.session.vars['past_rounds']
        return {
            'push': self.session.config['push'],
            'roles': self.participant.vars['roles'],
            'payoffs': self.participant.vars['francs'],
            'data': data,
            'group_number': self.group.group_number,
            'num_groups': self.subsession.num_groups,
            'group_numbers': self.participant.vars['group_numbers']
        }

    def before_next_page(self):
        self.player.update_payment()


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
    QuantityChoice,
    AssignWait,
    NoAuction,
    AssignRole,
    Wait,
    Auction,
    SetAuction,
    AuctionFinish,
    ResultsWaitPage,
    PerformanceReview,
    Payoffs
]
