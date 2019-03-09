from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)

import numpy

author = 'Tianzan Pang'

doc = """
Trading game with asymmetric information and retention.
"""


class Constants(BaseConstants):
    name_in_url = 'Retention_Signaling'
    players_per_group = 3
    num_rounds = 1
    alpha = 0.9
    Q = 5


class Subsession(BaseSubsession):
    def creating_session(self):
        # Creates random groups of buyers and sellers every round
        self.group_randomly()
        # Assigns types
        for group in self.get_groups():
            players = group.get_players()
            for p in players:
                p.seller_type = numpy.random.binomial(1, Constants.alpha)


class Group(BaseGroup):
    price = models.FloatField()

    def set_quantity(self):
        seller = self.get_player_by_role('seller')
        return seller.quantity_choice

    def set_price(self):
        buyers = [
            p for p in self.get_players()
            if p.role() == 'buyer'
        ]

        bids = [
            p.bid for p in buyers
        ]
        self.price = max(bids)


class Player(BasePlayer):
    bid = models.FloatField()
    is_seller = models.BooleanField()
    seller_type = models.BooleanField()
    quantity_choice = models.IntegerField()

    def role(self):
        if self.id_in_group == 1:
            self.is_seller = 1
            return 'seller'
        else:
            self.is_seller = 0
            return 'buyer'
