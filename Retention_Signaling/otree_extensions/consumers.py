from channels.generic.websockets import JsonWebsocketConsumer
import random
from Retention_Signaling.models import Constants, Player, Group
import json
import channels


class PriceTracker(JsonWebsocketConsumer):
    url_pattern = (r'^/price_increase/(?P<player_pk>[0-9]+)/(?P<group_pk>[0-9]+)$')

    def clean_kwargs(self):
        self.player_pk = self.kwargs['player_pk']
        self.group_pk = self.kwargs['group_pk']

    def connection_groups(self, **kwargs):
        group_name = self.get_group().get_channel_group_name()
        return [group_name]

    def connect(self, message, **kwargs):
        print('someone connected')

    def disconnect(self, message, **kwargs):
        print('someone disconnected')

    def get_player(self):
        self.clean_kwargs()
        return Player.objects.get(pk=self.player_pk)

    def get_group(self):
        self.clean_kwargs()
        return Group.objects.get(pk=self.group_pk)

    def receive(self, text=None, bytes=None, **kwargs):
        self.clean_kwargs()
        player = self.get_player()
        group = self.get_group()
        player.leave_auction()
        player.save()
        group.remaining_bidders()
        group.save()
        channels.Group(
            group.get_channel_group_name()
        ).send(
            {'text': json.dumps(
                {'num': group.num_in_auction,
                 })}
        )
