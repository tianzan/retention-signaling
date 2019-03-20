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


# def group_model_exists():
#     return 'retention-signaling_group' in connection.introspection.table_names()

def group_model_exists():
    return 'Retention_Signaling_group' in connection.introspection.table_names()


class Constants(BaseConstants):
    name_in_url = 'Retention_Signaling'
    players_per_group = 3
    num_rounds = 10
    alpha = 0.5
    Q = 5
    buyer_endowment = 200
    delta = 0.5
    fL = 10
    fH = 30
    num_groups = 1
    num_payoff_rounds = 4
    conversion_rate = 0.06666666666


class Subsession(BaseSubsession):
    def creating_session(self):

        # Creates random groups of buyers and sellers every round
        self.group_randomly()
        # Assigns types
        count = 1
        for group in self.get_groups():
            players = group.get_players()
            for p in players:
                p.seller_type = numpy.random.binomial(1, Constants.alpha)
                if p.seller_type == 1:
                    p.seller_color = 'green'
                else:
                    p.seller_color = 'blue'
            group.group_number = count
            count = count + 1

        if self.round_number == 1:
            rounds = []
            for i in range(1, Constants.num_rounds + 1):
                rounds.append(i)

            for p in self.get_players():
                p.participant.vars['payoff_rounds'] = random.sample(rounds, Constants.num_payoff_rounds)

        for p in self.get_players():
            if self.round_number in p.participant.vars['payoff_rounds']:
                p.payoff_round = True

class Group(BaseGroup):
    start = models.BooleanField(initial=False)

    time_till = models.IntegerField(initial=5)

    time_till_float = models.FloatField(initial=5.05)

    group_number = models.IntegerField()

    activated = models.BooleanField(initial=False)

    price_float = models.FloatField(initial=0)

    price = models.IntegerField(initial=0)

    group_quantity = models.IntegerField()

    group_type = models.BooleanField()

    group_color = models.StringField()

    num_in_auction = models.IntegerField(initial=Constants.players_per_group - 1)

    auction_over = models.BooleanField(initial=False)

    winner_payoff = models.IntegerField()

    seller_payoff = models.IntegerField()

    def get_channel_group_name(self):
        return 'auction_group_{}'.format(self.pk)

    def remaining_bidders(self):
        num = 0
        for p in self.get_players():
            num = num + p.in_auction
        self.num_in_auction = num

    def advance_participants(self):
        channels.Group(self.get_channel_group_name()).send(
            {'text': json.dumps({'accept': True})})

    def set_quantity(self):
        seller = self.get_player_by_role('seller')
        self.group_quantity = seller.quantity_choice

    def get_type(self):
        seller = self.get_player_by_role('seller')
        self.group_type = seller.seller_type

    def get_color(self):
        seller = self.get_player_by_role('seller')
        self.group_color = seller.seller_color

    def end_auction(self):
        self.auction_over = True
        self.activated = False

    def set_winner(self):
        potential_winners = [p for p in self.get_players()
                             if p.role() == 'buyer' and p.in_auction]
        winner = random.choice(potential_winners)
        winner.auction_winner = True

    def set_francs(self):
        for p in self.get_players():
            if p.role() == 'seller':
                p.francs = p.quantity_choice * self.price + (Constants.Q - p.quantity_choice) * (
                        p.seller_type * (Constants.fH - Constants.fL) + Constants.fL)
                self.seller_payoff = p.francs
            else:
                if not p.auction_winner:
                    p.francs = Constants.buyer_endowment
                else:
                    p.francs = Constants.buyer_endowment + self.group_quantity * (
                            self.group_type * (Constants.fH - Constants.fL) + Constants.fL - self.price)
                    self.winner_payoff = p.francs


class Player(BasePlayer):
    bid = models.IntegerField()
    is_seller = models.BooleanField()
    seller_type = models.BooleanField()
    seller_color = models.StringField()
    quantity_choice = models.IntegerField(initial=-1)
    in_auction = models.BooleanField(initial=False)
    leave_price = models.IntegerField()
    auction_winner = models.BooleanField(initial=False)
    francs = models.IntegerField()
    payoff_round = models.BooleanField(initial=False)
    payoff_updated = models.BooleanField(initial=False)

    def role(self):
        if self.id_in_group == 1:
            self.is_seller = 1
            return 'seller'
        else:
            self.is_seller = 0
            return 'buyer'

    def enter_auction(self):
        self.in_auction = True

    def leave_auction(self):
        self.in_auction = False
        # Captures price at which bidder leaves auction
        self.leave_price = self.group.price
        # A bidder does not win the auction if he/she leaves
        self.auction_winner = False

    def update_payment(self):
        if self.payoff_round and not self.payoff_updated:
            self.payoff += self.francs*Constants.conversion_rate
            self.payoff_updated = True

def runEverySecond():
    if group_model_exists():
        deactive_groups = Group.objects.filter(activated=False, start=True)
        for g in deactive_groups:
            if g.time_till > 0:
                g.time_till_float = g.time_till_float - 0.05
                g.time_till = int(g.time_till_float)
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'time_till': g.time_till})}
                )
            if g.time_till == 0:
                g.activated = True
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'time_till': g.time_till,
                         'activated': g.activated})}
                )
        activated_groups = Group.objects.filter(activated=True, auction_over=False)

        for g in activated_groups:
            if g.price < Constants.fH:
                g.price_float += 0.05
                g.price = int(g.price_float)
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'price': g.price,
                         'num': g.num_in_auction,
                         'over': g.auction_over,
                         'activated': g.activated})}
                )
            if g.price == Constants.fH:
                g.auction_over = True
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'price': g.price,
                         'num': g.num_in_auction,
                         'over': g.auction_over})}
                )


l = task.LoopingCall(runEverySecond)
l.start(0.1)
if not l.running:
    pass
