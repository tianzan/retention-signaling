from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
import channels
import json
from django.db import connection
import numpy
from twisted.internet import task
import time

author = 'Tianzan Pang'

doc = """
Trading game with asymmetric information and retention.
"""


# def group_model_exists():
#     return 'retention-signaling_group' in connection.introspection.table_names()


class Constants(BaseConstants):
    name_in_url = 'Retention_Signaling'
    players_per_group = 3
    num_rounds = 2
    alpha = 0.5
    Q = 5
    num_groups = 1


class Subsession(BaseSubsession):
    test = models.StringField()

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


class Group(BaseGroup):
    group_number = models.IntegerField()

    price = models.IntegerField(initial=0)

    group_quantity = models.IntegerField()

    group_type = models.BooleanField()

    def set_quantity(self):
        seller = self.get_player_by_role('seller')
        self.group_quantity = seller.quantity_choice

    def get_type(self):
        seller = self.get_player_by_role('seller')
        self.group_type = seller.seller_type

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
    bid = models.IntegerField()
    is_seller = models.BooleanField()
    seller_type = models.BooleanField()
    seller_color = models.StringField()
    quantity_choice = models.IntegerField()

    def role(self):
        if self.id_in_group == 1:
            self.is_seller = 1
            return 'seller'
        else:
            self.is_seller = 0
            return 'buyer'

# def runEverySecond():
#     activated_groups = Group.objects.filter(activated=True)
#     for g in activated_groups:
#         if g.price < 100:
#             g.price += 1
#             g.save()
# channels.Group(
#     g.get_channel_group_name()
# ).send(
# )
# else:
#     g.timeout = True
#     g.save()
#     g.advance_participants()

#
# l = task.LoopingCall(runEverySecond)
# l.start(1.0)
# if not l.running:
#     pass
