from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login, logout
from .models import Message
from .models import Profile
from .models import Contact
from .models import Notification, SharedFile, BackgroundOption, Archive
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from datetime import timedelta
import logging
logger = logging.getLogger(__name__)

User = get_user_model()

# Create your views here.

@login_required
def index(request):
    user = request.user
    # blocked_user_ids = Contact.objects.filter(user=user, blocked=True).values_list('contact_id', flat=True)

    blocked_user_ids = Contact.objects.filter(
        Q(user=user, blocked=True) | 
        Q(contact_id=user.id, blocked=True)
    ).values_list('contact_id', 'user_id')

    all_blocked_ids = set()
    for contact_id, user_id in blocked_user_ids:
        all_blocked_ids.add(contact_id if contact_id != user.id else user_id)
    
    archived_chat = Archive.objects.filter(is_active=True).values_list('thread_name', flat=True)

    seen_users = set()
    conversations = []
    messages_with_separators = []
    last_message_timestamp = None

    user_messages = Message.objects.filter(
        Q(sender=user) | Q(receiver=user)
        ).exclude(thread_name__isnull=True
        ).exclude(Q(sender_id__in=all_blocked_ids) | Q(receiver_id__in=all_blocked_ids)
        ).exclude(Q(thread_name__in=archived_chat)
        ).select_related('sender', 'receiver', 'sender__profile', 'receiver__profile').order_by('-timestamp')

    for message in user_messages:
        other_user = message.receiver if message.sender == user else message.sender

        if other_user.id not in seen_users:
            seen_users.add(other_user.id)
            conversations.append({
                'other_user': other_user,
                'latest_message': message,
                'thread_name': message.thread_name,
            })

    latest_conversation = conversations[0] if conversations else None
    thread_name = None
    if latest_conversation:
        thread_name = latest_conversation['thread_name']
        messages = Message.objects.filter(thread_name=thread_name).order_by('timestamp')
        sharedfiles = SharedFile.objects.filter(thread_name=thread_name).order_by('timestamp')

        all_items = []

        for message in messages:
            all_items.append({
                'timestamp': message.timestamp,
                'type': 'text',
                'content': message,
                'caption': '',
                'size': ''
            })
        
        for file in sharedfiles:           
            if file.image and file.image.name:
                all_items.append({
                    'timestamp': file.timestamp,
                    'type': 'image',
                    'content': file,
                    'caption': file.image_caption,
                    'size': ''
                })
                
            elif file.video and file.video.name:
                all_items.append({
                    'timestamp': file.timestamp,
                    'type': 'video',
                    'content': file,
                    'caption': '',
                    'size': ''
                })
            
            elif file.file and file.file.name:
                all_items.append({
                    'timestamp': file.timestamp,
                    'type': 'document',
                    'content': file,
                    'caption': '',
                    'size': file.file.size
                })
            
            elif file.link:
                all_items.append({
                    'timestamp': file.timestamp,
                    'type': 'link',
                    'content': file,
                    'caption': '',
                    'size': ''
                })
            
            elif file.audio and file.audio.name:
                all_items.append({
                    'timestamp': file.timestamp,
                    'type': 'audio',
                    'content': file,
                    'caption': '',
                    'size': ''
                })

        all_items.sort(key=lambda x:x['timestamp'])
        
        # Add timestamp separators
        prev_item = None
        for item in all_items:
            if prev_item and (item['timestamp'] - prev_item['timestamp']).total_seconds() > 86400:
                messages_with_separators.append({
                    'is_separator': True,
                    'timestamp': item['timestamp']
                })

            messages_with_separators.append({
                'is_separator': False,
                'message': item['content'],
                'type': item['type'],
                'image_caption': item['caption'],
                'size': item['size']
            })
            prev_item = item

    if messages_with_separators:
        for item in reversed(messages_with_separators):
            if not item['is_separator']:
                last_message_timestamp = item['message'].timestamp.isoformat()
                break
        
    return render(request, 'chat/index.html', {
        'thread_name': thread_name,
        'conversations': conversations,
        'other_user': latest_conversation['other_user'] if latest_conversation else None,
        'messages_with_separators': messages_with_separators,
        'last_message_timestamp': last_message_timestamp,
        'background_options': BackgroundOption.objects.filter(is_active=True).order_by('name')
    })

@login_required
def private_chat(request, other_user_id):
    user = request.user
    users_dict = {u.id: u for u in User.objects.filter(id__in=[user.id, other_user_id])}
    other_user = users_dict[other_user_id]

    # is_blocked = Contact.objects.filter(user=user, contact_id=other_user_id, blocked=True).exists()
    # if is_blocked:
    #     return redirect('index')

    is_blocked = Contact.objects.filter(
        Q(user=user, contact_id=other_user_id, blocked=True) |
        Q(user_id=other_user_id, contact=user, blocked=True)
    ).exists()

    if is_blocked:
        return redirect('index')
    blocked_user_ids = Contact.objects.filter(
        Q(user=user, blocked=True) |
        Q(contact_id=user.id, blocked=True)
    ).values_list('contact_id', 'user_id')

    all_blocked_ids = set()
    for contact_id, user_id in blocked_user_ids:
        all_blocked_ids.add(contact_id if contact_id != user.id else user_id)

    archived_chat = Archive.objects.filter(is_active=True).values_list('thread_name', flat=True)

    thread_name = Message.get_thread_name(user.id, other_user.id)
    if thread_name in archived_chat:
        return redirect('index')
    
    messages = Message.objects.filter(thread_name=thread_name)
    sharedfiles = SharedFile.objects.filter(thread_name=thread_name)

    all_items = []

    for message in messages:
        all_items.append({
            'timestamp': message.timestamp,
            'type': 'text',
            'content': message,
            'caption': '',
            'size': ''
        })
    
    for file in sharedfiles:           
        if file.image and file.image.name:
            all_items.append({
                'timestamp': file.timestamp,
                'type': 'image',
                'content': file,
                'caption': file.image_caption,
                'size': ''
            })
            
        elif file.video and file.video.name:
            all_items.append({
                'timestamp': file.timestamp,
                'type': 'video',
                'content': file,
                'caption': '',
                'size': ''
            })
        
        elif file.file and file.file.name:
            all_items.append({
                'timestamp': file.timestamp,
                'type': 'document',
                'content': file,
                'caption': '',
                'size': file.file.size
            })
        
        elif file.link:
            all_items.append({
                'timestamp': file.timestamp,
                'type': 'link',
                'content': file,
                'caption': '',
                'size': ''
            })
    
    all_items.sort(key=lambda x:x['timestamp'])

    messages_with_separators = []
    prev_item = None

    for item in all_items:
        if prev_item and (item['timestamp'] - prev_item['timestamp']).total_seconds() > 86400:
            messages_with_separators.append({
                'is_separator': True, 
                'timestamp': item['timestamp']
            })
        
        messages_with_separators.append({
            'is_separator': False,
            'type': item['type'],
            'message': item['content'],
            'image_caption': item['caption'],
            'size': item['size']
        })
        prev_item = item

    # Get conversations for sidebar (same logic as index)
    seen_users = set()
    conversations = []
    
    user_messages = Message.objects.filter(
        Q(sender=user) | Q(receiver=user)
    ).exclude(thread_name__isnull=True
    ).exclude(Q(sender_id__in=all_blocked_ids) | Q(receiver_id__in=all_blocked_ids)
    ).exclude(Q(thread_name__in=archived_chat)
    ).order_by('-timestamp')
    
    for message in user_messages:
        other_user_conv = message.receiver if message.sender == user else message.sender
        
        if other_user_conv.id not in seen_users:
            seen_users.add(other_user_conv.id)
            conversations.append({
                'other_user': other_user_conv,
                'latest_message': message,
                'thread_name': message.thread_name,
            })
    
    last_message_timestamp = None
    if messages_with_separators:
        for item in reversed(messages_with_separators):
            if not item['is_separator']:
                last_message_timestamp = item['message'].timestamp.isoformat()
                break

    return render(request, 'chat/index.html', {
        'thread_name': thread_name,
        'other_user': other_user,
        'current_user': other_user,
        'messages_with_separators': messages_with_separators,
        'conversations': conversations,
        'last_message_timestamp': last_message_timestamp,
        'background_options': BackgroundOption.objects.filter(is_active=True).order_by('name')
    })

@require_http_methods(['GET'])
@login_required
def get_notifications(request):
    try:
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

        data = [{
            'id': n.id,
            'message': n.content,
            'sender_firstname': n.sender.first_name,
            'sender_lastname': n.sender.last_name,
            'thread_name': n.message.thread_name if n.message else None,
            'sender_img': n.sender.profile.photo.url if n.sender.profile.photo else None,
            'created_at': n.created_at.isoformat(),
            'is_read': n.is_read
        } for n in notifications]

        return JsonResponse({'notifications': data, 'unread_count': unread_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(['POST'])
@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

@require_http_methods(['POST'])
@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})   

@require_http_methods(['DELETE'])
@login_required
def delete_message(request, message_id):
    try:        
        message = Message.objects.get(id=message_id, sender=request.user)
        thread_name = message.thread_name
        receiver_id = message.receiver_id
        message.delete() 

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send) (
            thread_name,
            {
                'type': 'message.deleted',
                'message_id': message_id
            }
        )

        if receiver_id:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{receiver_id}',
                {
                    'type': 'message.deleted',
                    'message_id': message_id
                }
            )
        return JsonResponse({'status': 'success'})
    except Message.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Message not found or unauthorized'}, status=404)
    
@require_http_methods(['DELETE'])
@login_required
def delete_file(request, message_id):
    try:
        file = SharedFile.objects.get(id=message_id, sender=request.user)
        thread_name = file.thread_name
        
        if file.video and file.video.name:
            file.video.delete(save=True)
            file.delete()
        elif file.image and file.image.name:
            file.image.delete(save=False)
            file.delete()
        elif file.audio and file.audio.name:
            file.audio.delete(save=False)
            file.delete()
        else:
            file.file.delete(save=False)
            file.delete()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            thread_name,
            {
                'type': 'message.deleted',
                'message_id': message_id
            }
        )
        return JsonResponse({'status': 'success'})
    except SharedFile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'File not found or unauthorized'}, status=404)

@login_required
def edit_profile(request):
    user_contacts = Contact.objects.filter(user=request.user, blocked=False)
    user_contacts_selected = user_contacts[:5]
    user_contacts_count = user_contacts.count() if user_contacts.exists() else 0
    
    return render(request, 'chat/edit-profile.html', {'user_contacts_selected': user_contacts_selected, 'user_contacts_count': user_contacts_count})

@login_required
def update_personal_info(request):
    if request.method == 'POST':
        first_name = request.POST.get('first-name')
        last_name = request.POST.get('last-name')
        email = request.POST.get('email', '').strip()

        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        return redirect('profile_page', user_id=request.user.id)
    return redirect('profile_page', user_id=request.user.id)

@login_required
def upload_photo(request):
    if request.method == 'POST' and (request.FILES.get('photo') or request.FILES.get('header-img')):
        profile, created = Profile.objects.get_or_create(user=request.user)
        if created:
            profile.bio = 'Welcome to our app!'
            profile.photo = None
            profile.header_img = None
        else:
            if request.FILES.get('photo'):
                profile.photo.delete(save=False)
            if request.FILES.get('header-img'):
                profile.header_img.delete(save=False)

        images_fields = {
            'header_img': request.FILES.get('header-img'),
            'photo': request.FILES.get('photo')
        }

        for image_field, value in images_fields.items():
            if value:
                setattr(profile, image_field, value)

        profile.save()
        return redirect('profile_page', user_id=request.user.id)
    
    return redirect('profile_page', user_id=request.user.id)

@login_required
def update_basic_info(request):
    if request.method == 'POST':
        profile, created = Profile.objects.get_or_create(user=request.user)

        fields = {
            'status': request.POST.get('status'),
            'bio': request.POST.get('bio'),
            'birthdate': request.POST.get('birthdate'),
            'gender': request.POST.get('gender'),
            'language': request.POST.get('language'),
            'city': request.POST.get('city'),
            'phone_no': request.POST.get('phone-no'),
            'nickname': request.POST.get('nickname')
        }

        for field, value in fields.items():
            if value:
                setattr(profile, field, value)

        profile.save()
        return redirect('profile_page', user_id=request.user.id)

@login_required
def profile_page(request, user_id=None):
    try:
        profile = Profile.objects.prefetch_related('user__contacts').get(user_id=user_id) if user_id else Profile.objects.prefetch_related('user__contacts').get(user=request.user)
        user_contacts = profile.user.contacts.filter(blocked=False)
        user_contacts_selected = user_contacts[:5]
        user_contacts_count = user_contacts.count() if user_contacts.exists() else 0
    except Profile.DoesNotExist:

        profile = None

    return render(request, 'chat/profile-page.html', {'profile': profile, 'user_contacts_selected': user_contacts_selected, 'user_contacts_count': user_contacts_count})

@login_required
def chat_users(request):
    users = User.objects.select_related('profile').filter(is_superuser=False, is_staff=False).exclude(id=request.user.id)
    added_user_ids = set(Contact.objects.filter(user=request.user).values_list('contact_id', flat=True))
    return render(request, 'chat/chat-users.html', {'users': users, 'added_user_ids': added_user_ids})

@require_http_methods(['POST'])
@login_required
def add_contact(request, user_id):
    try:
        contact_user = User.objects.get(id=user_id)
        if contact_user != request.user:
            Contact.objects.get_or_create(user=request.user, contact=contact_user)
            return JsonResponse({'status': 'success'})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)

# @login_required
# def contacts(request):
#     user = User.objects.prefetch_related('contacts__contact__profile').get(id=request.user.id)
#     first_user = user.contacts.order_by('added_at').first() if user.contacts.exists() else None
#     first_user_contact = Contact.objects.filter(user=first_user.contact).first() if first_user else None
#     first_user_contact_count = first_user_contact.contacts.count() if first_user_contact else 0
#     contact_count = user.contacts.count()
#     if user.contacts.exists():
#         return render(request, 'chat/contacts.html', {'user': user, 'first_user': first_user, 'first_user_contact_count': first_user_contact_count, 'contact_count': contact_count})
#     else:
#         error_message = 'No contacts found. Please add users'
#         return render(request, 'chat/contacts.html', {'error_message': error_message})

@login_required
def contacts(request):
    contacts_qs = request.user.contacts.select_related('contact__profile').filter(blocked=False).order_by('added_at')
    week_ago = timezone.now() - timedelta(days=7)
    new_contacts = contacts_qs.filter(added_at__gte=week_ago)
    favorite_contacts = contacts_qs.filter(is_favorite=True)
    blocked_contacts = request.user.contacts.filter(blocked=True)
    
    if not contacts_qs.exists():
        return render(request, 'chat/contacts.html', {
            'error_message': 'No contacts found. Please add users'
        })
    
    first_contact = contacts_qs.first()
    first_user_contacts = Contact.objects.filter(user=first_contact.contact, blocked=False)
    first_user_contacts_count = first_user_contacts.count() if first_user_contacts.exists() else 0
    first_user_contacts_selected = first_user_contacts[:5]
    
    return render(request, 'chat/contacts.html', {
        'contacts': contacts_qs,
        'first_user': first_contact,
        'first_user_contacts_selected': first_user_contacts_selected,
        'first_user_contacts_count': first_user_contacts_count,
        'contact_count': contacts_qs.count(),
        'new_contacts': new_contacts,
        'favorite_contacts': favorite_contacts,
        'blocked_contacts': blocked_contacts
    })

@require_http_methods(['DELETE'])
@login_required
def delete_contact(request, contact_id):
    try:
        contact = Contact.objects.get(user=request.user, contact_id=contact_id)
        contact.delete()
        return JsonResponse({'status': 'success'})
    except Contact.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Contact not found'}, status=404)

@require_http_methods(['GET'])
@login_required
def get_contact_profile(request, contact_id=None):
    try:
        contact_profile = Profile.objects.select_related('user').get(user_id=contact_id)
        contact_own_contacts_qs = Contact.objects.filter(user_id=contact_id, blocked=False)
        contact_own_contacts_qs_selected = contact_own_contacts_qs[:5]
        data = {
            'first_name': contact_profile.user.first_name,
            'last_name': contact_profile.user.last_name,
            'username': contact_profile.user.username,
            'profile_pic_url': contact_profile.photo.url if contact_profile.photo else None,
            'header_img_url': contact_profile.header_img.url if contact_profile.header_img else None,
            'bio': contact_profile.bio,
            'birthdate': contact_profile.birthdate.isoformat() if contact_profile.birthdate else None,
            'gender': contact_profile.gender,
            'language': contact_profile.language,
            'city': contact_profile.city,
            'phone_no': contact_profile.phone_no,
            'email': contact_profile.user.email,
            'contact_own_contacts_qs_count': contact_own_contacts_qs.count() if contact_own_contacts_qs else 0,
            'contact_own_contacts_qs_selected': [{'contact_profile_pic': contact.contact.profile.photo.url} for contact in contact_own_contacts_qs_selected] if contact_own_contacts_qs_selected else None
        }
        return JsonResponse(data)
    except Profile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Contact profile not found'}, status=404)

@require_http_methods(['POST'])
@login_required
def toggle_favorite(request, contact_id):
    try:
        contact = Contact.objects.get(user=request.user, contact_id=contact_id)
        contact.is_favorite = not contact.is_favorite
        contact.save()
        return JsonResponse({'status': 'success', 'is_favorite': contact.is_favorite})
    except Contact.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Contact not found'}, status=404)

@require_http_methods(['POST'])
@login_required
def toggle_block(request, contact_id):
    try:
        contact = Contact.objects.get(user=request.user, contact_id=contact_id)
        contact.blocked = not contact.blocked
        contact.save()
        return JsonResponse({'status': 'success', 'blocked': contact.blocked})
    except Contact.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Contact not found'}, status=404)

@require_http_methods(['POST'])
@login_required
def toggle_block_user(request, user_id):
    try:
        user_to_block = User.objects.get(id=user_id)
        contact, created = Contact.objects.get_or_create(
            user=request.user, 
            contact=user_to_block, 
            defaults={'blocked': True}
        )
        if not created:
            contact.blocked = not contact.blocked
            contact.save()
        return JsonResponse({'status': 'success', 'blocked': contact.blocked if not created else True})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    
@require_http_methods(['POST'])
@login_required
def upload_image(request):
    try:
        image = request.FILES.get('image')
        image_caption = request.POST.get('image_caption')
        receiver_id = request.POST.get('receiver_id')
        thread_name = Message.get_thread_name(request.user.id, receiver_id)

        if image and receiver_id:
            receiver = User.objects.get(id=receiver_id)
            shared_file = SharedFile.objects.create(
                sender=request.user,
                receiver=receiver,
                image=image,
                video=None,
                audio=None,
                image_caption=image_caption,
                thread_name=thread_name
            )
            return JsonResponse({'success': True, 'image_url': shared_file.image.url, 'image_caption': shared_file.image_caption, 'image_id': shared_file.id})
        
        return JsonResponse({'success': False, 'error': 'Missing image or receiver'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receiver not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['POST'])
@login_required
def upload_video(request):
    try:
        video = request.FILES.get('video')
        receiver_id = request.POST.get('receiver_id')
        thread_name = Message.get_thread_name(request.user.id, receiver_id)

        if video and receiver_id:
            receiver = User.objects.get(id=receiver_id)
            shared_file = SharedFile.objects.create(
                sender=request.user,
                receiver=receiver,
                video=video,
                image=None,
                audio=None,
                thread_name=thread_name
            )
            return JsonResponse({'success': True, 'video_url': shared_file.video.url, 'video_id': shared_file.id})
        
        return JsonResponse({'success': False, 'error': 'Missing image or receiver'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receiver not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['POST'])
@login_required
def upload_document(request):
    try:
        file = request.FILES.get('document')
        receiver_id = request.POST.get('receiver_id')
        thread_name = Message.get_thread_name(request.user.id, receiver_id)

        if file and receiver_id:
            receiver = User.objects.get(id=receiver_id)
            shared_file = SharedFile.objects.create(
                sender=request.user,
                receiver=receiver,
                video=None,
                image=None,
                file=file,
                thread_name=thread_name
            )

            file_size_mb = round(shared_file.file.size / (1024 * 1024), 2)

            return JsonResponse({'success': True, 'document_url': shared_file.file.url, 'document_name': shared_file.file.name, 'document_size': file_size_mb, 'document_id': shared_file.id})
        return JsonResponse({'success': False, 'error': 'Missing document or receiver'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receiver not found'}, status=404)
    except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['POST'])
@login_required
def upload_link(request):
    try:
        link = request.POST.get('link')
        receiver_id = request.POST.get('receiver_id')
        thread_name = Message.get_thread_name(request.user.id, receiver_id)

        if link and receiver_id:
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            receiver = User.objects.get(id=receiver_id)
            shared_file = SharedFile.objects.create(
                sender=request.user,
                receiver=receiver,
                link=link,
                thread_name=thread_name
            )

            return JsonResponse({'success': True, 'link': shared_file.link, 'link_id': shared_file.id})
        return JsonResponse({'success': False, 'error': 'Missing link or receiver'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Receiver not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['GET'])
@login_required
def get_active_time(request, other_user_id):
    try:
        other_user = User.objects.get(id=other_user_id)
        last_seen = other_user.profile.last_seen
        active_time = (timezone.now() - last_seen).total_seconds() < 300 if last_seen else False

        return JsonResponse({'active_time': active_time, 'last_seen': last_seen.isoformat() if last_seen else None})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

@require_http_methods(['GET'])
@login_required
def get_shared_files(request, other_user_id):
    try:
        thread_name = Message.get_thread_name(request.user.id, other_user_id)
        shared_files = SharedFile.objects.filter(thread_name=thread_name)

        video_files = shared_files.filter(video__isnull=False)
        image_files = shared_files.filter(image__isnull=False)
        files = shared_files.filter(file__isnull=False)
        links = shared_files.filter(link__isnull=False)

        image_data = [{
            'id': image.id,
            'image_caption': image.image_caption,
            'image_url': image.image.url,
            'image_name': image.image.name
        } for image in image_files if image.image]

        video_data = [{
            'id': video.id,
            'video_url': video.video.url,
            'video_name': str(video.video).split('/')[-1]
        } for video in video_files if video.video]

        file_data = [{
            'id': file.id,
            'file_url': file.file.url,
            'file_name': str(file.file).split('/')[-1],
            'file_size': round(file.file.size / (1024 * 1024), 2)
        } for file in files if file.file]

        link_data = [{
            'id': link.id,
            'link': link.link
        } for link in links if link.link]

        return JsonResponse({'image_data': image_data, 'video_data': video_data, 'file_data': file_data, 'link_data': link_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(['POST'])
@login_required
def upload_audio(request):
    try:
        audio = request.FILES.get('audio')
        receiver_id = request.POST.get('receiver_id')
        thread_name = Message.get_thread_name(request.user.id, receiver_id)

        if audio and receiver_id:
            receiver = User.objects.get(id=receiver_id)

            shared_file = SharedFile.objects.create(
                sender=request.user,
                receiver=receiver,
                audio=audio,
                image=None,
                video=None,
                thread_name=thread_name
            )

            return JsonResponse({'success': True, 'audio_url': shared_file.audio.url, 'audio_id': shared_file.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def archives(request):
    archives = Archive.objects.filter(user=request.user, is_active=True).order_by('-archived_at')

    if not archives.exists():
        return render(request, 'chat/archives.html', {'archives': []})

    thread_names = archives.values_list('thread_name', flat=True)

    latest_messages_qs = Message.objects.filter(
        thread_name__in=thread_names
    ).order_by('thread_name', '-timestamp').distinct('thread_name')
    
    messages_dict = {msg.thread_name: msg for msg in latest_messages_qs}

    for archive in archives:
        archive.latest_message = messages_dict.get(archive.thread_name)
        
    return render(request, 'chat/archives.html', {'archives': archives})

@require_http_methods(['POST'])
@login_required
def archive_chat(request, other_user_id):
    try:
        thread_name = Message.get_thread_name(request.user.id, other_user_id)
        archive_chat, created = Archive.objects.get_or_create(
            user=request.user,
            other_user_id=other_user_id,
            thread_name=thread_name,
            is_active=True
        )
        if not created:
            pass
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['POST'])
@login_required
def unarchive(request, other_user_id):
    try:
        thread_name = Message.get_thread_name(request.user.id, other_user_id)
        archive = Archive.objects.get(user=request.user, other_user_id=other_user_id, thread_name=thread_name)
        archive.is_active = False
        archive.save()
        return JsonResponse({'success': True})
    except Archive.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Archive not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['DELETE'])
@login_required
def delete_chat(request, other_user_id):
    try:
        thread_name = Message.get_thread_name(request.user.id, other_user_id)
        Message.objects.filter(thread_name=thread_name).delete()
        SharedFile.objects.filter(thread_name=thread_name).delete()
        Archive.objects.filter(user=request.user, other_user_id=other_user_id, thread_name=thread_name).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(['GET'])
@login_required
def search_conversations(request):
    try:
        query = request.GET.get('q', '')

        if not query:
            return JsonResponse({'conversations': []})
        
        blocked_user_ids = Contact.objects.filter(Q(user=request.user, blocked=True) | Q(contact_id=request.user.id, blocked=True)
                            ).values_list('contact_id', 'user_id')
        
        all_blocked_ids = set()
        for contact_id, user_id in blocked_user_ids:
            all_blocked_ids.add(contact_id if contact_id != request.user.id else user_id)
        
        archived_chat = Archive.objects.filter(is_active=True).values_list('thread_name', flat=True)
        
        # messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)
        #             ).filter(
        #                 Q(sender__first_name__icontains=query) | Q(receiver__first_name__icontains=query) |
        #                 Q(sender__last_name__icontains=query) | Q(receiver__last_name__icontains=query)
        #             ).exclude(
        #                 Q(sender_id__in=all_blocked_ids) | Q(receiver_id__in=all_blocked_ids)
        #             ).exclude(Q(thread_name__in=archived_chat)
        #             ).select_related('sender__profile', 'receiver__profile'
        #             ).order_by('-timestamp')
        # seen_threads = set()

        messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)
                    ).select_related('sender__profile', 'receiver__profile'
                    ).exclude(Q(sender_id__in=all_blocked_ids) | Q(receiver_id__in=all_blocked_ids)
                    ).exclude(Q(thread_name__in=archived_chat)
                    ).order_by('-timestamp')
        
        seen_users = set()
        results = []

        for message in messages:
            other_user = message.receiver if message.sender == request.user else message.sender
            if (query.lower() not in other_user.first_name.lower() and
                query.lower() not in other_user.last_name.lower()):
                continue

            if other_user.id in seen_users:
                continue
            seen_users.add(other_user.id)

            # if message.thread_name not in seen_threads:
            #     seen_threads.add(message.thread_name)

            results.append({
                'other_user_id': other_user.id,
                'first_name': other_user.first_name,
                'last_name': other_user.last_name,
                'photo_url': other_user.profile.photo.url if other_user.profile.photo else None,
                'content': message.content,
                'timestamp': message.timestamp.isoformat() if message.timestamp else None
            })

        return JsonResponse({'conversations': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def room(request, room_name):
    return render(request, 'private/private_chat.html', {'room_name': room_name})

def stories(request):
    return render(request, 'chat/stories.html')

def reset(request):
    return render(request, 'reset/reset.html')

def error_404(request):
    return render(request, 'error-404/error-404.html')

def user_login(request):
    if request.method == 'POST':
       username = request.POST.get('username')
       password = request.POST.get('password')

       user = authenticate(request, username=username, password=password)
       if user is not None:
           login(request, user)
           return redirect('/')
       else:
           error_message = 'Invalid username or password'
           return render(request, 'login/login.html', {'error_message': error_message})

    return render(request, 'login/login.html')

def user_signup(request):
    if request.method == 'POST':
       username = request.POST.get('username')
       email = request.POST.get('email')
       password = request.POST.get('password')
       repeatPassword = request.POST.get('repeat-password')
       policy = request.POST.get('policy')

       if password == repeatPassword and policy:
           try:
               user = User.objects.create_user(username, email, password)
               user.save()
               login(request, user)
               return redirect('/')
           except:
               error_message = 'Error creating account'
               return render(request, 'signup/signup.html', {'error_message': error_message})
       else:
           error_message = 'Passwords do not match or you did you accept the policy'
           return render(request, 'signup/signup.html', {'error_message': error_message})
    
    return render(request, 'signup/signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')