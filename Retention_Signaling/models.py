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
    dictionary_created = models.BooleanField()
    dictionary_updated = models.BooleanField()

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
            group.time_till = self.session.config['time_till']
            group.hidden_time_till = self.session.config['hidden_time_till']
            group.increment_size = self.session.config['increment_size']
            group.start_price = self.session.config['start_price']
            group.fL = self.session.config['fL']
            group.fH = self.session.config['fH']
            group.buyer_endowment = self.session.config['buyer_endowment']
            players = group.get_players()
            group.num_in_auction = self.players_per_group - 1
            group.group_number = count
            for p in players:
                p.participant.vars['roles'][str(p.round_number)+'R'+str(group.group_number)] = p.role()
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
    # The following four fields store parameters set in session_configs
    # They are set in the creating_session method
    increment_size = models.IntegerField()
    start_price = models.IntegerField()
    fL = models.IntegerField()
    fH = models.IntegerField()
    buyer_endowment = models.IntegerField()

    # These fields support features of the auction page
    # For before an auction starts
    start = models.BooleanField(initial=False)  # Countdown to auction start begins when start is true
    hidden_start = models.BooleanField(initial=False)  # To start invisible counter
    hidden_time_till = models.IntegerField()  # Invisible counter
    time_till = models.IntegerField()  # Used for button display
    # time_till_float = models.FloatField(initial=Constants.time_till + 0.05)  # Actual counter (is a float)

    activated = models.BooleanField(initial=False)  # Auction is live once activated is true
    move_count = models.IntegerField(initial=0)
    # button_activated_already = models.BooleanField(initial=False)

    price_float = models.IntegerField(initial=0)
    num_in_auction = models.IntegerField()
    auction_over = models.BooleanField(initial=False)

    # These fields store the key pieces of data in which I am interested
    price = models.IntegerField(initial=0)
    group_quantity = models.IntegerField()
    group_type = models.BooleanField()
    group_color = models.StringField()

    # Used to present feedback to subjects
    group_number = models.IntegerField()
    winner_payoff = models.IntegerField()
    seller_payoff = models.IntegerField()

    # Used to track whether data has been loaded into session vars
    data_updated = models.BooleanField()

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
        seller_type = seller.seller_type
        quantity = seller_type*seller.quantity_choice_green+(1-seller_type)*seller.quantity_choice_blue
        self.group_quantity = quantity
        seller.quantity_choice = quantity

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
            p.participant.vars['francs'][str(self.round_number)+'R'+str(self.group_number)] = p.francs


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
    payoff_updated = models.BooleanField(initial=False)
    dictionary_deleted = models.BooleanField(initial=False)

    def get_channel_player_name(self):
        return 'player_{}'.format(self.pk)

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
            self.payoff += round(self.francs * self.session.config['conversion_rate'], 2)
            self.payoff_updated = True



def runEverySecond():
    if group_model_exists():
        # Groups are hidden started once all group members reach Wait
        invisible_wait_groups = Group.objects.filter(hidden_start=True)
        for g in invisible_wait_groups:
            if g.hidden_time_till > 0:
                g.hidden_time_till = g.hidden_time_till - 1
                g.save()
            else:
                g.start = True
                g.hidden_start = False
                g.save()

        active_wait_groups = Group.objects.filter(activated=False, start=True)
        for g in active_wait_groups:
            if g.time_till > 0:
                g.time_till = g.time_till - 1
                # Save commands are necessary for the database to change
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'started': True,
                         'activated': False,
                         'time_till': g.time_till,
                         'over': False,
                         'activate_exit': False,
                         })}
                )
            if g.time_till == 0:
                # Group is activated once timer hits 0
                g.activated = True
                g.start = False
                g.price = g.start_price
                g.price_float = g.start_price
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'started': True,
                         'activated': True,
                         'time_till': g.time_till,
                         'activate_exit': True,
                         'over': False,
                         })}
                )
        # The auction is live in activated groups
        activated_groups = Group.objects.filter(activated=True, auction_over=False)

        for g in activated_groups:
            g.remaining_bidders()
            g.save()
            if g.price < g.fH and g.num_in_auction > 1:
                g.price  += g.increment_size
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'price': g.price,
                         'expense': g.price * g.group_quantity,
                         'num': g.num_in_auction,
                         'over': False,
                         'activated': True,
                         'activate_exit': False,
                         'started': True
                         })}
                )
            if int(g.price) == g.fH or g.num_in_auction <= 1:
                g.auction_over = True
                g.save()
                channels.Group(
                    g.get_channel_group_name()
                ).send(
                    {'text': json.dumps(
                        {'price': g.price,
                         'expense': g.price * g.group_quantity,
                         # Sometimes the incorrect number of remaining bidders is displayed for some reason
                         'num': g.num_in_auction,
                         'over': True,
                         'started': True,
                         'activated': True,
                         'activate_exit': False
                         })}
                )
        # Timer for moving to the next page after an auction concludes
        finished_groups = Group.objects.filter(activated=True, auction_over=True)
        for g in finished_groups:
            # Could put the max move_count into session_configs
            if g.move_count < 10:
                g.move_count += 1
                g.save()
            if g.move_count >= 10:
                g.move_count += 1
                g.save()
                g.advance_participants()


l = task.LoopingCall(runEverySecond)
l.start(1)
if not l.running:
    pass
