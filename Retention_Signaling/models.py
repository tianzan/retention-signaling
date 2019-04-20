from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
import channels
import json
from django.db import connection
import numpy
from twisted.internet import task
import random

author = 'Tianzan Pang'

doc = """
Trading game with asymmetric information and retention.
"""


def group_model_exists():
    return 'Retention_Signaling_group' in connection.introspection.table_names()


class Constants(BaseConstants):
    name_in_url = 'Retention_Signaling'
    # Session configuration (mostly for demo purposes)
    players_per_group = None
    # Number of rounds and rounds which pay (experimental design)
    num_rounds = 20
    # Treatment parameters
    alpha = 0.5
    Q = 5

    hidden_time_till = 2
    time_till = 4
    increment_speed = 1


class Subsession(BaseSubsession):
    num_groups = models.IntegerField()
    players_per_group = models.IntegerField()

    def creating_session(self):
        self.session.vars['past_rounds'] = {}
        self.session.vars['current_round'] = {}
        self.num_groups = self.session.config['num_groups']
        self.players_per_group = self.session.config['players_per_group']
        num_participants = self.num_groups * self.players_per_group
        alpha = self.session.config['alpha']
        num_payoff_rounds = self.session.config['num_payoff_rounds']
        # Creates random groups of buyers and sellers every round
        participants = range(1, num_participants + 1)
        random_matrix = numpy.random.choice(participants, size=(self.num_groups, self.players_per_group), replace=False)
        random_matrix_list = random_matrix.tolist()
        self.set_group_matrix(random_matrix_list)

        if self.round_number == 1:
            rounds = []
            for i in range(1, self.session.config['final_round'] + 1):
                rounds.append(i)

            for p in self.get_players():
                p.participant.vars['payoff_rounds'] = random.sample(rounds, num_payoff_rounds)
                p.participant.vars['roles'] = {}
                p.participant.vars['francs'] = {}
                p.participant.vars['group_numbers'] = []

        # Assigns numbers to groups and seller types to players; draws payoff rounds for participants as well
        # Creates and fills in the dictionaries used to track group/role for participants
        count = 1
        for group in self.get_groups():
            group.num_buyers = self.session.config['players_per_group']-1
            group.fL = self.session.config['fL']
            group.fH = self.session.config['fH']
            group.buyer_endowment = self.session.config['buyer_endowment']
            players = group.get_players()
            group.num_in_auction = self.players_per_group - 1
            group.group_number = count
            for p in players:
                p.participant.vars['roles'][str(p.round_number) + 'R' + str(group.group_number)] = p.role()
                p.participant.vars['group_numbers'].append(group.group_number)
                p.seller_type = numpy.random.binomial(1, alpha)
                if p.seller_type == 1:
                    p.seller_color = 'green'
                else:
                    p.seller_color = 'blue'

                if self.round_number in p.participant.vars['payoff_rounds']:
                    p.payoff_round = True
            count = count + 1


class Group(BaseGroup):
    started_auction = models.IntegerField(initial=0)
    num_buyers = models.IntegerField()

    # The following four fields store parameters set in session_configs
    # They are set in the creating_session method
    fL = models.IntegerField()
    fH = models.IntegerField()
    buyer_endowment = models.IntegerField()

    num_in_auction = models.IntegerField()

    # These fields store the key pieces of data in which I am interested
    price = models.IntegerField(initial=0)
    group_quantity = models.IntegerField()
    group_type = models.BooleanField()
    group_color = models.StringField()

    # Used to present feedback to subjects
    group_number = models.IntegerField()
    winner_payoff = models.IntegerField()
    seller_payoff = models.IntegerField()


    def get_channel_group_name(self):
        return 'auction_group_{}'.format(self.pk)


    def set_quantity(self):
        seller = self.get_player_by_role('seller')
        seller_type = seller.seller_type
        quantity = seller_type * seller.quantity_choice_green + (1 - seller_type) * seller.quantity_choice_blue
        self.group_quantity = quantity
        seller.quantity_choice = quantity

    def get_type(self):
        seller = self.get_player_by_role('seller')
        self.group_type = seller.seller_type

    def get_color(self):
        seller = self.get_player_by_role('seller')
        self.group_color = seller.seller_color

    def set_winner(self):

        potential_winners = [p for p in self.get_players()
                             if p.role() == 'buyer' and p.in_auction]
        if len(potential_winners) > 0:
            winner = random.choice(potential_winners)
            winner.auction_winner = True

        else:
            potential_winners = [p for p in self.get_players() if p.leave_price >= self.price]
            winner = random.choice(potential_winners)
            winner.auction_winner = True
        winner.save()

    def set_francs(self):
        delta = self.session.config['delta']
        buyer_endowment = self.session.config['buyer_endowment']
        for p in self.get_players():
            if p.role() == 'seller':
                p.francs = int(p.quantity_choice * self.price + delta * (Constants.Q - p.quantity_choice) * (
                        p.seller_type * (self.fH - self.fL) + self.fL))
                self.seller_payoff = p.francs
            else:
                if not p.auction_winner:
                    p.francs = buyer_endowment
                else:
                    p.francs = buyer_endowment + self.group_quantity * (
                            self.group_type * (self.fH - self.fL) + self.fL - self.price)
                    self.winner_payoff = p.francs
            p.participant.vars['francs'][str(self.round_number) + 'R' + str(self.group_number)] = p.francs


class Player(BasePlayer):
    is_seller = models.BooleanField()
    seller_type = models.BooleanField()
    seller_color = models.StringField()
    quantity_choice = models.IntegerField(initial=-1)
    quantity_choice_blue = models.IntegerField(initial=-1)
    quantity_choice_green = models.IntegerField(initial=-1)
    in_auction = models.BooleanField(initial=False)
    leave_price = models.IntegerField(initial=-5)
    auction_winner = models.BooleanField(initial=False)
    francs = models.IntegerField()
    payoff_round = models.BooleanField(initial=False)

    def get_channel_player_name(self):
        return 'player_{}'.format(self.pk)

    def role(self):
        if self.id_in_group == 1:
            self.is_seller = 1
            return 'seller'
        else:
            self.is_seller = 0
            return 'buyer'

    def update_payment(self):
        if self.payoff_round:
            self.payoff += round(self.francs * self.session.config['conversion_rate'], 2)

