import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Notification, Contact

User = get_user_model()

class PrivateChatConsumer(AsyncWebsocketConsumer):    
    async def connect(self):
        # print(f"WebSocket connect attempt")
        # print(f"User: {self.scope['user']}")
        # print(f"Is anonymous: {self.scope['user'].is_anonymous}")
        
        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.other_user_id = int(self.scope['url_route']['kwargs']['other_user_id'])
        
        # print(f"URL user_id: {self.user_id}")
        # print(f"URL other_user_id: {self.other_user_id}")

        if self.scope['user'].is_anonymous:
            #print("Rejecting: User is anonymous")
            await self.close()
            return

        current_user_id = self.scope['user'].id
        #print(f"Current user ID: {current_user_id}")
        
        if current_user_id not in [self.user_id, self.other_user_id]:
            # print(f"Rejecting: User {current_user_id} not in [{self.user_id}, {self.other_user_id}]")
            await self.close()
            return
        
        try:
            # print("Getting thread name...")
            self.room_name = Message.get_thread_name(int(self.user_id), int(self.other_user_id))
            # print(f"Room name now: {self.room_name}")
            
            self.room_group_name = self.room_name
            # print("Adding to channel layer...")
            
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            # print("Accepting connection...")
            
            await self.accept()
            # print("WebSocket connection accepted")
            
        except Exception as e:
            # print(f"Error in connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        # print(f"WebSocket disconnected with code: {close_code}")
        if hasattr(self, 'room_group_name'):
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            except Exception:
                pass  # Ignore errors during cleanup

    async def receive(self, text_data):
        data = json.loads(text_data)
        receiver_id = data.get('receiver_id')

        is_blocked = await self.check_blocked(receiver_id)
        
        if is_blocked:
            return
        
        try: 
            text_data_json = json.loads(text_data)

            if text_data_json['type'] == 'video_call_offer':
                await self.channel_layer.group_send(
                    self.room_group_name, 
                    {
                        'type': 'video_call_offer',
                        'offer': data['offer'],
                        'from_user': data.get('sender_id', self.scope['user'].id)
                    }
                )
                return

            if text_data_json['type'] == 'video_call_answer':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'video_call_answer',
                        'answer': data['answer']
                    }
                )
                return
            
            if text_data_json['type'] == 'video_call_end':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'video_call_end'
                    }
                )
                return
            
            if text_data_json['type'] == 'ice_candidate':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'ice_candidate',
                        'candidate': data['candidate']
                    }
                )
                return

            if text_data_json['type'] == 'image':
                image_url = text_data_json['image_url']
                if not image_url.startswith('/media/'):
                    return
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message',
                        'message': image_url,
                        'message_caption': text_data_json.get('image_caption'),
                        'sender_id': text_data_json.get('sender_id'),
                        'receiver_id': text_data_json.get('receiver_id'),
                        'message_id': text_data_json.get('image_id'),
                        'message_type': text_data_json['type']
                    }
                )
                return
            
            elif text_data_json['type'] == 'video':
                video_url = text_data_json['video_url']
                if not video_url.startswith('/media/'):
                    return
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message',
                        'message': video_url,
                        'sender_id': text_data_json.get('sender_id'),
                        'receiver_id': text_data_json.get('receiver_id'),
                        'message_id': text_data_json.get('video_id'),
                        'message_type': text_data_json['type']
                    }
                )
                return
            
            elif text_data_json['type'] == 'document':
                document_url = text_data_json.get('document_url')
                if not document_url.startswith('/media/'):
                    return
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message',
                        'message': text_data_json.get('document_name'),
                        'message_size': text_data_json.get('document_size'),
                        'sender_id': text_data_json.get('sender_id'),
                        'receiver_id': text_data_json.get('receiver_id'),
                        'message_id': text_data_json.get('document_id'),
                        'message_type': text_data_json.get('type')
                    }
                )
                return
            
            elif text_data_json['type'] == 'link':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message',
                        'message': text_data_json.get('link'),
                        'sender_id': text_data_json.get('sender_id'),
                        'receiver_id': text_data_json.get('receiver_id'),
                        'message_id': text_data_json.get('link_id'),
                        'message_type': text_data_json.get('type')
                    }
                )
                return
            
            elif text_data_json['type'] == 'audio':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message',
                        'message': text_data_json.get('audio_url'),
                        'sender_id': text_data_json.get('sender_id'),
                        'receiver_id': text_data_json.get('receiver_id'),
                        'message_id': text_data_json.get('audio_id'),
                        'message_type': text_data_json.get('type')
                    }
                ) 
                return
                 
            message = text_data_json['message']
            sender_id = text_data_json.get('sender_id')
            receiver_id = text_data_json.get('receiver_id')
            message_type = text_data_json.get('type')

            saved_message = await self.save_message(sender_id, receiver_id, message)

            await self.create_notification(sender_id, receiver_id, message, saved_message.id)

            # await self.message_id()

            await self.channel_layer.group_send(
                self.room_group_name, 
                {
                    'type': 'chat.message',
                    'message': message,
                    'sender_id': sender_id,
                    'receiver_id': receiver_id,
                    # 'message_id': await self.message_id()
                    'message_id': saved_message.id,
                    'message_type': message_type
                }
            )
        except Exception as e:
            # print(f"Error in receive: {e}")
            await self.close()

    async def chat_message(self, event):
            message = event['message']
            sender_id = event['sender_id']
            receiver_id = event['receiver_id']
            # message_history = event.get('message_history', [])
            # message_id = message_history[-1]['id'] if message_history else None
            message_id = event['message_id']
            message_type = event.get('message_type')
            message_caption = event.get('message_caption') if message_type == 'image' else None
            message_size = event.get('message_size') if message_type == 'document' else None

            await self.send(text_data=json.dumps({
                'message': message,
                'message_caption': message_caption if message_type == 'image' else None,
                'message_size': message_size if message_type == 'document' else None,
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'message_id': message_id,
                'message_type': message_type
            }))
    
    async def message_deleted(self, event):
        message_id = event['message_id']

        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': message_id
        }))
    
    async def video_call_offer(self, event):
        offer = event['offer']
        from_user = event['from_user']

        await self.send(text_data=json.dumps({
            'type': 'video_call_offer',
            'offer': offer,
            'from_user': from_user
        }))
    
    async def video_call_answer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'video_call_answer',
            'answer': event['answer']
        }))

    async def video_call_end(self, event):
        await self.send(text_data=json.dumps({
            'type': 'video_call_end'
        }))

    async def ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'candidate': event['candidate']
        }))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
        saved_message = Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            thread_name=self.room_name
        )
        return saved_message
    
    @database_sync_to_async
    def check_blocked(self, receiver_id):
        return Contact.objects.filter(
            user_id=receiver_id,
            contact_id=self.scope['user'].id,
            blocked=True
        ).exists()
     
    # @database_sync_to_async
    # def message_id(self):
    #     messages = Message.objects.filter(thread_name=self.room_name).order_by('-timestamp')
    #     message_id = messages[0].id if messages else None
    #     # message_list = [
    #     #     {
    #     #         'id': message.id,
    #     #         'sender_id': message.sender_id,
    #     #         'receiver_id': message.receiver_id,
    #     #         'content': message.content,
    #     #         'timestamp': message.timestamp.isoformat()
    #     #     } for message in messages
    #     # ]
    #     return message_id

    @database_sync_to_async
    def create_notification(self, sender_id, receiver_id, message_content, message_id):
        from django.contrib.auth import get_user_model
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        User = get_user_model()
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)

        try:
            saved_notification = Notification.objects.create(
                user=receiver,
                sender=sender,
                content=f'{message_content[:50]}...'
                if len(message_content) > 50 else message_content,
                message_id=message_id 
            )

            channel_layer = get_channel_layer()
            unread_count = Notification.objects.filter(user=receiver, is_read=False).count()
            sender_img = sender.profile.photo.url if hasattr(sender, 'profile') and sender.profile.photo else None
            thread_name = Message.get_thread_name(sender_id, receiver_id)

            async_to_sync(channel_layer.group_send)(
                f'notifications_{receiver_id}', {
                    'type': 'notification.message',
                    'message': f'{message_content[:50]}...',
                    'sender_firstname': sender.first_name,
                    'sender_lastname': sender.last_name,
                    'count': unread_count,
                    'sender_img': sender_img,
                    'thread_name': thread_name,
                    'notification_id': saved_notification.id,
                    'created_at': saved_notification.created_at.isoformat()
                }
            )
        except Exception as e:
            # print(f"Error creating notification: {e}")
            pass

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])

        if self.scope['user'].is_anonymous or int(self.scope['user'].id) != int(self.user_id):
            await self.close()
            return
    
        self.group_name = f'notifications_{self.user_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
            'sender_firstname': event['sender_firstname'],
            'sender_lastname': event['sender_lastname'],
            'count': event['count'],
            'sender_img': event['sender_img'],
            'thread_name': event['thread_name'],
            'notification_id': event['notification_id'],
            'created_at': event['created_at']
        }))

    async def message_deleted(self, event):

        await self.send(text_data=json.dumps({
            'type': 'delete',
        }))

class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
        await self.channel_layer.group_add(f'presence', self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        from django.utils import timezone
        
        await self.channel_layer.group_send('presence', {
            'type': 'user.status',
            'user_id': self.user_id,
            'is_active': False,
            'last_seen': timezone.now().isoformat() 
        })    
    
    async def receive(self, text_data):
        try:
            if json.loads(text_data)['type'] == 'heartbeat':
                await self.channel_layer.group_send('presence', {
                    'type': 'user.status',
                    'user_id': self.user_id,
                    'is_active': True
                })
        except Exception as e:
            await self.close()
    
    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'is_active': event['is_active'],
            'last_seen': event['last_seen'] if event['is_active'] == False else None
        }))
    


