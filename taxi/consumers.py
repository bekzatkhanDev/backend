import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

from taxi.models import Trip, TripChatRoom, ChatMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for trip chat rooms.
    
    Features:
    - Only allows access to trip participants (driver and customer)
    - Creates chat room automatically when driver is assigned to trip
    - Real-time message broadcasting
    - Message persistence in database
    """

    async def connect(self):
        self.trip_id = self.scope["url_route"]["kwargs"]["trip_id"]
        self.room_group_name = f"chat_{self.trip_id}"

        # Check if user is authenticated
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Check if user is authorized to access this chat room
        is_authorized = await self.is_trip_participant(self.trip_id, self.user.id)
        if not is_authorized:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send confirmation message
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Connected to chat room",
            "trip_id": str(self.trip_id),
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Receive message from WebSocket and save to database.
        """
        try:
            data = json.loads(text_data)
            message_text = data.get("message", "").strip()

            if not message_text:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Message cannot be empty"
                }))
                return

            # Save message to database
            chat_room = await self.get_or_create_chat_room(self.trip_id)
            if not chat_room:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Chat room not available. Driver must be assigned first."
                }))
                return

            message = await self.save_message(chat_room, self.user, message_text)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message_text,
                    "sender_id": self.user.id,
                    "sender_phone": self.user.phone,
                    "created_at": message.created_at.isoformat(),
                    "message_id": message.id,
                }
            )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid JSON format"
            }))

    async def chat_message(self, event):
        """
        Send message to WebSocket client.
        """
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_phone": event["sender_phone"],
            "created_at": event["created_at"],
            "message_id": event["message_id"],
        }))

    @database_sync_to_async
    def is_trip_participant(self, trip_id, user_id):
        """
        Check if user is a participant of the trip (driver or customer).
        """
        try:
            trip = Trip.objects.select_related('driver', 'customer').get(id=trip_id)
            return trip.driver_id == user_id or trip.customer_id == user_id
        except Trip.DoesNotExist:
            return False

    @database_sync_to_async
    def get_or_create_chat_room(self, trip_id):
        """
        Get existing chat room or create new one if driver is assigned.
        Returns None if driver is not assigned yet.
        """
        try:
            trip = Trip.objects.select_related('chat_room').get(id=trip_id)
            
            # Only create chat room if driver is assigned
            if not trip.driver_id:
                return None
            
            # Get or create chat room
            chat_room, created = TripChatRoom.objects.get_or_create(trip=trip)
            return chat_room
        except Trip.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, chat_room, user, text):
        """
        Save chat message to database.
        """
        return ChatMessage.objects.create(
            chat_room=chat_room,
            sender=user,
            text=text
        )
